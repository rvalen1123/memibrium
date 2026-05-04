#!/usr/bin/env python3
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT_PATH = ROOT / 'docs' / 'eval' / 'results' / 'run_locomo_context_packet_canary.py'
spec = importlib.util.spec_from_file_location('run_locomo_context_packet_canary', SCRIPT_PATH)
context_packet_canary = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(context_packet_canary)


class ContextPacketCanaryTests(unittest.TestCase):
    def test_fixed_row_identity_requires_exact_conv26_question_hashes(self):
        data = [
            {
                'sample_id': 'conv-26',
                'qa': [
                    {'category': 1, 'question': 'first question', 'answer': 'first'},
                    {'category': 2, 'question': 'second question', 'answer': 'second'},
                ],
            }
        ]
        fixed_rows = [
            {
                'one_based_index': 2,
                'cat': 'temporal',
                'question': 'second question',
                'question_sha256': context_packet_canary.sha256_text('second question'),
                'label': 'tiny_temporal',
            }
        ]

        proof = context_packet_canary.validate_fixed_row_identity(data, fixed_rows)

        self.assertTrue(proof['ok'])
        self.assertEqual(proof['sample_id'], 'conv-26')
        self.assertEqual(proof['rows'][0]['one_based_index'], 2)
        self.assertEqual(proof['rows'][0]['question_sha256'], context_packet_canary.sha256_text('second question'))

        bad_rows = [dict(fixed_rows[0], question_sha256='0' * 64)]
        with self.assertRaisesRegex(ValueError, 'row_identity_mismatch'):
            context_packet_canary.validate_fixed_row_identity(data, bad_rows)

    def test_arm_envs_only_differ_by_context_packet_flag(self):
        base_env = {
            'USE_CONTEXT_RERANK': '1',
            'USE_APPEND_CONTEXT_EXPANSION': '1',
            'USE_GATED_APPEND_CONTEXT_EXPANSION': '1',
            'USE_LEGACY_CONTEXT_ASSEMBLY': '1',
            'USE_FULL_DOMAIN_CONTEXT': '1',
            'LOCOMO_RETRIEVAL_TELEMETRY': '1',
        }

        baseline = context_packet_canary.build_benchmark_env(base_env, mcp_url='http://localhost:9999/mcp', context_packet=False)
        treatment = context_packet_canary.build_benchmark_env(base_env, mcp_url='http://localhost:9999/mcp', context_packet=True)
        merge = context_packet_canary.build_benchmark_env(base_env, mcp_url='http://localhost:9999/mcp', context_packet=False, context_packet_merge=True)

        merge_capped = context_packet_canary.build_benchmark_env(
            base_env,
            mcp_url='http://localhost:9999/mcp',
            context_packet=False,
            context_packet_merge=True,
            context_packet_merge_append_top_k=2,
        )
        merge_ref_gate = context_packet_canary.build_benchmark_env(
            base_env,
            mcp_url='http://localhost:9999/mcp',
            context_packet=False,
            context_packet_merge=True,
            context_packet_merge_ref_gate=True,
        )

        self.assertEqual(baseline['MCP_URL'], 'http://localhost:9999/mcp')
        self.assertEqual(treatment['MCP_URL'], 'http://localhost:9999/mcp')
        self.assertEqual(merge['MCP_URL'], 'http://localhost:9999/mcp')
        self.assertEqual(baseline['USE_QUERY_EXPANSION'], treatment['USE_QUERY_EXPANSION'])
        self.assertEqual(merge['USE_QUERY_EXPANSION'], baseline['USE_QUERY_EXPANSION'])
        self.assertEqual(baseline['INCLUDE_RECALL_TELEMETRY'], '1')
        self.assertEqual(treatment['INCLUDE_RECALL_TELEMETRY'], '1')
        self.assertNotIn('USE_CONTEXT_PACKET', baseline)
        self.assertEqual(treatment['USE_CONTEXT_PACKET'], '1')
        self.assertNotIn('USE_CONTEXT_PACKET', merge)
        self.assertEqual(merge['USE_CONTEXT_PACKET_MERGE'], '1')
        self.assertEqual(merge_capped['USE_CONTEXT_PACKET_MERGE'], '1')
        self.assertEqual(merge_capped['CONTEXT_PACKET_MERGE_APPEND_TOP_K'], '2')
        self.assertEqual(merge_ref_gate['USE_CONTEXT_PACKET_MERGE'], '1')
        self.assertEqual(merge_ref_gate['CONTEXT_PACKET_MERGE_REF_GATE'], '1')
        for incompatible in [
            'USE_CONTEXT_RERANK',
            'USE_APPEND_CONTEXT_EXPANSION',
            'USE_GATED_APPEND_CONTEXT_EXPANSION',
            'USE_LEGACY_CONTEXT_ASSEMBLY',
            'USE_FULL_DOMAIN_CONTEXT',
            'LOCOMO_RETRIEVAL_TELEMETRY',
            'USE_CONTEXT_PACKET_MERGE',
        ]:
            self.assertNotIn(incompatible, baseline)
            self.assertNotIn(incompatible, treatment)
        for incompatible in [
            'USE_CONTEXT_RERANK',
            'USE_APPEND_CONTEXT_EXPANSION',
            'USE_GATED_APPEND_CONTEXT_EXPANSION',
            'USE_LEGACY_CONTEXT_ASSEMBLY',
            'USE_FULL_DOMAIN_CONTEXT',
            'LOCOMO_RETRIEVAL_TELEMETRY',
            'USE_CONTEXT_PACKET',
        ]:
            self.assertNotIn(incompatible, merge)

    def test_tool_names_supports_dict_or_list_mcp_tools_response(self):
        self.assertEqual(
            context_packet_canary.tool_names_from_response([
                {'name': 'recall'},
                {'name': 'context_packet'},
            ]),
            ['recall', 'context_packet'],
        )
        self.assertEqual(
            context_packet_canary.tool_names_from_response({
                'tools': [
                    {'name': 'recall'},
                    {'name': 'context_packet'},
                ]
            }),
            ['recall', 'context_packet'],
        )

    def test_cleanup_sql_includes_context_graph_tables_with_array_evidence_links(self):
        sql = context_packet_canary.locomo_cleanup_sql()

        self.assertIn('DELETE FROM context_graph_edges', sql)
        self.assertIn('evidence_memory_ids ? id', sql)
        self.assertIn('DELETE FROM decision_traces', sql)
        self.assertIn('DELETE FROM self_model_observations', sql)
        self.assertIn('entity_a IN', sql)
        self.assertIn('entity_b IN', sql)

    def test_paired_artifact_validation_requires_same_rows_and_context_metadata(self):
        fixed_rows = [
            {
                'one_based_index': 2,
                'question': 'second question',
                'question_sha256': context_packet_canary.sha256_text('second question'),
                'label': 'tiny_temporal',
            }
        ]
        baseline = {
            'overall_score': 50.0,
            'condition': {'context_packet': False, 'context_packet_merge': False},
            'details': [
                {
                    'question': 'second question',
                    'row_identity': fixed_rows[0],
                    'recall_telemetry': {'counts': {'final_answer_context_count': 3}, 'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1}},
                }
            ],
        }
        treatment = {
            'overall_score': 50.0,
            'condition': {'context_packet': False, 'context_packet_merge': True},
            'details': [
                {
                    'question': 'second question',
                    'row_identity': fixed_rows[0],
                    'recall_telemetry': {
                        'counts': {
                            'context_packet_merge_enabled': True,
                            'base_final_answer_context_count': 3,
                            'final_answer_context_count': 4,
                        },
                        'context_packet': {'provenance_summary': {'memory_ids': ['m1']}},
                        'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1},
                    },
                }
            ],
        }

        comparison = context_packet_canary.validate_paired_artifacts(
            baseline,
            treatment,
            fixed_rows,
            treatment_context_packet=False,
            treatment_context_packet_merge=True,
        )

        self.assertTrue(comparison['row_identity_ok'])
        self.assertTrue(comparison['condition_metadata_ok'])
        self.assertTrue(comparison['context_packet_telemetry_ok'])
        self.assertEqual(comparison['row_count'], 1)
        self.assertEqual(comparison['gold_evidence_ref_hit_rate']['baseline'], 1.0)
        self.assertEqual(comparison['gold_evidence_ref_hit_rate']['treatment'], 1.0)
        self.assertEqual(comparison['gold_evidence_ref_hit_delta'], 0.0)
        self.assertTrue(comparison['gold_evidence_ref_hit_gate'])
        self.assertEqual(comparison['score_delta_pp'], 0.0)
        self.assertTrue(comparison['score_non_regression_gate'])

        mismatched_treatment = json.loads(json.dumps(treatment))
        mismatched_treatment['details'][0]['row_identity']['question_sha256'] = '1' * 64
        with self.assertRaisesRegex(ValueError, 'paired_row_identity_mismatch'):
            context_packet_canary.validate_paired_artifacts(
                baseline,
                mismatched_treatment,
                fixed_rows,
                treatment_context_packet=False,
                treatment_context_packet_merge=True,
            )
    def test_paired_artifact_validation_reports_baseline_prefix_and_answer_change_diagnostics(self):
        fixed_rows = [{
            'one_based_index': 1,
            'question': 'merge question',
            'question_sha256': context_packet_canary.sha256_text('merge question'),
            'label': 'merge_row',
        }]
        baseline = {
            'condition': {'context_packet': False, 'context_packet_merge': False},
            'details': [{
                'question': 'merge question',
                'row_identity': fixed_rows[0],
                'predicted': 'baseline answer',
                'score': 0.5,
                'recall_telemetry': {
                    'final_context': [{'id': 'b1'}, {'id': 'b2'}],
                    'counts': {'final_answer_context_count': 2},
                    'gold_evidence_ref_coverage': {'gold_ref_count': 2, 'final_context_refs_matched': 1},
                },
            }],
        }
        treatment = {
            'condition': {'context_packet': False, 'context_packet_merge': True},
            'details': [{
                'question': 'merge question',
                'row_identity': fixed_rows[0],
                'predicted': 'merge answer',
                'score': 1.0,
                'recall_telemetry': {
                    'final_context_before_packet_merge': [{'id': 'b1'}, {'id': 'b2'}],
                    'final_context': [{'id': 'b1'}, {'id': 'b2'}, {'id': 'p1'}],
                    'counts': {'context_packet_merge_enabled': True, 'base_final_answer_context_count': 2, 'final_answer_context_count': 3},
                    'context_packet': {'provenance_summary': {'memory_ids': ['p1']}},
                    'gold_evidence_ref_coverage': {'gold_ref_count': 2, 'final_context_refs_matched': 2},
                },
            }],
        }

        comparison = context_packet_canary.validate_paired_artifacts(
            baseline,
            treatment,
            fixed_rows,
            treatment_context_packet=False,
            treatment_context_packet_merge=True,
        )

        self.assertEqual(comparison['baseline_prefix_preserved_by_row'], [True])
        self.assertEqual(comparison['baseline_prefix_preserved_rate'], 1.0)
        self.assertEqual(comparison['answer_change_diagnostics'][0]['answer_changed'], True)
        self.assertEqual(comparison['answer_change_diagnostics'][0]['score_delta'], 0.5)

    def test_paired_artifact_validation_reports_packet_append_attribution_and_category_gates(self):
        fixed_rows = [
            {
                'one_based_index': 1,
                'question': 'appended question',
                'question_sha256': context_packet_canary.sha256_text('appended question'),
                'label': 'appended_row',
                'cat': 'temporal',
            },
            {
                'one_based_index': 2,
                'question': 'not appended question',
                'question_sha256': context_packet_canary.sha256_text('not appended question'),
                'label': 'not_appended_row',
                'cat': 'adversarial',
            },
        ]
        baseline = {
            'overall_score': 50.0,
            'category_scores': {'cat-temporal': 0.0, 'cat-adversarial': 100.0},
            'condition': {'context_packet': False, 'context_packet_merge': False},
            'details': [
                {
                    'question': 'appended question',
                    'row_identity': fixed_rows[0],
                    'cat': 'temporal',
                    'predicted': 'baseline appended',
                    'score': 0.0,
                    'recall_telemetry': {
                        'final_context': [{'id': 'b1'}],
                        'counts': {'final_answer_context_count': 1},
                        'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 0},
                    },
                },
                {
                    'question': 'not appended question',
                    'row_identity': fixed_rows[1],
                    'cat': 'adversarial',
                    'predicted': 'baseline no append',
                    'score': 1.0,
                    'recall_telemetry': {
                        'final_context': [{'id': 'b2'}],
                        'counts': {'final_answer_context_count': 1},
                        'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1},
                    },
                },
            ],
        }
        treatment = {
            'overall_score': 50.0,
            'category_scores': {'cat-temporal': 100.0, 'cat-adversarial': 0.0},
            'condition': {'context_packet': False, 'context_packet_merge': True},
            'details': [
                {
                    'question': 'appended question',
                    'row_identity': fixed_rows[0],
                    'cat': 'temporal',
                    'predicted': 'better appended',
                    'score': 1.0,
                    'recall_telemetry': {
                        'final_context_before_packet_merge': [{'id': 'b1'}],
                        'final_context': [{'id': 'b1'}, {'id': 'p1'}],
                        'counts': {'context_packet_merge_enabled': True, 'packet_episodic_added_count': 1},
                        'context_packet': {'provenance_summary': {'memory_ids': ['p1']}},
                        'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1},
                    },
                },
                {
                    'question': 'not appended question',
                    'row_identity': fixed_rows[1],
                    'cat': 'adversarial',
                    'predicted': 'worse no append',
                    'score': 0.0,
                    'recall_telemetry': {
                        'final_context_before_packet_merge': [{'id': 'b2'}],
                        'final_context': [{'id': 'b2'}],
                        'counts': {'context_packet_merge_enabled': True, 'packet_episodic_added_count': 0},
                        'context_packet': {'provenance_summary': {'memory_ids': []}},
                        'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1},
                    },
                },
            ],
        }

        comparison = context_packet_canary.validate_paired_artifacts(
            baseline,
            treatment,
            fixed_rows,
            treatment_context_packet=False,
            treatment_context_packet_merge=True,
        )

        self.assertEqual(comparison['packet_append_attribution']['rows_with_packet_append'], 1)
        self.assertEqual(comparison['packet_append_attribution']['score_delta_when_packet_appended'], 1.0)
        self.assertEqual(comparison['packet_append_attribution']['score_delta_when_no_packet_appended'], -1.0)
        self.assertEqual(comparison['packet_appended_by_row'], [True, False])
        self.assertEqual(comparison['category_regression_gates']['cat-temporal']['delta'], 100.0)
        self.assertEqual(comparison['category_regression_gates']['cat-adversarial']['delta'], -100.0)
        self.assertFalse(comparison['category_regression_gates']['no_severe_category_collapse'])

    def test_answer_question_with_frozen_context_replay_uses_baseline_context_without_recall(self):
        calls = []
        prompts = []

        class FakeModule:
            ANSWER_MODEL = 'gpt-test'
            CONTEXT_PACKET_TOP_K = 8
            CONTEXT_PACKET_MERGE_APPEND_TOP_K = 0
            USE_CONTEXT_PACKET_MERGE_REF_GATE = False

            @staticmethod
            def mcp_post(tool, payload):
                calls.append((tool, payload))
                if tool == 'recall':
                    raise AssertionError('frozen replay must not call recall')
                self.assertEqual(tool, 'context_packet')
                return {'episodic_evidence': [{'id': 'p1', 'content': 'packet Caroline evidence', 'refs': {'turn_start': 2}}]}

            @staticmethod
            def _append_packet_evidence_to_baseline(base_memories, packet, max_added=None, evidence_refs=None, ref_gate=False):
                added = packet['episodic_evidence']
                return list(base_memories) + added, added, len(added), 0, 0

            @staticmethod
            def _memory_telemetry_projection(memory, rank=None):
                content = memory.get('content', '')
                return {
                    'rank': rank,
                    'id': memory.get('id'),
                    'snippet': content[:160],
                    'refs': memory.get('refs', {}),
                    'content_sha256': context_packet_canary.sha256_text(content),
                }

            @staticmethod
            def _context_packet_telemetry_projection(packet):
                return {'provenance_summary': {'memory_ids': [m['id'] for m in packet['episodic_evidence']]}}

            @staticmethod
            def _render_plain_context(memories, question):
                return '\n'.join(f"- {memory['content']}" for memory in memories)

            @staticmethod
            def _count_ref_coverage(evidence_refs, memories):
                return 1

            @staticmethod
            def llm_call(messages, model='gpt-test', max_tokens=200, retries=3):
                prompts.append(messages[1]['content'])
                return 'answer from frozen context'

        answer, memory_count, telemetry = context_packet_canary.answer_question_with_frozen_context(
            FakeModule,
            'Who found the rainbow sidewalk?',
            'locomo-conv-26',
            [{'id': 'b1', 'content': 'baseline Melanie evidence', 'refs': {'turn_start': 1}}],
            evidence_refs=[{'turn_start': 1}],
            context_packet_merge=True,
        )

        self.assertEqual(answer, 'answer from frozen context')
        self.assertEqual(memory_count, 2)
        self.assertEqual([call[0] for call in calls], ['context_packet'])
        self.assertIn('baseline Melanie evidence', prompts[0])
        self.assertIn('packet Caroline evidence', prompts[0])
        self.assertLess(prompts[0].index('baseline Melanie evidence'), prompts[0].index('packet Caroline evidence'))
        self.assertTrue(telemetry['counts']['frozen_context_replay_enabled'])
        self.assertEqual([m['id'] for m in telemetry['final_context_before_packet_merge']], ['b1'])
        self.assertEqual([m['id'] for m in telemetry['final_context']], ['b1', 'p1'])

    def test_frozen_replay_allows_intentional_baseline_residue_between_arms(self):
        dirty = {'ok': False, 'memories': 49}
        clean = {'ok': True, 'memories': 0}

        self.assertFalse(context_packet_canary.should_block_on_hygiene(dirty, clean_requested=False))
        self.assertTrue(context_packet_canary.should_block_on_hygiene(dirty, clean_requested=True))
        self.assertFalse(context_packet_canary.should_block_on_hygiene(clean, clean_requested=True))

    def test_paired_artifact_validation_reports_frozen_context_hash_gate(self):
        fixed_rows = [{
            'one_based_index': 1,
            'question': 'frozen question',
            'question_sha256': context_packet_canary.sha256_text('frozen question'),
            'label': 'frozen_row',
            'cat': 'single-hop',
        }]
        baseline = {
            'condition': {'context_packet': False, 'context_packet_merge': False, 'frozen_context_replay': False},
            'details': [{
                'question': 'frozen question',
                'row_identity': fixed_rows[0],
                'predicted': 'baseline answer',
                'score': 1.0,
                'frozen_baseline_context_sha256': context_packet_canary.frozen_context_hash([{'id': 'b1'}]),
                'answer_prompt_context_sha256': 'baseline-prompt',
                'recall_telemetry': {
                    'final_context': [{'id': 'b1'}],
                    'counts': {'final_answer_context_count': 1},
                    'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1},
                },
            }],
        }
        treatment = {
            'condition': {'context_packet': False, 'context_packet_merge': True, 'frozen_context_replay': True},
            'details': [{
                'question': 'frozen question',
                'row_identity': fixed_rows[0],
                'predicted': 'treatment answer',
                'score': 1.0,
                'frozen_baseline_context_sha256': context_packet_canary.frozen_context_hash([{'id': 'b1'}]),
                'answer_prompt_context_sha256': 'treatment-prompt',
                'recall_telemetry': {
                    'final_context_before_packet_merge': [{'id': 'b1'}],
                    'final_context': [{'id': 'b1'}, {'id': 'p1'}],
                    'counts': {
                        'context_packet_merge_enabled': True,
                        'frozen_context_replay_enabled': True,
                        'packet_episodic_added_count': 1,
                    },
                    'context_packet': {'provenance_summary': {'memory_ids': ['p1']}},
                    'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1},
                },
            }],
        }

        comparison = context_packet_canary.validate_paired_artifacts(
            baseline,
            treatment,
            fixed_rows,
            treatment_context_packet=False,
            treatment_context_packet_merge=True,
            frozen_replay=True,
        )

        self.assertTrue(comparison['frozen_context_replay_ok'])
        self.assertEqual(comparison['frozen_context_hash_match_by_row'], [True])
        self.assertEqual(comparison['frozen_context_hash_match_rate'], 1.0)
        self.assertEqual(comparison['prompt_context_delta_source_by_row'], ['packet_transform'])

        mismatched_treatment = json.loads(json.dumps(treatment))
        mismatched_treatment['details'][0]['frozen_baseline_context_sha256'] = 'def456'
        with self.assertRaisesRegex(ValueError, 'frozen_context_hash_mismatch'):
            context_packet_canary.validate_paired_artifacts(
                baseline,
                mismatched_treatment,
                fixed_rows,
                treatment_context_packet=False,
                treatment_context_packet_merge=True,
                frozen_replay=True,
            )

    def test_paired_artifact_validation_reports_row_183_role_attribution_regression(self):
        fixed_rows = [{
            'one_based_index': 183,
            'question': 'Who found the rainbow sidewalk?',
            'question_sha256': context_packet_canary.sha256_text('Who found the rainbow sidewalk?'),
            'label': 'row_183',
            'cat': 'adversarial',
        }]
        baseline = {
            'condition': {'context_packet': False, 'context_packet_merge': False},
            'details': [{
                'question': 'Who found the rainbow sidewalk?',
                'row_identity': fixed_rows[0],
                'cat': 'adversarial',
                'predicted': 'Melanie found the rainbow sidewalk.',
                'score': 1.0,
                'recall_telemetry': {
                    'final_context': [{'id': 'b1'}],
                    'counts': {'final_answer_context_count': 1},
                    'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1},
                },
            }],
        }
        treatment = {
            'condition': {'context_packet': False, 'context_packet_merge': True},
            'details': [{
                'question': 'Who found the rainbow sidewalk?',
                'row_identity': fixed_rows[0],
                'cat': 'adversarial',
                'predicted': 'Caroline found it, not Melanie.',
                'score': 0.0,
                'recall_telemetry': {
                    'final_context_before_packet_merge': [{'id': 'b1'}],
                    'final_context': [{'id': 'b1'}, {'id': 'p1'}],
                    'counts': {'context_packet_merge_enabled': True, 'packet_episodic_added_count': 1},
                    'context_packet': {'provenance_summary': {'memory_ids': ['p1']}},
                    'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1},
                },
            }],
        }

        comparison = context_packet_canary.validate_paired_artifacts(
            baseline,
            treatment,
            fixed_rows,
            treatment_context_packet=False,
            treatment_context_packet_merge=True,
        )

        diagnostic = comparison['row_183_role_attribution_diagnostic']
        self.assertTrue(diagnostic['present'])
        self.assertTrue(diagnostic['role_attribution_regression'])
        self.assertFalse(diagnostic['role_attribution_regression_absent'])
        self.assertTrue(diagnostic['baseline_mentions_melanie'])
        self.assertTrue(diagnostic['treatment_mentions_caroline'])
        self.assertEqual(diagnostic['score_delta'], -1.0)

    def test_preregistered_larger_slice_requires_20_to_30_rows_and_category_coverage(self):
        rows = []
        cats = ['single-hop', 'temporal', 'multi-hop', 'unanswerable', 'adversarial']
        for idx in range(25):
            rows.append({
                'one_based_index': idx + 1,
                'cat': cats[idx % len(cats)],
                'question': f'question {idx}',
                'question_sha256': context_packet_canary.sha256_text(f'question {idx}'),
                'label': f'row_{idx}',
            })

        proof = context_packet_canary.validate_preregistered_larger_slice({'selected_rows': rows}, min_rows=20, max_rows=30)

        self.assertTrue(proof['ok'])
        self.assertEqual(proof['row_count'], 25)
        self.assertEqual(proof['category_counts']['adversarial'], 5)

        with self.assertRaisesRegex(ValueError, 'larger_slice_prereg_invalid'):
            context_packet_canary.validate_preregistered_larger_slice({'selected_rows': rows[:19]}, min_rows=20, max_rows=30)

    def test_canary_input_slice_records_session_order_mapping(self):
        data = [{
            'sample_id': 'conv-26',
            'conversation': {
                'session_1': [],
                'session_2': [],
                'session_10': [],
            },
            'qa': [
                {'category': 1, 'question': 'first question', 'answer': 'first'},
            ],
        }]
        fixed_rows = [{
            'one_based_index': 1,
            'cat': 'single-hop',
            'question': 'first question',
            'question_sha256': context_packet_canary.sha256_text('first question'),
            'label': 'tiny_single_hop',
        }]

        proof = context_packet_canary.validate_fixed_row_identity(data, fixed_rows)

        self.assertEqual(proof['session_order_mapping']['ordering'], 'lexicographic')
        self.assertEqual(proof['session_order_mapping']['ingest_to_dialogue_session'], {
            1: 'D1',
            2: 'D10',
            3: 'D2',
        })


if __name__ == '__main__':
    unittest.main()
