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
