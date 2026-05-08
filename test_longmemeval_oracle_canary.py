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

    def make_selection(self, rows=None):
        rows = rows or self.sample_rows()
        seed = 'memibrium-longmemeval-oracle-canary-2026-05-08-v1'
        return {
            'source_file': 'longmemeval_oracle.json',
            'hf_revision': longmem_canary.EXPECTED_HF_REVISION,
            'source_sha256': longmem_canary.EXPECTED_ORACLE_SHA256,
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


if __name__ == '__main__':
    unittest.main()
