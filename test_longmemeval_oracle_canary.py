#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent
SCRIPT_PATH = ROOT / 'docs' / 'eval' / 'results' / 'run_longmemeval_oracle_canary.py'
spec = importlib.util.spec_from_file_location('run_longmemeval_oracle_canary', SCRIPT_PATH)
longmem_canary = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(longmem_canary)


class LongMemEvalOracleCanaryTests(unittest.TestCase):
    def sample_rows(self):
        return [
            {
                'question_id': 'ku_abs',
                'question_type': 'knowledge-update',
                'question': 'What football did I collect?',
                'answer': 'The information provided is not enough.',
                'question_date': '2023/06/16 (Fri) 03:13',
                'haystack_dates': ['2023/05/22 (Mon) 11:02'],
                'haystack_session_ids': ['sess_abs_1'],
                'haystack_sessions': [[
                    {'role': 'user', 'content': 'I collected a signed baseball.', 'has_answer': False},
                    {'role': 'assistant', 'content': 'Nice baseball collection.', 'has_answer': False},
                ]],
                'answer_session_ids': ['sess_abs_1'],
            },
            {
                'question_id': 'multi_1',
                'question_type': 'multi-session',
                'question': 'Which two hobbies did I mention?',
                'answer': 'writing and hiking',
                'question_date': '2023/06/17 (Sat) 03:13',
                'haystack_dates': ['2023/05/20 (Sat) 10:00', '2023/05/21 (Sun) 10:00'],
                'haystack_session_ids': ['sess_multi_1', 'sess_multi_2'],
                'haystack_sessions': [
                    [{'role': 'user', 'content': 'I write short stories.', 'has_answer': True}],
                    [{'role': 'user', 'content': 'I hike on weekends.', 'has_answer': True}],
                ],
                'answer_session_ids': ['sess_multi_1', 'sess_multi_2'],
            },
            {
                'question_id': 'pref_1',
                'question_type': 'single-session-preference',
                'question': 'Can you recommend weekend events?',
                'answer': 'The user prefers Spanish and French language-practice cultural events.',
                'question_date': '2023/06/18 (Sun) 03:13',
                'haystack_dates': ['2023/05/23 (Tue) 12:00'],
                'haystack_session_ids': ['sess_pref_1'],
                'haystack_sessions': [[
                    {'role': 'user', 'content': 'I like cultural events where I can practice Spanish and French.', 'has_answer': True},
                ]],
                'answer_session_ids': ['sess_pref_1'],
            },
            {
                'question_id': 'temp_1',
                'question_type': 'temporal-reasoning',
                'question': 'How many days after Monday was the event?',
                'answer': '3 days',
                'question_date': '2023/06/19 (Mon) 03:13',
                'haystack_dates': ['2023/05/01 (Mon) 09:00', '2023/05/04 (Thu) 09:00'],
                'haystack_session_ids': ['sess_temp_1', 'sess_temp_2'],
                'haystack_sessions': [
                    [{'role': 'user', 'content': 'I finished the book on Monday.', 'has_answer': True}],
                    [{'role': 'user', 'content': 'I attended the related event on Thursday.', 'has_answer': True}],
                ],
                'answer_session_ids': ['sess_temp_1', 'sess_temp_2'],
            },
        ]

    def make_selection(self, rows=None, *, seed=None, prior_question_ids=None):
        rows = rows or self.sample_rows()
        seed = seed or 'memibrium-longmemeval-oracle-canary-2026-05-08-v1'
        selection = {
            'source_file': 'longmemeval_oracle.json',
            'hf_revision': longmem_canary.EXPECTED_HF_REVISION,
            'source_sha256': longmem_canary.EXPECTED_ORACLE_SHA256,
            'seed': seed,
            'counts': {
                'total': len(rows),
                'abstention': sum(1 for row in rows if row['question_id'].endswith('_abs')),
                'by_question_type': {
                    qtype: sum(1 for row in rows if row['question_type'] == qtype)
                    for qtype in sorted({row['question_type'] for row in rows})
                },
            },
            'rows': [
                {
                    'question_id': row['question_id'],
                    'question_type': row['question_type'],
                    'abstention': row['question_id'].endswith('_abs'),
                    'selection_hash': longmem_canary.sha256_text(f"{seed}:{row['question_id']}:{row['question']}"),
                    'selection_index': index,
                }
                for index, row in enumerate(rows, start=1)
            ],
        }
        if prior_question_ids is not None:
            selection['prior_slice_question_ids'] = list(prior_question_ids)
        return selection

    def test_validate_selection_requires_unique_rows_and_dataset_hash(self):
        dataset = self.sample_rows()[:2]
        selection = self.make_selection(dataset)

        proof = longmem_canary.validate_selection(dataset, selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

        self.assertEqual(proof['row_count'], 2)
        self.assertEqual(proof['abstention_count'], 1)
        self.assertEqual(proof['question_type_counts'], {'knowledge-update': 1, 'multi-session': 1})

        bad_selection = dict(selection, source_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'source_sha256_mismatch'):
            longmem_canary.validate_selection(dataset, bad_selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

        duplicate = json.loads(json.dumps(selection))
        duplicate['rows'][1]['question_id'] = 'ku_abs'
        with self.assertRaisesRegex(ValueError, 'duplicate_question_id'):
            longmem_canary.validate_selection(dataset, duplicate, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

    def test_build_oracle_prompt_preserves_evidence_identity_and_candidate_delta(self):
        row = self.sample_rows()[1]

        baseline = longmem_canary.build_oracle_prompt(row, treatment=False)
        treatment = longmem_canary.build_oracle_prompt(row, treatment=True)

        self.assertEqual(baseline['evidence_hash'], treatment['evidence_hash'])
        self.assertEqual(baseline['evidence_session_ids'], ['sess_multi_1', 'sess_multi_2'])
        self.assertIn('[session sess_multi_1 | turn 1 | user | has_answer=True]', baseline['prompt'])
        self.assertIn('Answer with the exact items', treatment['prompt'])
        self.assertNotIn('Answer with the exact items', baseline['prompt'])
        self.assertEqual(treatment['metadata_projection'], 'no-op')

    def test_category_contract_prompts_are_category_specific_without_changing_evidence(self):
        rows = {row['question_type']: row for row in self.sample_rows()}

        preference = longmem_canary.build_oracle_prompt(rows['single-session-preference'], condition='category_contract_v1')
        preference_baseline = longmem_canary.build_oracle_prompt(rows['single-session-preference'], condition='baseline')
        knowledge = longmem_canary.build_oracle_prompt(rows['knowledge-update'], condition='category_contract_v1')
        multi = longmem_canary.build_oracle_prompt(rows['multi-session'], condition='category_contract_v1')
        temporal = longmem_canary.build_oracle_prompt(rows['temporal-reasoning'], condition='category_contract_v1')

        self.assertEqual(preference['evidence_hash'], preference_baseline['evidence_hash'])
        self.assertEqual(preference['condition'], 'category_contract_v1')
        self.assertIn('recommender/advisor', preference['prompt'])
        self.assertIn('personalized suggestions', preference['prompt'])
        self.assertNotIn('merely because no concrete local events', preference_baseline['prompt'])
        self.assertIn('latest matching fact', knowledge['prompt'])
        self.assertIn('Do not substitute adjacent entities', knowledge['prompt'])
        self.assertIn('combine all relevant evidence items', multi['prompt'])
        self.assertIn('Use dates in the evidence', temporal['prompt'])
        self.assertNotIn('Answer with the exact items, counts, names, or dates requested', multi['prompt'])

    def test_prepare_category_contract_writes_placeholder_and_prompt_metadata_without_chat_calls(self):
        rows = self.sample_rows()
        selection = self.make_selection(rows)

        def forbidden_chat(*args, **kwargs):
            raise AssertionError('prep mode must not call chat')

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = longmem_canary.prepare_oracle_canary(
                rows,
                selection,
                out_dir,
                allow_answer_generation=False,
                condition='category_contract_v1',
                chat_fn=forbidden_chat,
            )
            metadata = json.loads((out_dir / 'longmemeval_oracle_canary_preparation_metadata.json').read_text())
            treatment_lines = (out_dir / 'longmemeval_oracle_canary_category_contract_v1_placeholder.jsonl').read_text().splitlines()

        self.assertEqual(result['mode'], 'preparation_only_no_answer_generation')
        self.assertEqual(result['condition'], 'category_contract_v1')
        self.assertEqual(metadata['condition'], 'category_contract_v1')
        self.assertEqual(metadata['candidate_prompts'][0]['condition'], 'category_contract_v1')
        self.assertEqual(json.loads(treatment_lines[0]), {'question_id': 'ku_abs', 'hypothesis': ''})

    def test_prepare_predictions_requires_placeholder_mode_without_explicit_launch(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = longmem_canary.prepare_oracle_canary(rows, selection, out_dir, allow_answer_generation=False)
            baseline_lines = (out_dir / 'longmemeval_oracle_canary_baseline_placeholder.jsonl').read_text().splitlines()
            treatment_lines = (out_dir / 'longmemeval_oracle_canary_treatment_placeholder.jsonl').read_text().splitlines()

        self.assertEqual(result['mode'], 'preparation_only_no_answer_generation')
        self.assertEqual(len(baseline_lines), 2)
        self.assertEqual(len(treatment_lines), 2)
        self.assertEqual(json.loads(baseline_lines[0]), {'question_id': 'ku_abs', 'hypothesis': ''})
        self.assertEqual(json.loads(treatment_lines[0]), {'question_id': 'ku_abs', 'hypothesis': ''})

    def test_prepare_oracle_canary_scored_launch_writes_predictions_evals_and_summary(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows)
        calls = []

        def fake_chat(messages, *, model, max_tokens):
            content = messages[-1]['content']
            calls.append({'model': model, 'max_tokens': max_tokens, 'content': content})
            if 'Is the model response correct?' in content or 'Does the model correctly identify' in content:
                return 'yes' if 'writing and hiking' in content or 'information provided is not enough' in content else 'no'
            if 'Which two hobbies' in content:
                return 'writing and hiking'
            return 'The information provided is not enough.'

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = longmem_canary.prepare_oracle_canary(
                rows,
                selection,
                out_dir,
                allow_answer_generation=True,
                chat_fn=fake_chat,
                answer_model='answer-model',
                judge_model='judge-model',
                endpoint_metadata={'host': 'example.test'},
            )
            baseline_predictions = [json.loads(line) for line in (out_dir / 'longmemeval_oracle_canary_baseline_predictions.jsonl').read_text().splitlines()]
            treatment_predictions = [json.loads(line) for line in (out_dir / 'longmemeval_oracle_canary_treatment_predictions.jsonl').read_text().splitlines()]
            baseline_evals = [json.loads(line) for line in (out_dir / 'longmemeval_oracle_canary_baseline_eval_results.jsonl').read_text().splitlines()]
            summary = json.loads((out_dir / 'longmemeval_oracle_canary_scored_summary.json').read_text())

        self.assertEqual(result['mode'], 'scored_oracle_canary')
        self.assertEqual([row['hypothesis'] for row in baseline_predictions], ['The information provided is not enough.', 'writing and hiking'])
        self.assertEqual([row['question_id'] for row in treatment_predictions], ['ku_abs', 'multi_1'])
        self.assertEqual(baseline_evals[0]['autoeval_label']['model'], 'judge-model')
        self.assertEqual(summary['baseline']['accuracy'], 1.0)
        self.assertEqual(summary['treatment']['accuracy'], 1.0)
        self.assertEqual(summary['row_count'], 2)
        self.assertTrue(any(call['model'] == 'answer-model' for call in calls))
        self.assertTrue(any(call['model'] == 'judge-model' for call in calls))

    def test_validate_selection_recomputes_selection_hash_and_quota_groups(self):
        dataset = self.sample_rows()
        selection = self.make_selection(dataset)

        selection['rows'][0]['selection_hash'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'selection_hash_mismatch:ku_abs'):
            longmem_canary.validate_selection(dataset, selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

        selection = self.make_selection(dataset)
        selection['selection_rule'] = 'reserve one slot for abstention rows'
        selection['rows'][0]['selection_group'] = 'knowledge-update:reserved-abstention'
        selection['rows'][1]['selection_group'] = 'multi-session:wrong-fill'
        with self.assertRaisesRegex(ValueError, 'selection_group_mismatch:multi_1'):
            longmem_canary.validate_selection(dataset, selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

    def test_validate_selection_accepts_hash_fill_groups_when_type_has_no_abstention(self):
        dataset = [
            dict(
                self.sample_rows()[0],
                question_id='assistant_1',
                question_type='single-session-assistant',
                question='What did you suggest?',
            ),
            dict(
                self.sample_rows()[1],
                question_id='assistant_2',
                question_type='single-session-assistant',
                question='What else did you suggest?',
            ),
        ]
        selection = self.make_selection(dataset)
        selection['counts'] = {'total': 2, 'abstention': 0, 'by_question_type': {'single-session-assistant': 2}}
        selection['rows'][0]['selection_group'] = 'single-session-assistant:hash-fill'
        selection['rows'][1]['selection_group'] = 'single-session-assistant:hash-fill'

        proof = longmem_canary.validate_selection(dataset, selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

        self.assertEqual(proof['question_type_counts'], {'single-session-assistant': 2})

    def test_validate_selection_rejects_wrong_seed_and_non_preregistered_extra_group(self):
        dataset = self.sample_rows()
        selection = self.make_selection(dataset)
        selection['seed'] = 'wrong-seed'
        with self.assertRaisesRegex(ValueError, 'selection_seed_mismatch'):
            longmem_canary.validate_selection(dataset, selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

        selection = self.make_selection(dataset)
        selection['rows'][1]['selection_group'] = 'multi-session:extra-product-telemetry'
        with self.assertRaisesRegex(ValueError, 'selection_group_mismatch:multi_1'):
            longmem_canary.validate_selection(dataset, selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

        selection = self.make_selection(dataset)
        selection['rows'][0]['selection_group'] = 'knowledge-update:extra-product-telemetry'
        with self.assertRaisesRegex(ValueError, 'selection_group_mismatch:ku_abs'):
            longmem_canary.validate_selection(dataset, selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

        selection = self.make_selection(dataset)
        selection['rows'][1]['selection_group'] = 'multi-session:reserved-abstention'
        with self.assertRaisesRegex(ValueError, 'selection_group_mismatch:multi_1'):
            longmem_canary.validate_selection(dataset, selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

    def test_second_slice_selection_uses_distinct_seed_and_rejects_prior_overlap(self):
        dataset = self.sample_rows()
        second_seed = 'memibrium-longmemeval-oracle-canary-2026-05-08-v2'
        selection = self.make_selection(
            dataset[1:],
            seed=second_seed,
            prior_question_ids=['ku_abs'],
        )
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        selection['selection_rule'] = 'second hash-stratified slice excluding prior-slice question IDs'

        proof = longmem_canary.validate_selection(dataset, selection, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

        self.assertEqual(proof['seed'], second_seed)
        self.assertEqual(proof['slice_id'], 'longmemeval_oracle_canary_25_second_slice_20260508')
        self.assertEqual(proof['prior_slice_overlap_count'], 0)
        self.assertEqual(proof['row_count'], 3)

        overlapping = json.loads(json.dumps(selection))
        overlapping['rows'][0]['question_id'] = 'ku_abs'
        overlapping['rows'][0]['question_type'] = 'knowledge-update'
        overlapping['rows'][0]['abstention'] = True
        overlapping['rows'][0]['selection_hash'] = longmem_canary.sha256_text(f"{second_seed}:ku_abs:What football did I collect?")
        with self.assertRaisesRegex(ValueError, 'prior_slice_overlap:ku_abs'):
            longmem_canary.validate_selection(dataset, overlapping, dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256)

    def test_preparation_metadata_records_second_slice_gates_and_forbids_chat(self):
        rows = self.sample_rows()
        second_seed = 'memibrium-longmemeval-oracle-canary-2026-05-08-v2'
        selection = self.make_selection(rows, seed=second_seed, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        selection['preregistered_gates'] = longmem_canary.SECOND_SLICE_GATES

        def forbidden_chat(*args, **kwargs):
            raise AssertionError('second-slice prep must not call chat')

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = longmem_canary.prepare_oracle_canary(
                rows,
                selection,
                out_dir,
                allow_answer_generation=False,
                condition='category_contract_v1',
                chat_fn=forbidden_chat,
            )
            metadata = json.loads((out_dir / 'longmemeval_oracle_canary_preparation_metadata.json').read_text())

        self.assertEqual(result['mode'], 'preparation_only_no_answer_generation')
        self.assertEqual(metadata['selection_proof']['seed'], second_seed)
        self.assertEqual(metadata['preregistered_gates']['total_score'], 'category_contract_v1 >= baseline on the same slice')
        self.assertEqual(metadata['preregistered_gates']['moved_row_win_loss'], 'moved_rows >= 3 and recovered/regressed >= 2:1')
        self.assertIn('preference_baseline_wrong == 0', metadata['preregistered_gates']['preference_recovery_zero_denominator'])
        self.assertIn('minimum ratio that still constitutes evidence', metadata['preregistered_gates']['moved_row_win_loss_rationale'])
        self.assertNotIn('1:1', json.dumps(metadata['preregistered_gates']))

    def make_eval_rows(self, labels):
        return [
            {'question_id': question_id, 'autoeval_label': {'label': label}}
            for question_id, label in labels
        ]

    def test_second_slice_gate_evaluator_predeclares_preference_zero_denominator(self):
        rows = [
            dict(self.sample_rows()[0], question_id='ku_1', question_type='knowledge-update'),
            dict(self.sample_rows()[2], question_id='pref_1', question_type='single-session-preference'),
            dict(self.sample_rows()[2], question_id='pref_2', question_type='single-session-preference'),
            dict(self.sample_rows()[2], question_id='pref_3', question_type='single-session-preference'),
            dict(self.sample_rows()[2], question_id='pref_4', question_type='single-session-preference'),
        ]
        baseline = self.make_eval_rows([
            ('ku_1', True),
            ('pref_1', True),
            ('pref_2', True),
            ('pref_3', True),
            ('pref_4', True),
        ])
        treatment = self.make_eval_rows([
            ('ku_1', True),
            ('pref_1', True),
            ('pref_2', True),
            ('pref_3', True),
            ('pref_4', True),
        ])

        result = longmem_canary.evaluate_second_slice_gates(rows, baseline, treatment)

        self.assertTrue(result['gates']['preference_recovery']['pass'])
        self.assertEqual(result['gates']['preference_recovery']['reason'], 'zero_denominator_no_recovery_needed')
        self.assertEqual(result['preference']['baseline_wrong'], 0)

    def test_second_slice_gate_evaluator_rejects_zero_or_too_few_moved_rows(self):
        rows = [
            dict(self.sample_rows()[0], question_id='ku_1', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='multi_1', question_type='multi-session'),
            dict(self.sample_rows()[2], question_id='pref_1', question_type='single-session-preference'),
        ]
        baseline = self.make_eval_rows([('ku_1', True), ('multi_1', False), ('pref_1', False)])
        treatment = self.make_eval_rows([('ku_1', True), ('multi_1', False), ('pref_1', True)])

        result = longmem_canary.evaluate_second_slice_gates(rows, baseline, treatment)

        self.assertEqual(result['paired_outcomes']['moved_rows'], 1)
        self.assertFalse(result['gates']['moved_row_stability']['pass'])
        self.assertEqual(result['gates']['moved_row_stability']['reason'], 'minimum_moved_rows_not_met')

    def test_second_slice_gate_evaluator_requires_two_to_one_moved_row_ratio(self):
        rows = [
            dict(self.sample_rows()[0], question_id='ku_1', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='multi_1', question_type='multi-session'),
            dict(self.sample_rows()[2], question_id='pref_1', question_type='single-session-preference'),
            dict(self.sample_rows()[3], question_id='temp_1', question_type='temporal-reasoning'),
            dict(self.sample_rows()[1], question_id='multi_2', question_type='multi-session'),
            dict(self.sample_rows()[2], question_id='pref_2', question_type='single-session-preference'),
        ]
        passing = longmem_canary.evaluate_second_slice_gates(
            rows,
            self.make_eval_rows([('ku_1', True), ('multi_1', False), ('pref_1', False), ('temp_1', True), ('multi_2', True), ('pref_2', True)]),
            self.make_eval_rows([('ku_1', True), ('multi_1', True), ('pref_1', True), ('temp_1', False), ('multi_2', True), ('pref_2', True)]),
        )
        failing = longmem_canary.evaluate_second_slice_gates(
            rows,
            self.make_eval_rows([('ku_1', True), ('multi_1', False), ('pref_1', False), ('temp_1', True), ('multi_2', True), ('pref_2', False)]),
            self.make_eval_rows([('ku_1', True), ('multi_1', True), ('pref_1', False), ('temp_1', False), ('multi_2', False), ('pref_2', True)]),
        )

        self.assertTrue(passing['gates']['moved_row_stability']['pass'])
        self.assertEqual(passing['paired_outcomes']['recovered'], 2)
        self.assertEqual(passing['paired_outcomes']['regressed'], 1)
        self.assertFalse(failing['gates']['moved_row_stability']['pass'])
        self.assertEqual(failing['gates']['moved_row_stability']['reason'], 'recovered_regressed_ratio_below_2_to_1')

    def test_second_slice_gate_evaluator_flags_category_collapse_and_knowledge_update(self):
        rows = [
            dict(self.sample_rows()[0], question_id='ku_1', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='multi_1', question_type='multi-session'),
            dict(self.sample_rows()[1], question_id='multi_2', question_type='multi-session'),
            dict(self.sample_rows()[2], question_id='pref_1', question_type='single-session-preference'),
        ]
        baseline = self.make_eval_rows([('ku_1', True), ('multi_1', True), ('multi_2', True), ('pref_1', False)])
        treatment = self.make_eval_rows([('ku_1', False), ('multi_1', False), ('multi_2', False), ('pref_1', True)])

        result = longmem_canary.evaluate_second_slice_gates(rows, baseline, treatment)

        self.assertFalse(result['gates']['knowledge_update']['pass'])
        self.assertFalse(result['gates']['category_collapse']['pass'])
        self.assertEqual(result['gates']['category_collapse']['drops'], {'multi-session': -2})

    def test_offline_gate_report_loads_eval_jsonl_and_writes_report_without_chat(self):
        rows = [
            *self.sample_rows()[:4],
            dict(self.sample_rows()[1], question_id='multi_2', question_type='multi-session'),
            dict(self.sample_rows()[2], question_id='pref_2', question_type='single-session-preference'),
            dict(self.sample_rows()[3], question_id='temp_2', question_type='temporal-reasoning'),
        ]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        baseline_evals = self.make_eval_rows([('ku_abs', True), ('multi_1', False), ('pref_1', False), ('temp_1', True), ('multi_2', True), ('pref_2', True), ('temp_2', True)])
        treatment_evals = self.make_eval_rows([('ku_abs', True), ('multi_1', True), ('pref_1', True), ('temp_1', False), ('multi_2', False), ('pref_2', True), ('temp_2', True)])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline_path = tmp_path / 'baseline_eval.jsonl'
            treatment_path = tmp_path / 'treatment_eval.jsonl'
            report_path = tmp_path / 'gate_report.json'
            longmem_canary.write_jsonl(baseline_path, baseline_evals)
            longmem_canary.write_jsonl(treatment_path, treatment_evals)

            report = longmem_canary.write_second_slice_gate_report(
                rows,
                selection,
                baseline_path,
                treatment_path,
                report_path,
                dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256,
            )
            written = json.loads(report_path.read_text())

        self.assertEqual(report['mode'], 'second_slice_gate_evaluation_offline')
        self.assertEqual(written['mode'], 'second_slice_gate_evaluation_offline')
        self.assertEqual(written['selection_proof']['seed'], longmem_canary.SECOND_SLICE_SELECTION_SEED)
        self.assertEqual(written['input_files']['baseline_eval_file'], str(baseline_path))
        self.assertEqual(written['paired_outcomes']['moved_rows'], 4)
        self.assertEqual(written['communication_boundary'], 'oracle answer-side mechanism evidence only; retrieval untested')
        self.assertFalse(written['gates']['overall']['pass'])

    def test_offline_gate_report_rejects_duplicate_eval_rows_before_scoring(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        baseline = self.make_eval_rows([('ku_abs', True), ('multi_1', False), ('multi_1', True)])
        treatment = self.make_eval_rows([('ku_abs', True), ('multi_1', True)])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline_path = tmp_path / 'baseline_eval.jsonl'
            treatment_path = tmp_path / 'treatment_eval.jsonl'
            report_path = tmp_path / 'gate_report.json'
            longmem_canary.write_jsonl(baseline_path, baseline)
            longmem_canary.write_jsonl(treatment_path, treatment)

            with self.assertRaisesRegex(ValueError, 'duplicate_baseline_eval_rows:multi_1'):
                longmem_canary.write_second_slice_gate_report(
                    rows,
                    selection,
                    baseline_path,
                    treatment_path,
                    report_path,
                    dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256,
                )

        self.assertFalse(report_path.exists())

    def test_offline_gate_report_rejects_missing_extra_and_missing_labels(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        valid_treatment = self.make_eval_rows([('ku_abs', True), ('multi_1', True)])

        cases = [
            ('missing_baseline_eval_rows:multi_1', self.make_eval_rows([('ku_abs', True)])),
            ('unknown_baseline_eval_rows:extra_1', self.make_eval_rows([('ku_abs', True), ('multi_1', False), ('extra_1', True)])),
            ('missing_autoeval_label:multi_1', [{'question_id': 'ku_abs', 'autoeval_label': {'label': True}}, {'question_id': 'multi_1'}]),
            ('invalid_autoeval_label:multi_1', [{'question_id': 'ku_abs', 'autoeval_label': {'label': True}}, {'question_id': 'multi_1', 'autoeval_label': {'label': 'maybe'}}]),
        ]

        for expected_error, baseline in cases:
            with self.subTest(expected_error=expected_error):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    baseline_path = tmp_path / 'baseline_eval.jsonl'
                    treatment_path = tmp_path / 'treatment_eval.jsonl'
                    report_path = tmp_path / 'gate_report.json'
                    longmem_canary.write_jsonl(baseline_path, baseline)
                    longmem_canary.write_jsonl(treatment_path, valid_treatment)

                    with self.assertRaisesRegex(ValueError, expected_error):
                        longmem_canary.write_second_slice_gate_report(
                            rows,
                            selection,
                            baseline_path,
                            treatment_path,
                            report_path,
                            dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256,
                        )
                    self.assertFalse(report_path.exists())

    def test_parse_args_supports_offline_gate_report_without_allow_answer_generation(self):
        args = longmem_canary.parse_args([
            '--offline-gate-report',
            '--baseline-eval-file', 'baseline.jsonl',
            '--treatment-eval-file', 'treatment.jsonl',
        ])

        self.assertTrue(args.offline_gate_report)
        self.assertFalse(args.allow_answer_generation)
        self.assertEqual(args.baseline_eval_file, Path('baseline.jsonl'))
        self.assertEqual(args.treatment_eval_file, Path('treatment.jsonl'))

    def test_second_slice_gates_define_zero_denominators_and_minimum_movement(self):
        gates = longmem_canary.SECOND_SLICE_GATES

        self.assertEqual(
            gates['preference_recovery_zero_denominator'],
            'if preference_baseline_wrong == 0, preference gate is automatically satisfied because no recovery is needed',
        )
        self.assertEqual(gates['moved_row_minimum'], 'moved_rows = recovered + regressed >= 3')
        self.assertEqual(gates['zero_movement'], 'moved_rows == 0 fails the replication/mechanism gate')
        self.assertEqual(gates['moved_row_win_loss'], 'moved_rows >= 3 and recovered/regressed >= 2:1')
        self.assertIn('minimum ratio that still constitutes evidence', gates['moved_row_win_loss_rationale'])
        self.assertNotIn('1:1', json.dumps(gates))

    def test_retrieval_bridge_phase_a_gate_definitions_match_preregistration(self):
        gates = longmem_canary.RETRIEVAL_BRIDGE_PHASE_A_GATES

        self.assertEqual(gates['coverage_audit_completeness'], '25/25 rows have a coverage class and preserved retrieval artifacts')
        self.assertEqual(gates['retrieval_operational_success'], 'no uncaught 500s, serialization errors, or missing JSON fields')
        self.assertEqual(gates['preference_coverage'], 'at least 3/4 single-session-preference rows are gold_supported or gold_supported_with_conflict')
        self.assertEqual(gates['knowledge_update_coverage'], 'at least 3/5 knowledge-update rows are gold_supported, gold_supported_with_conflict, or partial_support; stale_only counted separately')
        self.assertEqual(gates['abstention_contamination'], 'no more than 1/4 abstention rows may be unanswerable_contaminated')
        self.assertEqual(gates['evidence_identity'], 'every answerable row preserves source refs sufficient for artifact-only review')
        self.assertEqual(gates['substrate_comparability'], 'pre-answer substrate comparability met per launch plan: all answerable rows have a substrate-comparable retrieval result')
        self.assertNotIn('answer generation', json.dumps(gates).lower())
        self.assertNotIn('judge', json.dumps(gates).lower())

    def test_prepare_retrieval_bridge_writes_phase_a_placeholders_without_runtime_or_model_calls(self):
        rows = self.sample_rows()
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'

        def forbidden_retrieval(*args, **kwargs):
            raise AssertionError('retrieval bridge prep must not call Memibrium runtime')

        def forbidden_chat(*args, **kwargs):
            raise AssertionError('retrieval bridge prep must not call chat/model/judge')

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = longmem_canary.prepare_retrieval_bridge_canary(
                rows,
                selection,
                out_dir,
                retrieval_fn=forbidden_retrieval,
                chat_fn=forbidden_chat,
            )
            metadata = json.loads((out_dir / 'longmemeval_retrieval_bridge_preparation_metadata.json').read_text())
            ingest_manifest = json.loads((out_dir / 'ingest_manifest_placeholder.json').read_text())
            retrieval_rows = [
                json.loads(line)
                for line in (out_dir / 'retrieval_results_placeholder.jsonl').read_text().splitlines()
            ]
            coverage_audit = json.loads((out_dir / 'retrieval_coverage_audit_placeholder.json').read_text())
            baseline_lines = (out_dir / 'answer_baseline_predictions_blocked_placeholder.jsonl').read_text().splitlines()
            treatment_lines = (out_dir / 'answer_category_contract_v1_predictions_blocked_placeholder.jsonl').read_text().splitlines()

        self.assertEqual(result['mode'], 'retrieval_bridge_preparation_only_no_runtime_calls')
        self.assertEqual(result['condition'], 'longmemeval_bridge_v1_retrieval_plus_category_contract_v1')
        self.assertEqual(result['domain'], 'longmemeval-bridge-v1-20260508-second-slice')
        self.assertEqual(metadata['selection_proof']['seed'], longmem_canary.SECOND_SLICE_SELECTION_SEED)
        self.assertEqual(metadata['phase'], 'phase_a_retrieval_coverage_preparation')
        self.assertEqual(metadata['phase_a_gates'], longmem_canary.RETRIEVAL_BRIDGE_PHASE_A_GATES)
        self.assertEqual(metadata['communication_boundary'], 'retrieval bridge preparation only; no retrieval/product benchmark claim')
        self.assertIn('no LongMemEval conversation ingestion', metadata['guardrails'])
        self.assertIn('no Memibrium recall/context calls', metadata['guardrails'])
        self.assertIn('no DB/Docker/runtime mutation', metadata['guardrails'])
        self.assertIn('no answer model calls', metadata['guardrails'])
        self.assertIn('no judge calls', metadata['guardrails'])
        self.assertEqual(metadata['answer_conditions']['baseline']['retrieved_evidence_source'], 'shared_retrieval_results_after_phase_a')
        self.assertEqual(metadata['answer_conditions']['treatment']['condition'], 'category_contract_v1')
        self.assertEqual(metadata['answer_conditions']['evidence_identity_requirement'], 'baseline and treatment must share identical retrieved evidence per question_id')
        self.assertEqual(ingest_manifest['memory_ids_created'], [])
        self.assertEqual(ingest_manifest['domain'], 'longmemeval-bridge-v1-20260508-second-slice')
        self.assertEqual(ingest_manifest['selected_question_ids'], ['ku_abs', 'multi_1', 'pref_1', 'temp_1'])
        self.assertEqual(ingest_manifest['source_session_ids'], ['sess_abs_1', 'sess_multi_1', 'sess_multi_2', 'sess_pref_1', 'sess_temp_1', 'sess_temp_2'])
        self.assertEqual(retrieval_rows[0]['question_id'], 'ku_abs')
        self.assertEqual(retrieval_rows[0]['retrieval_status'], 'not_run_runtime_not_authorized')
        self.assertEqual(retrieval_rows[0]['retrieved_memory_ids'], [])
        self.assertIsNone(retrieval_rows[0]['coverage_class'])
        self.assertEqual(coverage_audit['coverage_status'], 'not_evaluated_retrieval_not_run')
        self.assertEqual(coverage_audit['phase_a_stop_rule'], 'if coverage is missing, stop before answer generation')
        self.assertEqual(len(coverage_audit['rows']), 4)
        self.assertEqual(json.loads(baseline_lines[0]), {'question_id': 'ku_abs', 'hypothesis': ''})
        self.assertEqual(json.loads(treatment_lines[0]), {'question_id': 'ku_abs', 'hypothesis': ''})

    def test_prepare_retrieval_bridge_rejects_launch_side_effect_flags_before_writing(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        cases = [
            {'allow_runtime_retrieval': True},
            {'allow_answer_generation': True},
            {'allow_judge_calls': True},
        ]

        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with tempfile.TemporaryDirectory() as tmp:
                    out_dir = Path(tmp)
                    with self.assertRaisesRegex(ValueError, 'retrieval_bridge_launch_not_authorized'):
                        longmem_canary.prepare_retrieval_bridge_canary(rows, selection, out_dir, **kwargs)
                    self.assertEqual(list(out_dir.iterdir()), [])

        wrong_seed = self.make_selection(rows, seed=longmem_canary.EXPECTED_SELECTION_SEED, prior_question_ids=[])
        wrong_seed['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'retrieval_bridge_requires_second_slice_seed'):
                longmem_canary.prepare_retrieval_bridge_canary(rows, wrong_seed, Path(tmp))

    def test_parse_args_supports_retrieval_bridge_preparation_only(self):
        args = longmem_canary.parse_args([
            '--prepare-retrieval-bridge',
            '--selection', 'docs/eval/results/longmemeval_oracle_canary_25_second_slice_selection_20260508.json',
            '--out-dir', 'bridge-out',
        ])

        self.assertTrue(args.prepare_retrieval_bridge)
        self.assertFalse(args.allow_answer_generation)
        self.assertFalse(args.allow_runtime_retrieval)
        self.assertFalse(args.allow_judge_calls)
        self.assertEqual(args.out_dir, Path('bridge-out'))

    def make_retrieval_rows(self, statuses):
        return [
            {
                'question_id': question_id,
                'question_type': question_type,
                'coverage_class': coverage_class,
                'retrieval_status': retrieval_status,
                'retrieved_memory_ids': memory_ids,
                'source_refs': source_refs,
                'fallback_error_flags': error_flags,
                'timestamp_source_metadata': [{
                    'recall_telemetry_present': retrieval_status == 'ok',
                    'substrate_readiness_present': retrieval_status == 'ok',
                    'substrate_readiness': {'schema': 'memibrium.substrate_readiness.v1'} if retrieval_status == 'ok' else None,
                }],
                'candidate_pool': {
                    'schema': 'memibrium.recall.candidate_pool.v1',
                    'candidate_group_count': 1 if memory_ids else 0,
                    'groups': [{'source': 'test', 'count': len(memory_ids), 'top_ids': memory_ids[:10]}] if memory_ids else [],
                    'total_candidates_before_merge': len(memory_ids),
                    'total_merged_candidates': len(memory_ids),
                    'ranked_returned_count': len(memory_ids),
                    'top_ranked_ids': memory_ids[:10],
                },
                'score_components': [
                    {'id': memory_id, 'final_score': 1.0, 'retrieval_sources': ['test']}
                    for memory_id in memory_ids
                ],
                'source_ref_analysis': {'supporting_source_refs': source_refs},
                'coverage_rationale': 'test_fixture_coverage',
            }
            for question_id, question_type, coverage_class, retrieval_status, memory_ids, source_refs, error_flags in statuses
        ]

    def test_retrieval_bridge_phase_a_evaluator_passes_complete_supported_coverage(self):
        rows = [
            dict(self.sample_rows()[0], question_id='ku_1', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='ku_2', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='ku_3', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='ku_4', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='ku_5', question_type='knowledge-update'),
            dict(self.sample_rows()[2], question_id='pref_1', question_type='single-session-preference'),
            dict(self.sample_rows()[2], question_id='pref_2', question_type='single-session-preference'),
            dict(self.sample_rows()[2], question_id='pref_3', question_type='single-session-preference'),
            dict(self.sample_rows()[2], question_id='pref_4', question_type='single-session-preference'),
            dict(self.sample_rows()[0], question_id='abs_1_abs', question_type='multi-session'),
            dict(self.sample_rows()[0], question_id='abs_2_abs', question_type='knowledge-update'),
            dict(self.sample_rows()[0], question_id='abs_3_abs', question_type='single-session-user'),
            dict(self.sample_rows()[0], question_id='abs_4_abs', question_type='temporal-reasoning'),
        ]
        retrieval_rows = self.make_retrieval_rows([
            ('ku_1', 'knowledge-update', 'gold_supported', 'ok', ['m1'], ['s1:t1'], []),
            ('ku_2', 'knowledge-update', 'gold_supported_with_conflict', 'ok', ['m2'], ['s2:t1'], []),
            ('ku_3', 'knowledge-update', 'partial_support', 'ok', ['m3'], ['s3:t1'], []),
            ('ku_4', 'knowledge-update', 'stale_only', 'ok', ['m4'], ['s4:t1'], []),
            ('ku_5', 'knowledge-update', 'unsupported', 'ok', [], [], []),
            ('pref_1', 'single-session-preference', 'gold_supported', 'ok', ['m6'], ['s6:t1'], []),
            ('pref_2', 'single-session-preference', 'gold_supported_with_conflict', 'ok', ['m7'], ['s7:t1'], []),
            ('pref_3', 'single-session-preference', 'gold_supported', 'ok', ['m8'], ['s8:t1'], []),
            ('pref_4', 'single-session-preference', 'partial_support', 'ok', ['m9'], ['s9:t1'], []),
            ('abs_1_abs', 'multi-session', 'unanswerable_supported', 'ok', ['m10'], ['s10:t1'], []),
            ('abs_2_abs', 'knowledge-update', 'unanswerable_contaminated', 'ok', ['m11'], ['s11:t1'], []),
            ('abs_3_abs', 'single-session-user', 'unanswerable_supported', 'ok', ['m12'], ['s12:t1'], []),
            ('abs_4_abs', 'temporal-reasoning', 'unanswerable_supported', 'ok', ['m13'], ['s13:t1'], []),
        ])

        report = longmem_canary.evaluate_retrieval_bridge_phase_a_gates(rows, retrieval_rows)

        self.assertTrue(report['gates']['overall']['pass'])
        self.assertEqual(report['coverage_counts']['total'], 13)
        self.assertEqual(report['preference']['adequate_coverage'], 3)
        self.assertEqual(report['knowledge_update']['adequate_coverage'], 3)
        self.assertEqual(report['abstention']['unanswerable_contaminated'], 1)
        self.assertEqual(report['stale_only_question_ids'], ['ku_4'])
        self.assertEqual(report['phase_b_recommendation'], 'phase_a_passed_answer_generation_still_requires_explicit_approval')

    def test_retrieval_bridge_phase_a_evaluator_fails_non_comparable_answerable_rows(self):
        rows = self.sample_rows()[:2]
        retrieval_rows = self.make_retrieval_rows([
            ('ku_abs', 'knowledge-update', 'unanswerable_supported', 'ok', ['m1'], ['s1:t1'], []),
            ('multi_1', 'multi-session', 'gold_supported', 'ok', ['m2'], ['s2:t1'], []),
        ])
        retrieval_rows[1]['timestamp_source_metadata'] = [{
            'recall_telemetry_present': True,
            'substrate_readiness_present': False,
        }]

        report = longmem_canary.evaluate_retrieval_bridge_phase_a_gates(rows, retrieval_rows)

        self.assertFalse(report['gates']['substrate_comparability']['pass'])
        self.assertIn('multi_1', report['gates']['substrate_comparability']['non_comparable_question_ids'])
        self.assertFalse(report['gates']['overall']['pass'])

    def test_retrieval_bridge_phase_a_evaluator_fails_missing_rows_errors_and_identity(self):
        rows = self.sample_rows()[:3]
        retrieval_rows = self.make_retrieval_rows([
            ('ku_abs', 'knowledge-update', 'gold_supported', 'ok', ['m1'], ['s1:t1'], []),
            ('multi_1', 'multi-session', 'gold_supported', 'error_500', ['m2'], [], ['500']),
        ])

        report = longmem_canary.evaluate_retrieval_bridge_phase_a_gates(rows, retrieval_rows)

        self.assertFalse(report['gates']['overall']['pass'])
        self.assertFalse(report['gates']['coverage_audit_completeness']['pass'])
        self.assertIn('pref_1', report['gates']['coverage_audit_completeness']['missing_question_ids'])
        self.assertFalse(report['gates']['retrieval_operational_success']['pass'])
        self.assertFalse(report['gates']['evidence_identity']['pass'])
        self.assertEqual(report['phase_b_recommendation'], 'stop_before_answer_generation_phase_a_failed')

        duplicate = retrieval_rows + [dict(retrieval_rows[0])]
        with self.assertRaisesRegex(ValueError, 'duplicate_retrieval_rows:ku_abs'):
            longmem_canary.evaluate_retrieval_bridge_phase_a_gates(rows, duplicate)

        invalid = [dict(retrieval_rows[0], coverage_class='made_up_class')]
        with self.assertRaisesRegex(ValueError, 'invalid_coverage_class:ku_abs'):
            longmem_canary.evaluate_retrieval_bridge_phase_a_gates(rows[:1], invalid)

    def test_retrieval_bridge_phase_a_evaluator_fails_incomplete_runtime_diagnostics(self):
        rows = self.sample_rows()[:1]
        retrieval_rows = self.make_retrieval_rows([
            ('ku_abs', 'knowledge-update', 'gold_supported', 'ok', ['m1'], ['s1:t1'], []),
        ])
        retrieval_rows[0]['timestamp_source_metadata'] = [{'recall_telemetry_present': True}]
        retrieval_rows[0]['candidate_pool'] = {}
        retrieval_rows[0]['score_components'] = []
        retrieval_rows[0].pop('coverage_rationale')

        report = longmem_canary.evaluate_retrieval_bridge_phase_a_gates(rows, retrieval_rows)

        self.assertFalse(report['gates']['diagnostics_completeness']['pass'])
        self.assertFalse(report['gates']['overall']['pass'])
        issue_row = report['gates']['diagnostics_completeness']['issue_rows'][0]
        self.assertEqual(issue_row['question_id'], 'ku_abs')
        self.assertIn('candidate_pool_missing_or_incomplete', issue_row['issues'])
        self.assertIn('score_components_missing', issue_row['issues'])
        self.assertIn('substrate_readiness_not_explicit', issue_row['issues'])
        self.assertIn('coverage_rationale_missing', issue_row['issues'])

    def test_retrieval_bridge_phase_a_evaluator_allows_not_run_placeholders_as_failed_gate(self):
        rows = self.sample_rows()[:2]
        retrieval_rows = [
            {
                'question_id': row['question_id'],
                'question_type': row['question_type'],
                'coverage_class': None,
                'retrieval_status': 'not_run_runtime_not_authorized',
                'retrieved_memory_ids': [],
                'source_refs': [],
                'fallback_error_flags': [],
            }
            for row in rows
        ]

        report = longmem_canary.evaluate_retrieval_bridge_phase_a_gates(rows, retrieval_rows)

        self.assertFalse(report['gates']['overall']['pass'])
        self.assertEqual(
            report['gates']['coverage_audit_completeness']['incomplete_coverage_question_ids'],
            ['ku_abs', 'multi_1'],
        )
        self.assertFalse(report['gates']['retrieval_operational_success']['pass'])
        self.assertEqual(report['phase_b_recommendation'], 'stop_before_answer_generation_phase_a_failed')

    def test_write_retrieval_bridge_phase_a_report_loads_jsonl_and_writes_offline_report(self):
        rows = self.sample_rows()
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        retrieval_rows = self.make_retrieval_rows([
            ('ku_abs', 'knowledge-update', 'gold_supported', 'ok', ['m1'], ['s1:t1'], []),
            ('multi_1', 'multi-session', 'gold_supported', 'ok', ['m2'], ['s2:t1'], []),
            ('pref_1', 'single-session-preference', 'gold_supported', 'ok', ['m3'], ['s3:t1'], []),
            ('temp_1', 'temporal-reasoning', 'unsupported', 'ok', [], [], []),
        ])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            retrieval_path = tmp_path / 'retrieval_results.jsonl'
            report_path = tmp_path / 'phase_a_report.json'
            longmem_canary.write_jsonl(retrieval_path, retrieval_rows)
            report = longmem_canary.write_retrieval_bridge_phase_a_report(
                rows,
                selection,
                retrieval_path,
                report_path,
                dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256,
            )
            written = json.loads(report_path.read_text())

        self.assertEqual(report['mode'], 'retrieval_bridge_phase_a_gate_evaluation_offline')
        self.assertEqual(written['mode'], 'retrieval_bridge_phase_a_gate_evaluation_offline')
        self.assertEqual(written['selection_proof']['seed'], longmem_canary.SECOND_SLICE_SELECTION_SEED)
        self.assertEqual(written['input_files']['retrieval_results_file'], str(retrieval_path))
        self.assertEqual(written['communication_boundary'], 'retrieval coverage evidence only; no answer/product benchmark claim')
        self.assertFalse(written['gates']['overall']['pass'])

    def test_parse_args_supports_retrieval_bridge_phase_a_report_without_launch(self):
        args = longmem_canary.parse_args([
            '--retrieval-bridge-phase-a-report',
            '--retrieval-results-file', 'retrieval.jsonl',
            '--phase-a-report-file', 'phase_a.json',
        ])

        self.assertTrue(args.retrieval_bridge_phase_a_report)
        self.assertEqual(args.retrieval_results_file, Path('retrieval.jsonl'))
        self.assertEqual(args.phase_a_report_file, Path('phase_a.json'))
        self.assertFalse(args.allow_runtime_retrieval)
        self.assertFalse(args.allow_answer_generation)
        self.assertFalse(args.allow_judge_calls)

    def test_build_retrieval_bridge_ingest_items_preserves_source_refs_and_domain(self):
        rows = self.sample_rows()
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'

        manifest = longmem_canary.build_retrieval_bridge_ingest_manifest(
            rows,
            selection,
            dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256,
        )

        self.assertEqual(manifest['mode'], 'retrieval_bridge_phase_a_ingest_manifest')
        self.assertEqual(manifest['domain'], 'longmemeval-bridge-v1-20260508-second-slice')
        self.assertEqual(manifest['selected_question_ids'], ['ku_abs', 'multi_1', 'pref_1', 'temp_1'])
        self.assertEqual(manifest['source_session_ids'], ['sess_abs_1', 'sess_multi_1', 'sess_multi_2', 'sess_pref_1', 'sess_temp_1', 'sess_temp_2'])
        self.assertEqual(manifest['planned_memory_count'], 7)
        first = manifest['planned_memories'][0]
        self.assertEqual(first['source_ref'], 'sess_abs_1:turn_1:user')
        self.assertEqual(first['metadata']['question_ids'], ['ku_abs'])
        self.assertEqual(first['metadata']['domain'], longmem_canary.RETRIEVAL_BRIDGE_DOMAIN)
        self.assertEqual(manifest['memory_ids_created'], [])
        self.assertEqual(manifest['ingest_status'], 'planned_no_db_writes')

    def test_run_retrieval_bridge_phase_a_with_injected_fakes_writes_artifacts_and_stops_before_answers(self):
        rows = [
            dict(self.sample_rows()[0], question_id='ku_1', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='ku_2', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='ku_3', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='ku_4', question_type='knowledge-update'),
            dict(self.sample_rows()[1], question_id='ku_5', question_type='knowledge-update'),
            dict(self.sample_rows()[2], question_id='pref_1', question_type='single-session-preference'),
            dict(self.sample_rows()[2], question_id='pref_2', question_type='single-session-preference'),
            dict(self.sample_rows()[2], question_id='pref_3', question_type='single-session-preference'),
            dict(self.sample_rows()[2], question_id='pref_4', question_type='single-session-preference'),
            dict(self.sample_rows()[0], question_id='abs_1_abs', question_type='multi-session'),
            dict(self.sample_rows()[0], question_id='abs_2_abs', question_type='knowledge-update'),
            dict(self.sample_rows()[0], question_id='abs_3_abs', question_type='single-session-user'),
            dict(self.sample_rows()[0], question_id='abs_4_abs', question_type='temporal-reasoning'),
        ]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        calls = []

        coverage_by_qid = {
            'ku_1': 'gold_supported',
            'ku_2': 'gold_supported_with_conflict',
            'ku_3': 'partial_support',
            'ku_4': 'stale_only',
            'ku_5': 'unsupported',
            'pref_1': 'gold_supported',
            'pref_2': 'gold_supported_with_conflict',
            'pref_3': 'gold_supported',
            'pref_4': 'partial_support',
            'abs_1_abs': 'unanswerable_supported',
            'abs_2_abs': 'unanswerable_contaminated',
            'abs_3_abs': 'unanswerable_supported',
            'abs_4_abs': 'unanswerable_supported',
        }
        substrate_metadata = [{
            'recall_telemetry_present': True,
            'substrate_readiness_present': True,
            'substrate_readiness': {'schema': 'memibrium.substrate_readiness.v1'},
        }]

        def fake_ingest(planned_memories, *, domain):
            calls.append(('ingest', len(planned_memories), domain))
            return [f'mem_{index}' for index, _ in enumerate(planned_memories, start=1)]

        def fake_retrieve(row, *, domain, memory_ids):
            calls.append(('retrieve', row['question_id'], domain, len(memory_ids)))
            coverage_class = coverage_by_qid[row['question_id']]
            if coverage_class == 'unsupported':
                return {
                    'retrieved_memory_ids': [],
                    'source_refs': [],
                    'evidence_snippets': [],
                    'timestamp_source_metadata': substrate_metadata,
                    'coverage_class': coverage_class,
                    'candidate_pool': {
                        'schema': 'memibrium.recall.candidate_pool.v1',
                        'candidate_group_count': 0,
                        'groups': [],
                        'total_merged_candidates': 0,
                        'ranked_returned_count': 0,
                        'top_ranked_ids': [],
                    },
                    'score_components': [],
                    'source_ref_analysis': {},
                    'coverage_rationale': 'artifact unsupported for test fixture',
                }
            return {
                'retrieved_memory_ids': [memory_ids[0]],
                'source_refs': [f"{row['question_id']}:source"],
                'evidence_snippets': [f"evidence for {row['question_id']}"],
                'timestamp_source_metadata': substrate_metadata,
                'coverage_class': coverage_class,
                'candidate_pool': {
                    'schema': 'memibrium.recall.candidate_pool.v1',
                    'candidate_group_count': 1,
                    'total_merged_candidates': len(memory_ids),
                    'ranked_returned_count': len(memory_ids),
                    'top_ranked_ids': memory_ids[:10],
                    'groups': [{'source': 'fake', 'count': len(memory_ids), 'top_ids': memory_ids[:10]}],
                },
                'score_components': [{'id': memory_ids[0], 'final_score': 0.9, 'retrieval_sources': ['fake']}],
                'source_ref_analysis': {'supporting_source_refs': [f"{row['question_id']}:source"]},
                'coverage_rationale': f'artifact support for {row["question_id"]}',
            }

        def fake_cleanup(*, domain, memory_ids):
            calls.append(('cleanup', len(memory_ids), domain))
            return {'deleted_memory_count': len(memory_ids), 'final_domain_count_verified': 0, 'linked_rows_deleted': {}}

        def forbidden_chat(*args, **kwargs):
            raise AssertionError('Phase A must not call answer or judge models')

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = longmem_canary.run_retrieval_bridge_phase_a(
                rows,
                selection,
                out_dir,
                allow_db_writes=True,
                allow_runtime_retrieval=True,
                allow_cleanup_deletes=True,
                ingest_fn=fake_ingest,
                retrieval_fn=fake_retrieve,
                cleanup_fn=fake_cleanup,
                chat_fn=forbidden_chat,
                dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256,
            )
            manifest = json.loads((out_dir / 'ingest_manifest.json').read_text())
            retrieval_rows = [json.loads(line) for line in (out_dir / 'retrieval_results.jsonl').read_text().splitlines()]
            coverage_audit = json.loads((out_dir / 'retrieval_coverage_audit.json').read_text())
            report = json.loads((out_dir / 'longmemeval_retrieval_bridge_phase_a_gate_report.json').read_text())
            cleanup = json.loads((out_dir / 'cleanup_report.json').read_text())
            metadata = json.loads((out_dir / 'run_metadata.json').read_text())

        self.assertEqual(result['mode'], 'retrieval_bridge_phase_a_runtime_scaffold')
        self.assertTrue(result['overall_pass'])
        self.assertEqual(result['phase_b_recommendation'], 'phase_a_passed_answer_generation_still_requires_explicit_approval')
        self.assertEqual(manifest['ingest_status'], 'completed_with_injected_ingest_fn')
        self.assertEqual(len(manifest['memory_ids_created']), manifest['planned_memory_count'])
        self.assertEqual(len(retrieval_rows), len(rows))
        self.assertTrue(all(row['retrieval_status'] == 'ok' for row in retrieval_rows))
        self.assertEqual(coverage_audit['coverage_status'], 'evaluated_artifact_only')
        self.assertEqual(coverage_audit['rows'][0]['coverage_class'], 'gold_supported')
        self.assertEqual(retrieval_rows[0]['candidate_pool']['total_merged_candidates'], manifest['planned_memory_count'])
        self.assertEqual(retrieval_rows[0]['score_components'][0]['id'], 'mem_1')
        self.assertEqual(coverage_audit['rows'][0]['source_ref_analysis']['supporting_source_refs'], ['ku_1:source'])
        self.assertIn('artifact support for ku_1', coverage_audit['rows'][0]['classification_notes'])
        self.assertTrue(report['gates']['overall']['pass'])
        self.assertEqual(cleanup['cleanup_status'], 'complete')
        self.assertEqual(cleanup['final_domain_count_verified'], 0)
        self.assertEqual(metadata['guardrails'], [
            'no answer model calls',
            'no judge calls',
            'no full LongMemEval _s/_m run',
            'no direct /mcp/tools inspection',
        ])
        self.assertIn(('ingest', manifest['planned_memory_count'], longmem_canary.RETRIEVAL_BRIDGE_DOMAIN), calls)
        self.assertEqual(sum(1 for call in calls if call[0] == 'retrieve'), len(rows))
        self.assertIn(('cleanup', manifest['planned_memory_count'], longmem_canary.RETRIEVAL_BRIDGE_DOMAIN), calls)

    def test_run_retrieval_bridge_phase_a_requires_explicit_side_effect_scope_before_writing(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'retrieval_bridge_phase_a_requires_explicit_side_effect_approval'):
                longmem_canary.run_retrieval_bridge_phase_a(rows, selection, out_dir)
            self.assertEqual(list(out_dir.iterdir()), [])

    def test_memibrium_http_ingest_adapter_requests_benchmark_fast_path_when_enabled(self):
        planned = [{
            'source_ref': 'sess_1:turn_1:user',
            'content': 'Preference text.',
            'metadata': {'question_ids': ['pref_1']},
        }]
        seen_payloads = []

        def fake_post(path, payload, *, base_url, timeout=30):
            seen_payloads.append(payload)
            return {'id': 'mem_fast'}

        adapter = longmem_canary.make_memibrium_ingest_fn(
            base_url='http://localhost:9999',
            post_fn=fake_post,
            benchmark_fast_path=True,
        )
        self.assertEqual(adapter(planned, domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN), ['mem_fast'])
        self.assertEqual(seen_payloads[0]['benchmark_fast_path'], True)

    def test_memibrium_http_ingest_adapter_posts_retain_with_namespaced_refs_and_redacted_endpoint_metadata(self):
        planned = [{
            'source_ref': 'sess_1:turn_1:user',
            'content': 'I prefer trail runs near water.',
            'metadata': {
                'domain': longmem_canary.RETRIEVAL_BRIDGE_DOMAIN,
                'session_id': 'sess_1',
                'session_date': '2023/05/20 (Sat) 10:00',
                'turn_index': 1,
                'role': 'user',
                'has_answer': True,
                'question_ids': ['pref_1'],
            },
        }]
        calls = []

        def fake_post(path, payload, *, base_url, timeout=30):
            calls.append((path, payload, base_url, timeout))
            self.assertEqual(path, '/mcp/retain')
            self.assertEqual(base_url, 'http://localhost:9999')
            self.assertEqual(payload['domain'], longmem_canary.RETRIEVAL_BRIDGE_DOMAIN)
            self.assertEqual(payload['source'], 'longmemeval_bridge_phase_a')
            self.assertEqual(payload['event_at'], '2023-05-20T10:00:00+00:00')
            self.assertEqual(payload['refs']['longmemeval_bridge']['source_ref'], 'sess_1:turn_1:user')
            self.assertEqual(payload['refs']['longmemeval_bridge']['question_ids'], ['pref_1'])
            return {'id': 'mem_abc123', 'state': 'observation'}

        adapter = longmem_canary.make_memibrium_ingest_fn(
            base_url='http://localhost:9999',
            post_fn=fake_post,
        )
        created_ids = adapter(planned, domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN)

        self.assertEqual(created_ids, ['mem_abc123'])
        self.assertEqual(len(calls), 1)
        metadata = longmem_canary.redacted_memibrium_runtime_metadata('http://user:credential@localhost:9999/path?query=value')
        self.assertEqual(metadata['memibrium_base_url']['host'], 'localhost:9999')
        self.assertEqual(metadata['memibrium_base_url']['path'], '/path')
        self.assertNotIn('credential', json.dumps(metadata))
        self.assertNotIn('query=value', json.dumps(metadata))

    def test_memibrium_http_ingest_adapter_can_capture_per_retain_diagnostics_without_content_or_refs(self):
        planned = [{
            'source_ref': 'sess_1:turn_1:user',
            'content': 'Secret preference text.',
            'metadata': {'session_date': '2023/05/20 (Sat) 10:00'},
        }]

        def fake_post(path, payload, *, base_url, timeout=30):
            self.assertTrue(payload['include_diagnostics'])
            return {
                'id': 'mem_diag',
                'diagnostics': {
                    'schema': 'memibrium.retain.diagnostics.v1',
                    'domain': payload['domain'],
                    'source': payload['source'],
                    'content_length': len(payload['content']),
                    'content_sha256_prefix': 'abc123abc123',
                    'timings_ms': {'total_ms': 12.5, 'ingest_total_ms': 10.0},
                    'refs': {'should_not': 'be recorded'},
                    'content': payload['content'],
                },
            }

        adapter = longmem_canary.make_memibrium_ingest_fn(
            base_url='http://localhost:9999',
            post_fn=fake_post,
            include_diagnostics=True,
        )
        created_ids = adapter(planned, domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN)

        self.assertEqual(created_ids, ['mem_diag'])
        diagnostics = adapter.retain_diagnostics
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]['memory_id'], 'mem_diag')
        self.assertEqual(diagnostics[0]['source_ref'], 'sess_1:turn_1:user')
        self.assertEqual(diagnostics[0]['timings_ms']['ingest_total_ms'], 10.0)
        diagnostics_json = json.dumps(diagnostics)
        self.assertNotIn('Secret preference text', diagnostics_json)
        self.assertNotIn('should_not', diagnostics_json)
        self.assertNotIn('refs', diagnostics_json)

    def test_memibrium_http_ingest_adapter_records_failure_index_and_created_count(self):
        planned = [
            {'source_ref': 'sess_1:turn_1:user', 'content': 'First memory.', 'metadata': {}},
            {'source_ref': 'sess_1:turn_2:user', 'content': 'Second memory.', 'metadata': {}},
        ]
        calls = []

        def fake_post(path, payload, *, base_url, timeout=30):
            calls.append(payload)
            if len(calls) == 1:
                return {'id': 'mem_created', 'diagnostics': {'timings_ms': {'total_ms': 1.0}}}
            raise RuntimeError('retain timed out')

        adapter = longmem_canary.make_memibrium_ingest_fn(
            base_url='http://localhost:9999',
            post_fn=fake_post,
            include_diagnostics=True,
        )

        with self.assertRaises(longmem_canary.MemibriumIngestError) as cm:
            adapter(planned, domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN)

        self.assertEqual(cm.exception.created_ids, ['mem_created'])
        self.assertEqual(cm.exception.failure_index, 1)
        self.assertEqual(cm.exception.created_count, 1)
        self.assertEqual(len(cm.exception.retain_diagnostics), 1)

    def test_memibrium_http_ingest_adapter_raises_partial_failure_with_created_ids(self):
        planned = [
            {
                'source_ref': 'sess_1:turn_1:user',
                'content': 'First memory.',
                'metadata': {'session_date': '2023/05/20 (Sat) 10:00'},
            },
            {
                'source_ref': 'sess_1:turn_2:user',
                'content': 'Second memory.',
                'metadata': {'session_date': 'not a parseable LongMemEval date'},
            },
        ]
        calls = []

        def fake_post(path, payload, *, base_url, timeout=30):
            calls.append((path, payload, base_url, timeout))
            if len(calls) == 1:
                return {'memory_id': 'mem_created'}
            raise RuntimeError('retain failed')

        adapter = longmem_canary.make_memibrium_ingest_fn(
            base_url='http://localhost:9999',
            post_fn=fake_post,
        )

        with self.assertRaises(longmem_canary.MemibriumIngestError) as cm:
            adapter(planned, domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN)

        self.assertEqual(cm.exception.created_ids, ['mem_created'])
        self.assertIsInstance(cm.exception.__cause__, RuntimeError)
        self.assertIsNone(calls[1][1]['event_at'])

    def test_parse_longmemeval_session_date_returns_none_for_unparseable_values(self):
        self.assertEqual(
            longmem_canary._parse_longmemeval_session_date('2023/05/20 (Sat) 10:00'),
            '2023-05-20T10:00:00+00:00',
        )
        self.assertIsNone(longmem_canary._parse_longmemeval_session_date('not a parseable LongMemEval date'))

    def test_memibrium_http_post_rejects_non_http_base_url_before_urlopen(self):
        called = []

        def forbidden_urlopen(*args, **kwargs):
            called.append((args, kwargs))
            raise AssertionError('urlopen must not be called for non-http schemes')

        original_urlopen = longmem_canary.urllib.request.urlopen
        try:
            longmem_canary.urllib.request.urlopen = forbidden_urlopen
            with self.assertRaisesRegex(ValueError, 'memibrium_http_invalid_base_url_scheme'):
                longmem_canary.memibrium_http_post('/mcp/retain', {}, base_url='file:///tmp/memibrium')
        finally:
            longmem_canary.urllib.request.urlopen = original_urlopen

        self.assertEqual(called, [])

    def test_memibrium_http_post_wraps_non_json_success_response(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'<html>not json</html>'

        def fake_urlopen(request, timeout=30):
            return FakeResponse()

        original_urlopen = longmem_canary.urllib.request.urlopen
        try:
            longmem_canary.urllib.request.urlopen = fake_urlopen
            with self.assertRaisesRegex(RuntimeError, 'memibrium_http_invalid_json'):
                longmem_canary.memibrium_http_post('/mcp/retain', {}, base_url='http://localhost:9999')
        finally:
            longmem_canary.urllib.request.urlopen = original_urlopen

    def test_run_retrieval_bridge_phase_a_cleans_up_partial_ingest_failures(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        cleanup_calls = []

        def failing_ingest(planned_memories, *, domain):
            raise longmem_canary.MemibriumIngestError('partial ingest', ['mem_created'], RuntimeError('retain failed'))

        def forbidden_retrieve(*args, **kwargs):
            raise AssertionError('retrieval must not run after ingest failure')

        def fake_cleanup(*, domain, memory_ids):
            cleanup_calls.append((domain, list(memory_ids)))
            return {'deleted_memory_count': len(memory_ids), 'final_domain_count_verified': 0, 'linked_rows_deleted': {}}

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(longmem_canary.MemibriumIngestError):
                longmem_canary.run_retrieval_bridge_phase_a(
                    rows,
                    selection,
                    Path(tmp),
                    allow_db_writes=True,
                    allow_runtime_retrieval=True,
                    allow_cleanup_deletes=True,
                    ingest_fn=failing_ingest,
                    retrieval_fn=forbidden_retrieve,
                    cleanup_fn=fake_cleanup,
                    dataset_sha256=longmem_canary.EXPECTED_ORACLE_SHA256,
                )

        self.assertEqual(cleanup_calls, [(longmem_canary.RETRIEVAL_BRIDGE_DOMAIN, ['mem_created'])])

    def test_memibrium_http_retrieval_adapter_calls_context_packet_with_source_attribution_and_normalizes_results(self):
        calls = []

        def fake_post(path, payload, *, base_url, timeout=30):
            calls.append((path, payload, base_url, timeout))
            self.assertEqual(path, '/mcp/context_packet')
            self.assertEqual(payload['domain'], longmem_canary.RETRIEVAL_BRIDGE_DOMAIN)
            self.assertIn('Preference retrieval', payload['query'])
            self.assertIn('Can you recommend weekend events?', payload['query'])
            self.assertTrue(payload['include_source_attribution'])
            self.assertTrue(payload['include_recall_telemetry'])
            self.assertFalse(payload['include_decision_traces'])
            self.assertEqual(payload['top_k'], 8)
            return {
                'episodic_evidence': [
                    {
                        'memory_id': 'mem_1',
                        'content': 'The user prefers Spanish and French practice events.',
                        'combined_score': 0.91,
                        'refs': {'longmemeval_bridge': {'source_ref': 'sess_pref_1:turn_1:user'}},
                    }
                ],
                'source_attribution': {
                    'retrieval_path': 'query_agent.recall',
                    'evidence': [
                        {'id': 'mem_1', 'refs': {'longmemeval_bridge': {'source_ref': 'sess_pref_1:turn_1:user'}}},
                    ],
                },
                'recall_telemetry': {
                    'streams': {
                        'semantic': {'returned_count': 1, 'items': [{'id': 'mem_1', 'cosine_score': 0.91}]},
                        'lexical': {'returned_count': 0, 'items': []},
                    },
                    'fusion': {'fused_count_before_cap': 1, 'items_before_cap': [{'id': 'mem_1'}]},
                    'final': {'returned_count': 1, 'items': [{'id': 'mem_1'}]},
                    'ranking': {
                        'top_ranked_ids': ['mem_1'],
                        'score_components': [{
                            'id': 'mem_1',
                            'retrieval_score': 0.91,
                            'ct_score': 0.72,
                            'final_score': 0.8245,
                            'retrieval_sources': ['semantic'],
                        }],
                    },
                    'server': {
                        'timings_ms': {'total_ms': 12.5},
                        'hybrid_succeeded': True,
                        'extra_vector_candidates_executed': False,
                        'candidate_pool': {
                            'candidate_group_count': 1,
                            'total_candidates_before_merge': 1,
                            'total_merged_candidates': 1,
                            'groups': [{'source': 'hybrid', 'count': 1}],
                        },
                    }
                },
            }

        adapter = longmem_canary.make_memibrium_retrieval_fn(
            base_url='http://localhost:9999',
            post_fn=fake_post,
            top_k=8,
        )
        retrieved = adapter(self.sample_rows()[2], domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN, memory_ids=['mem_1'])

        self.assertEqual(retrieved['retrieval_status'], 'ok')
        self.assertEqual(retrieved['query_variants'][0], 'Can you recommend weekend events?')
        self.assertIn('Preference retrieval', retrieved['query_variants'][1])
        self.assertEqual(retrieved['retrieved_memory_ids'], ['mem_1'])
        self.assertEqual(retrieved['scores'], [0.91])
        self.assertEqual(retrieved['source_refs'], ['sess_pref_1:turn_1:user'])
        self.assertEqual(retrieved['evidence_snippets'], ['The user prefers Spanish and French practice events.'])
        metadata = retrieved['timestamp_source_metadata'][0]
        self.assertEqual(metadata['retrieval_path'], 'query_agent.recall')
        self.assertTrue(metadata['recall_telemetry_present'])
        self.assertEqual(metadata['recall_timings_ms']['total_ms'], 12.5)
        self.assertTrue(metadata['hybrid_succeeded'])
        self.assertFalse(metadata['extra_vector_candidates_executed'])
        self.assertFalse(metadata['substrate_readiness_present'])
        self.assertIsNone(metadata['substrate_readiness'])
        self.assertEqual(retrieved['coverage_class'], 'gold_supported')
        self.assertEqual(retrieved['candidate_pool']['schema'], 'memibrium.recall.candidate_pool.v1')
        self.assertEqual(retrieved['candidate_pool']['total_merged_candidates'], 1)
        self.assertEqual(retrieved['candidate_pool']['ranked_returned_count'], 1)
        self.assertEqual(retrieved['score_components'][0]['id'], 'mem_1')
        self.assertEqual(retrieved['source_ref_analysis']['supporting_source_refs'], ['sess_pref_1:turn_1:user'])
        self.assertIn('preference_session_support', retrieved['coverage_rationale'])
        self.assertEqual(calls[0][2], 'http://localhost:9999')

    def test_phase_a_coverage_heuristic_treats_preference_session_support_as_gold(self):
        row = self.sample_rows()[2]
        evidence = [{
            'memory_id': 'mem_pref',
            'content': 'I like cultural events where I can practice Spanish and French.',
            'refs': {'longmemeval_bridge': {'source_ref': 'sess_pref_1:turn_1:user'}},
        }]

        self.assertEqual(
            longmem_canary._heuristic_coverage_class(row, evidence, ['sess_pref_1:turn_1:user']),
            'gold_supported',
        )

    def test_phase_a_coverage_heuristic_abstention_is_not_contaminated_by_irrelevant_sources(self):
        row = self.sample_rows()[0]
        evidence = [{
            'memory_id': 'mem_abs',
            'content': 'I collected a signed baseball, but there was no football detail.',
            'refs': {'longmemeval_bridge': {'source_ref': 'sess_abs_1:turn_1:user'}},
        }]

        self.assertEqual(
            longmem_canary._heuristic_coverage_class(row, evidence, ['sess_abs_1:turn_1:user']),
            'unanswerable_supported',
        )

    def test_phase_a_coverage_heuristic_abstention_near_miss_context_is_supported(self):
        row = {
            'question_id': 'manager_abs',
            'question_type': 'knowledge-update',
            'question': 'How many engineers do I lead when I just started my new role as Software Engineer Manager?',
            'answer': 'The information provided is not enough. You mentioned starting the role as Senior Software Engineer but not Software Engineer Manager.',
            'answer_session_ids': ['sess_manager'],
        }
        evidence = [{
            'memory_id': 'mem_manager',
            'content': 'I now lead a team of five engineers in my role as Senior Software Engineer.',
            'refs': {'longmemeval_bridge': {'source_ref': 'sess_manager:turn_1:user'}},
        }]

        self.assertEqual(
            longmem_canary._heuristic_coverage_class(row, evidence, ['sess_manager:turn_1:user']),
            'unanswerable_supported',
        )

    def test_phase_a_coverage_heuristic_abstention_direct_missing_target_leak_is_contaminated(self):
        row = {
            'question_id': 'manager_abs',
            'question_type': 'knowledge-update',
            'question': 'How many engineers do I lead when I just started my new role as Software Engineer Manager?',
            'answer': 'The information provided is not enough. You mentioned starting the role as Senior Software Engineer but not Software Engineer Manager.',
            'answer_session_ids': ['sess_manager'],
        }
        evidence = [{
            'memory_id': 'mem_manager',
            'content': 'I just started as Software Engineer Manager and lead seven engineers.',
            'refs': {'longmemeval_bridge': {'source_ref': 'sess_manager:turn_2:user'}},
        }]

        self.assertEqual(
            longmem_canary._heuristic_coverage_class(row, evidence, ['sess_manager:turn_2:user']),
            'unanswerable_contaminated',
        )

    def test_phase_a_coverage_heuristic_abstention_mixed_negative_and_target_leak_is_contaminated(self):
        row = {
            'question_id': 'manager_abs',
            'question_type': 'knowledge-update',
            'question': 'How many engineers do I lead when I just started my new role as Software Engineer Manager?',
            'answer': 'The information provided is not enough. You mentioned starting the role as Senior Software Engineer but not Software Engineer Manager.',
            'answer_session_ids': ['sess_manager'],
        }
        evidence = [{
            'memory_id': 'mem_manager',
            'content': 'There was no hiring-plan detail, but I just started as Software Engineer Manager and lead seven engineers.',
            'refs': {'longmemeval_bridge': {'source_ref': 'sess_manager:turn_2:user'}},
        }]

        self.assertEqual(
            longmem_canary._heuristic_coverage_class(row, evidence, ['sess_manager:turn_2:user']),
            'unanswerable_contaminated',
        )

    def test_memibrium_http_cleanup_adapter_deletes_only_namespaced_domain_and_verifies_zero_count(self):
        class FakeConn:
            def __init__(self, fail_on_memory_delete=False):
                self.fail_on_memory_delete = fail_on_memory_delete
                self.fetchvals = []
                self.fetchrows = []
                self.executes = []
                self.pending_executes = []
                self.committed_executes = []
                self.in_transaction = False

            def transaction(self):
                conn = self

                class FakeTransaction:
                    async def __aenter__(self):
                        conn.in_transaction = True
                        conn.pending_executes = []
                        return self

                    async def __aexit__(self, exc_type, exc, tb):
                        conn.in_transaction = False
                        if exc_type is None:
                            conn.committed_executes.extend(conn.pending_executes)
                        conn.pending_executes = []
                        return False

                return FakeTransaction()

            async def fetchval(self, sql, *params):
                self.fetchvals.append((sql, params, self.in_transaction))
                if 'SELECT COUNT(id) FROM memories' in sql:
                    return 0
                return None

            async def fetchrow(self, sql, *params):
                self.fetchrows.append((sql, params, self.in_transaction))
                return {'memory_count': 2, 'feedback_count': 1, 'snapshot_count': 1, 'edge_count': 1, 'contradiction_count': 1, 'temporal_expression_count': 1, 'context_graph_edge_count': 1, 'decision_trace_count': 1, 'self_model_observation_count': 1}

            async def execute(self, sql, *params):
                record = (sql, params, self.in_transaction)
                self.executes.append(record)
                if self.in_transaction:
                    self.pending_executes.append(record)
                else:
                    self.committed_executes.append(record)
                if self.fail_on_memory_delete and sql == 'DELETE FROM memories WHERE domain = $1 AND id = ANY($2::text[])':
                    raise RuntimeError('memory delete failed')
                if 'DELETE FROM memories' in sql:
                    return 'DELETE 2'
                return 'DELETE 1'

            async def close(self):
                self.closed = True

        fake_conn = FakeConn()

        async def fake_connect(dsn):
            self.assertEqual(dsn, 'postgresql://localhost:5432/memory')
            return fake_conn

        adapter = longmem_canary.make_memibrium_cleanup_fn(
            db_dsn='postgresql://localhost:5432/memory',
            connect_fn=fake_connect,
        )
        result = adapter(domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN, memory_ids=['mem_1', 'mem_2'])

        self.assertEqual(result['deleted_memory_count'], 2)
        self.assertEqual(result['final_domain_count_verified'], 0)
        executed_sql = '\n'.join(sql for sql, _params, _in_transaction in fake_conn.executes)
        self.assertIn('memory_a_id', executed_sql)
        self.assertIn('memory_b_id', executed_sql)
        self.assertIn('DELETE FROM context_graph_edges', executed_sql)
        self.assertIn('DELETE FROM decision_traces', executed_sql)
        self.assertIn('DELETE FROM self_model_observations', executed_sql)
        self.assertIn('ARRAY(SELECT id FROM memories WHERE domain = $1 AND id = ANY($2::text[]))', executed_sql)
        self.assertIn('domain = $1', executed_sql)
        self.assertIn('DELETE FROM memories', executed_sql)
        self.assertNotIn('LIKE', executed_sql)
        self.assertTrue(all(in_transaction for _sql, _params, in_transaction in fake_conn.executes))
        self.assertTrue(all(params[0] == longmem_canary.RETRIEVAL_BRIDGE_DOMAIN for _sql, params, _in_transaction in fake_conn.executes if params))
        self.assertTrue(all(params[1] == ['mem_1', 'mem_2'] for _sql, params, _in_transaction in fake_conn.executes if len(params) > 1))
        self.assertEqual(fake_conn.committed_executes, fake_conn.executes)

        failing_conn = FakeConn(fail_on_memory_delete=True)

        async def fake_connect_failing(dsn):
            return failing_conn

        failing_adapter = longmem_canary.make_memibrium_cleanup_fn(
            db_dsn='postgresql://localhost:5432/memory',
            connect_fn=fake_connect_failing,
        )
        with self.assertRaisesRegex(RuntimeError, 'memory delete failed'):
            failing_adapter(domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN, memory_ids=['mem_1', 'mem_2'])
        self.assertEqual(failing_conn.committed_executes, [])

    def test_memibrium_cleanup_adapter_preserves_connect_failure_and_does_not_require_memory_ids(self):
        async def fake_connect(_dsn):
            raise RuntimeError('connect failed')

        adapter = longmem_canary.make_memibrium_cleanup_fn(
            db_dsn='postgresql://localhost:5432/memory',
            connect_fn=fake_connect,
        )
        with self.assertRaisesRegex(RuntimeError, 'connect failed'):
            adapter(domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN, memory_ids=[])

    def test_memibrium_cleanup_adapter_rejects_running_event_loop_with_clear_error(self):
        async def fake_connect(_dsn):
            raise AssertionError('connect should not be reached from a running loop')

        adapter = longmem_canary.make_memibrium_cleanup_fn(
            db_dsn='postgresql://localhost:5432/memory',
            connect_fn=fake_connect,
        )

        async def invoke_adapter():
            adapter(domain=longmem_canary.RETRIEVAL_BRIDGE_DOMAIN, memory_ids=[])

        with self.assertRaisesRegex(RuntimeError, 'memibrium_cleanup_requires_async_cleanup_in_running_loop'):
            longmem_canary.asyncio.run(invoke_adapter())

    def test_run_retrieval_bridge_phase_a_writes_progress_checkpoint_before_ingest_and_after_cleanup(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        cleanup_calls = []

        def failing_ingest(planned_memories, *, domain):
            self.assertGreater(len(planned_memories), 0)
            raise longmem_canary.MemibriumIngestError('memibrium_ingest_partial_failure', ['mem_partial'], RuntimeError('retain timed out'))

        def retrieval_fn(*_args, **_kwargs):
            raise AssertionError('retrieval should not run after ingest failure')

        def cleanup_fn(*, domain, memory_ids):
            cleanup_calls.append((domain, list(memory_ids)))
            final_count = 1 if memory_ids else 0
            return {'deleted_memory_count': len(memory_ids) or 1, 'final_domain_count_verified': final_count, 'linked_rows_deleted': {'memory_edges': 0}}

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / 'phase-a-out'
            with self.assertRaises(longmem_canary.MemibriumIngestError):
                longmem_canary.run_retrieval_bridge_phase_a(
                    rows,
                    selection,
                    out_dir,
                    allow_db_writes=True,
                    allow_runtime_retrieval=True,
                    allow_cleanup_deletes=True,
                    ingest_fn=failing_ingest,
                    retrieval_fn=retrieval_fn,
                    cleanup_fn=cleanup_fn,
                    runtime_metadata={'memibrium_base_url': {'host': 'localhost'}},
                )
            progress = json.loads((out_dir / 'progress_checkpoint.json').read_text())
            cleanup_report = json.loads((out_dir / 'cleanup_report.json').read_text())

        self.assertEqual(progress['stage'], 'cleanup_complete_after_failure')
        self.assertEqual(progress['planned_memory_count'], 4)
        self.assertEqual(progress['created_memory_count'], 1)
        self.assertEqual(progress['retrieval_completed_count'], 0)
        self.assertEqual(progress['last_error_class'], 'MemibriumIngestError')
        self.assertNotIn('postgresql://', json.dumps(progress))
        self.assertEqual(cleanup_report['cleanup_status'], 'complete')
        self.assertEqual(cleanup_calls, [
            (longmem_canary.RETRIEVAL_BRIDGE_DOMAIN, ['mem_partial']),
            (longmem_canary.RETRIEVAL_BRIDGE_DOMAIN, []),
        ])

    def test_run_retrieval_bridge_phase_a_smoke_max_questions_limits_rows_and_manifest(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        ingest_counts = []
        retrieved_qids = []

        def ingest_fn(planned_memories, *, domain):
            ingest_counts.append(len(planned_memories))
            return [f'mem_{idx}' for idx, _memory in enumerate(planned_memories, start=1)]

        def retrieval_fn(row, *, domain, memory_ids):
            retrieved_qids.append(row['question_id'])
            return {
                'retrieval_status': 'ok',
                'coverage_class': 'partial_support',
                'retrieved_memory_ids': memory_ids[:1],
                'source_refs': ['smoke:turn_1:user'],
            }

        def cleanup_fn(*, domain, memory_ids):
            return {'deleted_memory_count': len(memory_ids), 'final_domain_count_verified': 0, 'linked_rows_deleted': {}}

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / 'phase-a-out'
            result = longmem_canary.run_retrieval_bridge_phase_a(
                rows,
                selection,
                out_dir,
                allow_db_writes=True,
                allow_runtime_retrieval=True,
                allow_cleanup_deletes=True,
                ingest_fn=ingest_fn,
                retrieval_fn=retrieval_fn,
                cleanup_fn=cleanup_fn,
                smoke_max_questions=1,
            )
            manifest = json.loads((out_dir / 'ingest_manifest.json').read_text())
            retrieval_lines = (out_dir / 'retrieval_results.jsonl').read_text().strip().splitlines()

        self.assertEqual(result['row_count'], 1)
        self.assertEqual(manifest['selected_question_ids'], [rows[0]['question_id']])
        self.assertEqual(manifest['planned_memory_count'], 2)
        self.assertEqual(ingest_counts, [2])
        self.assertEqual(retrieved_qids, [rows[0]['question_id']])
        self.assertEqual(len(retrieval_lines), 1)

    def test_main_wires_live_phase_a_adapters_only_when_runtime_scaffold_is_requested(self):
        rows = self.sample_rows()[:2]
        selection = self.make_selection(rows, seed=longmem_canary.SECOND_SLICE_SELECTION_SEED, prior_question_ids=[])
        selection['slice_id'] = 'longmemeval_oracle_canary_25_second_slice_20260508'
        calls = []
        factory_calls = []

        def fake_runner(dataset, selection_payload, out_dir, **kwargs):
            calls.append((dataset, selection_payload, out_dir, kwargs))
            self.assertIsNotNone(kwargs['ingest_fn'])
            self.assertIsNotNone(kwargs['retrieval_fn'])
            self.assertIsNotNone(kwargs['cleanup_fn'])
            self.assertIsNone(kwargs.get('chat_fn'))
            self.assertEqual(kwargs.get('smoke_max_questions'), 1)
            return {
                'mode': 'retrieval_bridge_phase_a_runtime_live_memibrium',
                'domain': longmem_canary.RETRIEVAL_BRIDGE_DOMAIN,
                'row_count': len(dataset),
                'overall_pass': False,
                'phase_b_recommendation': 'stop_before_answer_generation_phase_a_failed',
                'phase_a_report_file': str(out_dir / 'longmemeval_retrieval_bridge_phase_a_gate_report.json'),
            }

        def fake_ingest_factory(*, base_url, timeout, include_diagnostics=False, benchmark_fast_path=False):
            factory_calls.append(('ingest', base_url, timeout, include_diagnostics, benchmark_fast_path))
            return lambda planned_memories, *, domain: ['mem_1']

        def fake_retrieval_factory(*, base_url, timeout):
            factory_calls.append(('retrieval', base_url, timeout))
            return lambda row, *, domain, memory_ids: {'retrieval_status': 'ok'}

        def fake_cleanup_factory(*, db_dsn):
            factory_calls.append(('cleanup', db_dsn))
            return lambda *, domain, memory_ids: {'final_domain_count_verified': 0}

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path = tmp_path / 'dataset.json'
            selection_path = tmp_path / 'selection.json'
            out_dir = tmp_path / 'phase-a-out'
            dataset_path.write_text(json.dumps(rows))
            selection['source_sha256'] = longmem_canary.sha256_file(dataset_path)
            selection_path.write_text(json.dumps(selection))
            argv = [
                '--run-retrieval-bridge-phase-a',
                '--allow-db-writes',
                '--allow-runtime-retrieval',
                '--allow-cleanup-deletes',
                '--dataset', str(dataset_path),
                '--selection', str(selection_path),
                '--out-dir', str(out_dir),
                '--memibrium-base-url', 'http://localhost:9999',
                '--memibrium-db-dsn', 'postgresql://localhost:5432/memory',
                '--memibrium-http-timeout', '180',
                '--memibrium-retain-diagnostics',
                '--memibrium-benchmark-fast-path',
                '--retrieval-bridge-smoke-max-questions', '1',
            ]
            stdout = io.StringIO()
            original_parse_args = longmem_canary.parse_args
            original_runner = longmem_canary.run_retrieval_bridge_phase_a
            original_ingest_factory = longmem_canary.make_memibrium_ingest_fn
            original_retrieval_factory = longmem_canary.make_memibrium_retrieval_fn
            original_cleanup_factory = longmem_canary.make_memibrium_cleanup_fn
            try:
                longmem_canary.parse_args = lambda: original_parse_args(argv)
                longmem_canary.run_retrieval_bridge_phase_a = fake_runner
                longmem_canary.make_memibrium_ingest_fn = fake_ingest_factory
                longmem_canary.make_memibrium_retrieval_fn = fake_retrieval_factory
                longmem_canary.make_memibrium_cleanup_fn = fake_cleanup_factory
                with contextlib.redirect_stdout(stdout):
                    longmem_canary.main()
            finally:
                longmem_canary.parse_args = original_parse_args
                longmem_canary.run_retrieval_bridge_phase_a = original_runner
                longmem_canary.make_memibrium_ingest_fn = original_ingest_factory
                longmem_canary.make_memibrium_retrieval_fn = original_retrieval_factory
                longmem_canary.make_memibrium_cleanup_fn = original_cleanup_factory

        self.assertEqual(len(calls), 1)
        printed = json.loads(stdout.getvalue())
        self.assertEqual(printed['mode'], 'retrieval_bridge_phase_a_runtime_live_memibrium')
        self.assertFalse(printed['overall_pass'])
        self.assertNotIn('postgresql://', stdout.getvalue())
        self.assertNotIn('memory:memory', stdout.getvalue())
        self.assertIn(('ingest', 'http://localhost:9999', 180, True, True), factory_calls)
        self.assertIn(('retrieval', 'http://localhost:9999', 180), factory_calls)
        self.assertIn(('cleanup', 'postgresql://localhost:5432/memory'), factory_calls)

    def test_parse_args_defaults_phase_a_to_second_slice_and_allows_container_dsn_source(self):
        with mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != 'MEMIBRIUM_DB_DSN'}, clear=True):
            args = longmem_canary.parse_args([
                '--run-retrieval-bridge-phase-a',
                '--allow-db-writes',
                '--allow-runtime-retrieval',
                '--allow-cleanup-deletes',
            ])

        self.assertEqual(args.selection, longmem_canary.DEFAULT_SECOND_SLICE_SELECTION_PATH)
        self.assertEqual(args.memibrium_db_dsn, '')
        self.assertEqual(args.memibrium_db_dsn_source, 'env-or-container')
        self.assertEqual(args.memibrium_server_container, 'memibrium-server')
        self.assertFalse(args.memibrium_retain_diagnostics)
        self.assertFalse(args.memibrium_benchmark_fast_path)

    def test_resolve_memibrium_cleanup_dsn_can_derive_from_container_env_without_printing_secret(self):
        docker_payload = json.dumps([{
            'Config': {
                'Env': [
                    'DB_HOST=memibrium-ruvector-db',
                    'DB_PORT=5432',
                    'DB_NAME=memory',
                    'DB_USER=memory',
                    'DB_PASSWORD=[REDACTED]',
                ]
            }
        }])
        calls = []

        def fake_run(cmd, *, check, capture_output, text):
            calls.append(cmd)
            self.assertEqual(cmd, ['docker', 'inspect', 'memibrium-server'])

            class Result:
                stdout = docker_payload

            return Result()

        dsn = longmem_canary.resolve_memibrium_cleanup_dsn(
            explicit_dsn='',
            source='container',
            container_name='memibrium-server',
            subprocess_run=fake_run,
        )

        self.assertEqual(calls, [['docker', 'inspect', 'memibrium-server']])
        expected_dsn = 'postgresql://memory:%5BREDACTED%5D@localhost:5432/memory'
        self.assertEqual(dsn, expected_dsn)
        self.assertNotIn('[REDACTED]', repr(calls))

    def test_redacted_memibrium_runtime_metadata_empty_and_none_urls(self):
        for url in ('', None):
            result = longmem_canary.redacted_memibrium_runtime_metadata(url)
            self.assertFalse(result['memibrium_base_url']['configured'])
            self.assertEqual(result['memibrium_base_url']['scheme'], '')
            self.assertEqual(result['memibrium_base_url']['host'], '')
            self.assertEqual(result['memibrium_base_url']['path'], '')

    def test_parse_args_supports_retrieval_bridge_phase_a_runtime_scaffold_but_keeps_models_off(self):
        args = longmem_canary.parse_args([
            '--run-retrieval-bridge-phase-a',
            '--allow-db-writes',
            '--allow-runtime-retrieval',
            '--allow-cleanup-deletes',
            '--out-dir', 'phase-a-out',
            '--memibrium-base-url', 'http://localhost:9999',
            '--memibrium-db-dsn', 'postgresql://localhost:5432/memory',
            '--memibrium-http-timeout', '180',
            '--retrieval-bridge-smoke-max-questions', '1',
        ])

        self.assertTrue(args.run_retrieval_bridge_phase_a)
        self.assertTrue(args.allow_db_writes)
        self.assertTrue(args.allow_runtime_retrieval)
        self.assertTrue(args.allow_cleanup_deletes)
        self.assertFalse(args.allow_answer_generation)
        self.assertFalse(args.allow_judge_calls)
        self.assertEqual(args.out_dir, Path('phase-a-out'))
        self.assertEqual(args.memibrium_base_url, 'http://localhost:9999')
        self.assertEqual(args.memibrium_db_dsn, 'postgresql://localhost:5432/memory')
        self.assertEqual(args.memibrium_http_timeout, 180)
        self.assertEqual(args.retrieval_bridge_smoke_max_questions, 1)


if __name__ == '__main__':
    unittest.main()
