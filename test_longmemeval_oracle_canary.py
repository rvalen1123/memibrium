#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


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
        ]

    def test_validate_selection_requires_unique_rows_and_dataset_hash(self):
        dataset = self.sample_rows()
        selection = {
            'source_file': 'longmemeval_oracle.json',
            'hf_revision': longmem_canary.EXPECTED_HF_REVISION,
            'source_sha256': longmem_canary.EXPECTED_ORACLE_SHA256,
            'counts': {'total': 2, 'abstention': 1, 'by_question_type': {'knowledge-update': 1, 'multi-session': 1}},
            'rows': [
                {'question_id': 'ku_abs', 'question_type': 'knowledge-update', 'abstention': True, 'selection_hash': 'a' * 64, 'selection_index': 1},
                {'question_id': 'multi_1', 'question_type': 'multi-session', 'abstention': False, 'selection_hash': 'b' * 64, 'selection_index': 2},
            ],
        }

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

    def test_prepare_predictions_requires_explicit_launch_flag_and_writes_placeholder_jsonl(self):
        rows = self.sample_rows()
        selection = {
            'source_file': 'longmemeval_oracle.json',
            'hf_revision': longmem_canary.EXPECTED_HF_REVISION,
            'source_sha256': longmem_canary.EXPECTED_ORACLE_SHA256,
            'counts': {'total': 1, 'abstention': 1, 'by_question_type': {'knowledge-update': 1}},
            'rows': [
                {'question_id': 'ku_abs', 'question_type': 'knowledge-update', 'abstention': True, 'selection_hash': 'a' * 64, 'selection_index': 1},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'answer_generation_requires_explicit_launch'):
                longmem_canary.prepare_oracle_canary(rows, selection, out_dir, allow_answer_generation=True)

            result = longmem_canary.prepare_oracle_canary(rows, selection, out_dir, allow_answer_generation=False)
            baseline_lines = (out_dir / 'longmemeval_oracle_canary_baseline_placeholder.jsonl').read_text().splitlines()
            treatment_lines = (out_dir / 'longmemeval_oracle_canary_treatment_placeholder.jsonl').read_text().splitlines()

        self.assertEqual(result['mode'], 'preparation_only_no_answer_generation')
        self.assertEqual(len(baseline_lines), 1)
        self.assertEqual(len(treatment_lines), 1)
        self.assertEqual(json.loads(baseline_lines[0]), {'question_id': 'ku_abs', 'hypothesis': ''})
        self.assertEqual(json.loads(treatment_lines[0]), {'question_id': 'ku_abs', 'hypothesis': ''})


if __name__ == '__main__':
    unittest.main()
