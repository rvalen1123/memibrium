#!/usr/bin/env python3
"""Guarded Step 5j_v2 LOCOMO corrected-slice launch controller.

This is an execution artifact, not product code. It enforces the preregistered
startup guard for the authorized telemetry-off conv-26 199Q reproducibility run.
"""
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path('/home/zaddy/src/Memibrium')
LOG_PATH = Path('/tmp/locomo_conv26_telemetry_off_reproducibility_v2_2026-05-02.log')
SUMMARY_PATH = REPO / 'docs/eval/results/locomo_corrected_slice_guard_summary_2026-05-02.json'

COMMAND = ['python3', 'benchmark_scripts/locomo_bench_v2.py', '--max-convs', '1', '--query-expansion']
GUARD_TIMEOUT_SECONDS = 180


def load_env_file(path: Path):
    env = os.environ.copy()
    if not path.exists():
        return env
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        env[key] = value
    return env


def main():
    env = load_env_file(REPO / '.env')
    env.update({
        'AZURE_CHAT_DEPLOYMENT': 'gpt-4.1-mini',
        'AZURE_OPENAI_DEPLOYMENT': 'gpt-4.1-mini',
        'ANSWER_MODEL': 'gpt-4.1-mini',
        'JUDGE_MODEL': 'gpt-4.1-mini',
        'CHAT_MODEL': 'gpt-4.1-mini',
        'AZURE_EMBEDDING_DEPLOYMENT': 'text-embedding-3-small',
        'USE_QUERY_EXPANSION': '1',
        'PYTHONUNBUFFERED': '1',
    })
    for key in [
        'INCLUDE_RECALL_TELEMETRY',
        'LOCOMO_RETRIEVAL_TELEMETRY',
        'USE_CONTEXT_RERANK',
        'USE_APPEND_CONTEXT_EXPANSION',
        'USE_GATED_APPEND_CONTEXT_EXPANSION',
        'USE_LEGACY_CONTEXT_ASSEMBLY',
    ]:
        env.pop(key, None)

    summary = {
        'step': '5j_v2_exec_guarded_launch',
        'timestamp_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'command': COMMAND,
        'log_path': str(LOG_PATH),
        'guard_timeout_seconds': GUARD_TIMEOUT_SECONDS,
        'env_assertions': {
            'INCLUDE_RECALL_TELEMETRY_absent': 'INCLUDE_RECALL_TELEMETRY' not in env,
            'LOCOMO_RETRIEVAL_TELEMETRY_absent': 'LOCOMO_RETRIEVAL_TELEMETRY' not in env,
            'USE_QUERY_EXPANSION': env.get('USE_QUERY_EXPANSION'),
            'AZURE_EMBEDDING_DEPLOYMENT': env.get('AZURE_EMBEDDING_DEPLOYMENT'),
            'AZURE_CHAT_DEPLOYMENT': env.get('AZURE_CHAT_DEPLOYMENT'),
            'AZURE_OPENAI_DEPLOYMENT': env.get('AZURE_OPENAI_DEPLOYMENT'),
        },
        'observed': {},
        'guard_status': 'running',
        'abort_reason': None,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open('w', buffering=1) as log:
        log.write(f"# guarded launch started {summary['timestamp_utc']}\n")
        log.write('# command: ' + ' '.join(COMMAND) + '\n')
        proc = subprocess.Popen(
            COMMAND,
            cwd=str(REPO),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        start = time.monotonic()
        convs_ok = total_ok = convline_ok = False
        mismatch = None

        while True:
            line = proc.stdout.readline() if proc.stdout else ''
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
                log.write(line)
                stripped = line.strip()
                m = re.search(r'Conversations to process:\s*(\d+)', stripped)
                if m:
                    val = int(m.group(1))
                    summary['observed']['conversations_to_process'] = val
                    if val == 1:
                        convs_ok = True
                    else:
                        mismatch = f'conversations_to_process_{val}'
                m = re.search(r'Total questions:\s*(\d+)\s*\((\d+)\s+evaluated', stripped)
                if m:
                    total = int(m.group(1)); evaluated = int(m.group(2))
                    summary['observed']['total_questions'] = total
                    summary['observed']['evaluated_questions'] = evaluated
                    if evaluated == 199:
                        total_ok = True
                    else:
                        mismatch = f'evaluated_questions_{evaluated}'
                if '[1/1] Conv ' in stripped:
                    summary['observed']['first_conversation_line'] = stripped
                    if stripped.startswith('[1/1] Conv conv-26:') or stripped.startswith('[1/1] Conv conv-26'):
                        convline_ok = True
                    else:
                        mismatch = f'first_conversation_line_{stripped}'

                if mismatch:
                    summary['guard_status'] = 'killed'
                    summary['abort_reason'] = 'slice_mismatch_invalid:' + mismatch
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    break
                if convs_ok and total_ok and convline_ok:
                    summary['guard_status'] = 'passed_startup_guard'
                    SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
                    # Guard passed; stream the rest without scope checks.
                    for rest in proc.stdout:
                        sys.stdout.write(rest)
                        sys.stdout.flush()
                        log.write(rest)
                    break
            else:
                if proc.poll() is not None:
                    break
                if time.monotonic() - start > GUARD_TIMEOUT_SECONDS:
                    summary['guard_status'] = 'killed'
                    summary['abort_reason'] = 'slice_guard_timeout'
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    break
                time.sleep(0.1)

        rc = proc.wait()
        summary['returncode'] = rc
        summary['completed_utc'] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if summary['guard_status'] == 'running':
            summary['guard_status'] = 'process_exited_before_guard_pass'
            summary['abort_reason'] = summary['abort_reason'] or 'repro_blocked_runtime_error'
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
        log.write(f"# guarded launch completed rc={rc} guard_status={summary['guard_status']} abort_reason={summary['abort_reason']}\n")

    if summary['guard_status'] != 'passed_startup_guard':
        return 70
    return summary.get('returncode') or 0


if __name__ == '__main__':
    raise SystemExit(main())
