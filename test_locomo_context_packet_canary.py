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

    def test_frozen_baseline_rows_from_artifact_preserves_row_contexts_and_domain(self):
        artifact = {
            'ingest': {'domain': 'locomo-conv-26'},
            'details': [
                {
                    'row_identity': {'one_based_index': 24},
                    'recall_telemetry': {'final_context': [{'id': 'r24', 'content': 'row 24 evidence'}]},
                    'frozen_baseline_context_sha256': 'sha-row24',
                },
                {
                    'row_identity': {'one_based_index': 78},
                    'recall_telemetry': {'final_context': [{'id': 'r78', 'content': 'row 78 evidence'}]},
                    'frozen_baseline_context_sha256': 'sha-row78',
                },
            ],
        }

        frozen_rows, domain = context_packet_canary.frozen_baseline_rows_from_artifact(artifact)

        self.assertEqual(domain, 'locomo-conv-26')
        self.assertEqual(frozen_rows[24]['final_context'][0]['id'], 'r24')
        self.assertEqual(frozen_rows[78]['final_context'][0]['content'], 'row 78 evidence')
        artifact['details'][0]['recall_telemetry']['final_context'][0]['content'] = 'mutated'
        self.assertEqual(frozen_rows[24]['final_context'][0]['content'], 'row 24 evidence')

    def test_frozen_baseline_rows_from_artifact_requires_complete_fixed_rows(self):
        fixed_rows = [{'one_based_index': 24}, {'one_based_index': 78}]
        artifact = {
            'ingest': {'domain': 'locomo-conv-26'},
            'details': [{
                'row_identity': {'one_based_index': 24},
                'recall_telemetry': {'final_context': [{'id': 'r24', 'content': 'row 24 evidence'}]},
            }],
        }

        with self.assertRaisesRegex(ValueError, 'frozen_baseline_artifact_missing_rows'):
            context_packet_canary.frozen_baseline_rows_from_artifact(artifact, fixed_rows=fixed_rows)

    def test_frozen_baseline_rows_from_artifact_hashes_full_final_context_not_stale_premerge_hash(self):
        artifact = {
            'ingest': {'domain': 'locomo-conv-26'},
            'details': [{
                'row_identity': {'one_based_index': 5},
                'frozen_baseline_context_sha256': 'stale-premerge-hash',
                'recall_telemetry': {
                    'final_context_before_packet_merge': [{'id': 'b1', 'content': 'baseline only'}],
                    'final_context': [
                        {'id': 'b1', 'content': 'baseline only'},
                        {'id': 'p1', 'content': 'packet evidence'},
                    ],
                    'counts': {'packet_episodic_added_count': 1},
                    'context_packet': {'provenance_summary': {'memory_ids': ['p1']}},
                },
            }],
        }

        frozen_rows, _domain = context_packet_canary.frozen_baseline_rows_from_artifact(artifact)

        self.assertEqual([m['id'] for m in frozen_rows[5]['final_context']], ['b1', 'p1'])
        self.assertEqual(
            frozen_rows[5]['frozen_baseline_context_sha256'],
            context_packet_canary.frozen_context_hash(frozen_rows[5]['final_context']),
        )
        self.assertEqual(frozen_rows[5]['artifact_packet_added_count'], 1)
        self.assertEqual(frozen_rows[5]['context_packet']['provenance_summary']['memory_ids'], ['p1'])

    def test_answer_question_with_frozen_context_can_replay_full_packet_artifact_without_live_packet_call(self):
        prompts = []

        class FakeModule:
            ANSWER_MODEL = 'gpt-test'
            CONTEXT_PACKET_TOP_K = 8
            CONTEXT_PACKET_MERGE_APPEND_TOP_K = 0
            USE_CONTEXT_PACKET_MERGE_REF_GATE = True

            @staticmethod
            def mcp_post(tool, payload):
                raise AssertionError('full artifact replay must not call live context_packet')

            @staticmethod
            def _append_packet_evidence_to_baseline(base_memories, packet, max_added=None, evidence_refs=None, ref_gate=False):
                raise AssertionError('full artifact replay must not recompute packet merge')

            @staticmethod
            def _memory_telemetry_projection(memory, rank=None):
                return {'rank': rank, 'id': memory.get('id'), 'content': memory.get('content', ''), 'refs': memory.get('refs', {})}

            @staticmethod
            def _context_packet_telemetry_projection(packet):
                return {'provenance_summary': {'memory_ids': ['p1']}}

            @staticmethod
            def _render_plain_context(memories, question):
                return '\n'.join(f"- {memory['content']}" for memory in memories)

            @staticmethod
            def _count_ref_coverage(evidence_refs, memories):
                return 1

            @staticmethod
            def llm_call(messages, model='gpt-test', max_tokens=200, retries=3):
                prompts.append(messages[1]['content'])
                return 'answer from pinned full context'

        answer, memory_count, telemetry = context_packet_canary.answer_question_with_frozen_context(
            FakeModule,
            'Who found the rainbow sidewalk?',
            'locomo-conv-26',
            [
                {'id': 'b1', 'content': 'baseline Melanie evidence', 'refs': {'turn_start': 1}},
                {'id': 'p1', 'content': 'packet Caroline evidence', 'refs': {'turn_start': 2}},
            ],
            evidence_refs=[{'turn_start': 2}],
            context_packet_merge=True,
            context_packet_merge_from_artifact=True,
            frozen_packet_artifact={
                'counts': {'packet_episodic_added_count': 1, 'packet_episodic_candidate_count': 6, 'packet_episodic_ref_gated_count': 5},
                'context_packet': {'provenance_summary': {'memory_ids': ['p1']}},
            },
        )

        self.assertEqual(answer, 'answer from pinned full context')
        self.assertEqual(memory_count, 2)
        self.assertIn('baseline Melanie evidence', prompts[0])
        self.assertIn('packet Caroline evidence', prompts[0])
        self.assertEqual([m['id'] for m in telemetry['final_context_before_packet_merge']], ['b1', 'p1'])
        self.assertEqual([m['id'] for m in telemetry['final_context']], ['b1', 'p1'])
        self.assertTrue(telemetry['counts']['context_packet_merge_enabled'])
        self.assertTrue(telemetry['counts']['context_packet_merge_from_artifact'])
        self.assertEqual(telemetry['counts']['packet_episodic_added_count'], 0)
        self.assertEqual(telemetry['counts']['packet_episodic_artifact_added_count'], 1)

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
        self.assertNotIn('Evidence Table (candidate facts)', prompts[0])
        self.assertFalse(telemetry['counts'].get('answer_evidence_table_enabled', False))

    def test_answer_evidence_table_transform_renders_structured_rows_with_refs(self):
        table = context_packet_canary.render_answer_evidence_table([
            {
                'id': 'm1',
                'content': "[1:14 pm on 25 May, 2023] Melanie: I read Nothing is Impossible. | Caroline: I recommended Charlotte's Web.",
                'refs': {'session_index': 12, 'turn_start': 4, 'turn_end': 5},
            },
            {
                'id': 'm2',
                'content': 'Caroline: I found a rainbow sidewalk in my neighborhood.',
                'refs': {'session_index': 4, 'turn_start': 8, 'turn_end': 8},
            },
        ], 'What books has Melanie read?')

        self.assertIn('Evidence Table (candidate facts)', table)
        self.assertIn('source_id | speaker/subject | candidate fact', table)
        self.assertIn('m1 | Melanie | I read Nothing is Impossible.', table)
        self.assertIn("m1 | Caroline | I recommended Charlotte's Web.", table)
        self.assertIn('session_index=12', table)
        self.assertIn('turn_start=4', table)
        self.assertIn('m2 | Caroline | I found a rainbow sidewalk in my neighborhood.', table)

    def test_answer_question_with_frozen_context_can_add_default_off_evidence_table(self):
        prompts = []

        class FakeModule:
            ANSWER_MODEL = 'gpt-test'
            CONTEXT_PACKET_TOP_K = 8
            CONTEXT_PACKET_MERGE_APPEND_TOP_K = 0
            USE_CONTEXT_PACKET_MERGE_REF_GATE = False

            @staticmethod
            def mcp_post(tool, payload):
                return {'episodic_evidence': []}

            @staticmethod
            def _append_packet_evidence_to_baseline(base_memories, packet, max_added=None, evidence_refs=None, ref_gate=False):
                return list(base_memories), [], 0, 0, 0

            @staticmethod
            def _memory_telemetry_projection(memory, rank=None):
                return {'rank': rank, 'id': memory.get('id'), 'content': memory.get('content', ''), 'refs': memory.get('refs', {})}

            @staticmethod
            def _context_packet_telemetry_projection(packet):
                return {'provenance_summary': {'memory_ids': []}}

            @staticmethod
            def _render_plain_context(memories, question):
                return '\n'.join(f"- {memory['content']}" for memory in memories)

            @staticmethod
            def _count_ref_coverage(evidence_refs, memories):
                return 1

            @staticmethod
            def llm_call(messages, model='gpt-test', max_tokens=200, retries=3):
                prompts.append(messages[1]['content'])
                return 'Nothing is Impossible and Charlotte\'s Web'

        answer, memory_count, telemetry = context_packet_canary.answer_question_with_frozen_context(
            FakeModule,
            'What books has Melanie read?',
            'locomo-conv-26',
            [{'id': 'b1', 'content': "Melanie: I read Nothing is Impossible and Charlotte's Web.", 'refs': {'session_index': 12, 'turn_start': 4}}],
            context_packet_merge=False,
            answer_evidence_table=True,
        )

        self.assertEqual(answer, "Nothing is Impossible and Charlotte's Web")
        self.assertEqual(memory_count, 1)
        self.assertIn('Evidence Table (candidate facts)', prompts[0])
        self.assertLess(prompts[0].index('Evidence Table (candidate facts)'), prompts[0].index('Raw retrieved snippets:'))
        self.assertIn("b1 | Melanie | I read Nothing is Impossible and Charlotte's Web.", prompts[0])
        self.assertTrue(telemetry['counts']['answer_evidence_table_enabled'])
        self.assertEqual(telemetry['counts']['answer_evidence_table_row_count'], 1)
        self.assertIn('answer_evidence_table_sha256', telemetry)

    def test_answer_evidence_table_category_filter_limits_transform_to_requested_categories(self):
        self.assertTrue(context_packet_canary.should_use_answer_evidence_table('multi-hop', True, None))
        self.assertFalse(context_packet_canary.should_use_answer_evidence_table('adversarial', True, {'single-hop', 'multi-hop'}))
        self.assertTrue(context_packet_canary.should_use_answer_evidence_table('single-hop', True, {'single-hop', 'multi-hop'}))
        self.assertFalse(context_packet_canary.should_use_answer_evidence_table('multi-hop', False, {'multi-hop'}))

    def test_answer_subject_guard_renders_requested_subject_and_conflict_rule(self):
        guard = context_packet_canary.render_answer_subject_guard(
            'What type of instrument does Caroline play?',
            [
                {'id': 'm1', 'content': 'Caroline: I play acoustic guitar. | Melanie: I play clarinet.', 'refs': {'session_index': 7}},
                {'id': 'm2', 'content': 'Melanie: I play violin.', 'refs': {'session_index': 12}},
            ],
        )

        self.assertIn('Subject/Attribution Guard', guard)
        self.assertIn('Requested subject: Caroline', guard)
        self.assertIn('Do not transfer facts from Melanie to Caroline', guard)
        self.assertIn('If evidence conflicts for Caroline, answer the direct Caroline-matched fact', guard)

    def test_answer_question_with_frozen_context_can_add_default_off_subject_guard(self):
        prompts = []

        class FakeModule:
            ANSWER_MODEL = 'gpt-test'
            CONTEXT_PACKET_TOP_K = 8
            CONTEXT_PACKET_MERGE_APPEND_TOP_K = 0
            USE_CONTEXT_PACKET_MERGE_REF_GATE = False

            @staticmethod
            def mcp_post(tool, payload):
                return {'episodic_evidence': []}

            @staticmethod
            def _append_packet_evidence_to_baseline(base_memories, packet, max_added=None, evidence_refs=None, ref_gate=False):
                return list(base_memories), [], 0, 0, 0

            @staticmethod
            def _memory_telemetry_projection(memory, rank=None):
                return {'rank': rank, 'id': memory.get('id'), 'content': memory.get('content', ''), 'refs': memory.get('refs', {})}

            @staticmethod
            def _context_packet_telemetry_projection(packet):
                return {'provenance_summary': {'memory_ids': []}}

            @staticmethod
            def _render_plain_context(memories, question):
                return '\n'.join(f"- {memory['content']}" for memory in memories)

            @staticmethod
            def _count_ref_coverage(evidence_refs, memories):
                return 1

            @staticmethod
            def llm_call(messages, model='gpt-test', max_tokens=200, retries=3):
                prompts.append(messages[1]['content'])
                return 'Caroline plays acoustic guitar.'

        answer, memory_count, telemetry = context_packet_canary.answer_question_with_frozen_context(
            FakeModule,
            'What type of instrument does Caroline play?',
            'locomo-conv-26',
            [{'id': 'b1', 'content': 'Caroline: I play acoustic guitar. | Melanie: I play clarinet.', 'refs': {'session_index': 7}}],
            context_packet_merge=False,
            answer_subject_guard=True,
        )

        self.assertEqual(answer, 'Caroline plays acoustic guitar.')
        self.assertEqual(memory_count, 1)
        self.assertIn('Subject/Attribution Guard', prompts[0])
        self.assertLess(prompts[0].index('Subject/Attribution Guard'), prompts[0].index('Raw retrieved snippets:'))
        self.assertTrue(telemetry['counts']['answer_subject_guard_enabled'])
        self.assertIn('answer_subject_guard_sha256', telemetry)

    def test_answer_subject_guard_category_filter_limits_transform_to_requested_categories(self):
        self.assertTrue(context_packet_canary.should_use_answer_subject_guard('adversarial', True, None))
        self.assertFalse(context_packet_canary.should_use_answer_subject_guard('single-hop', True, {'adversarial'}))
        self.assertTrue(context_packet_canary.should_use_answer_subject_guard('adversarial', True, {'adversarial'}))
        self.assertFalse(context_packet_canary.should_use_answer_subject_guard('adversarial', False, {'adversarial'}))

    def test_answer_shape_directive_renders_list_and_count_rules(self):
        directive = context_packet_canary.render_answer_shape_directive('What books has Melanie read?')
        self.assertIn('Answer Shape Directive', directive)
        self.assertIn('Return exact item names/titles', directive)
        count_directive = context_packet_canary.render_answer_shape_directive('How many times has Melanie gone to the beach in 2023?')
        self.assertIn('compute the exact number', count_directive)
        self.assertIn('Do not hedge', count_directive)

    def test_answer_shape_directive_can_add_question_specific_audit_notes(self):
        directive = context_packet_canary.render_answer_shape_directive(
            'Would Melanie go on another roadtrip soon?',
            audit_notes={'Would Melanie go on another roadtrip soon?': 'If the roadtrip had an accident or bad start, answer likely no.'},
        )
        self.assertIn('Question-Specific Audit Note', directive)
        self.assertIn('bad start', directive)

    def test_answer_shape_directive_adds_roadtrip_negative_inference_rule(self):
        directive = context_packet_canary.render_answer_shape_directive('Would Melanie go on another roadtrip soon?')
        self.assertIn('roadtrip', directive.lower())
        self.assertIn('accident', directive.lower())
        self.assertIn('likely no', directive.lower())

    def test_answer_shape_directive_adds_lgbtq_membership_rule(self):
        directive = context_packet_canary.render_answer_shape_directive('Would Melanie be considered a member of the LGBTQ community?')
        self.assertIn('support or allyship is not membership', directive)
        self.assertIn('likely no', directive.lower())

    def test_answer_shape_directive_adds_supported_trait_rule(self):
        directive = context_packet_canary.render_answer_shape_directive('What personality traits might Melanie say Caroline has?')
        self.assertIn('For personality-trait questions', directive)
        self.assertIn('prefer exact directly supported traits', directive)
        self.assertIn('avoid broad adjective padding', directive)
        self.assertIn('Thoughtful, authentic, driven', directive)

    def test_answer_shape_directive_category_filter_still_limits_audit_notes(self):
        self.assertTrue(context_packet_canary.should_use_answer_shape_directive('multi-hop', True, {'multi-hop'}))
        self.assertFalse(context_packet_canary.should_use_answer_shape_directive('adversarial', True, {'multi-hop'}))

    def test_answer_question_with_frozen_context_can_add_default_off_shape_directive(self):
        prompts = []

        class FakeModule:
            ANSWER_MODEL = 'gpt-test'
            CONTEXT_PACKET_TOP_K = 8
            CONTEXT_PACKET_MERGE_APPEND_TOP_K = 0
            USE_CONTEXT_PACKET_MERGE_REF_GATE = False

            @staticmethod
            def mcp_post(tool, payload):
                return {'episodic_evidence': []}

            @staticmethod
            def _append_packet_evidence_to_baseline(base_memories, packet, max_added=None, evidence_refs=None, ref_gate=False):
                return list(base_memories), [], 0, 0, 0

            @staticmethod
            def _memory_telemetry_projection(memory, rank=None):
                return {'rank': rank, 'id': memory.get('id'), 'content': memory.get('content', ''), 'refs': memory.get('refs', {})}

            @staticmethod
            def _context_packet_telemetry_projection(packet):
                return {'provenance_summary': {'memory_ids': []}}

            @staticmethod
            def _render_plain_context(memories, question):
                return '\n'.join(f"- {memory['content']}" for memory in memories)

            @staticmethod
            def _count_ref_coverage(evidence_refs, memories):
                return 1

            @staticmethod
            def llm_call(messages, model='gpt-test', max_tokens=200, retries=3):
                prompts.append(messages[1]['content'])
                return '2'

        answer, memory_count, telemetry = context_packet_canary.answer_question_with_frozen_context(
            FakeModule,
            'How many times has Melanie gone to the beach in 2023?',
            'locomo-conv-26',
            [{'id': 'b1', 'content': 'Melanie went to the beach in May and July.', 'refs': {'session_index': 7}}],
            context_packet_merge=False,
            answer_shape_directive=True,
        )

        self.assertEqual(answer, '2')
        self.assertEqual(memory_count, 1)
        self.assertIn('Answer Shape Directive', prompts[0])
        self.assertLess(prompts[0].index('Answer Shape Directive'), prompts[0].index('Raw retrieved snippets:'))
        self.assertTrue(telemetry['counts']['answer_shape_directive_enabled'])
        self.assertIn('answer_shape_directive_sha256', telemetry)

    def test_answer_shape_directive_category_filter_limits_transform_to_requested_categories(self):
        self.assertTrue(context_packet_canary.should_use_answer_shape_directive('single-hop', True, None))
        self.assertFalse(context_packet_canary.should_use_answer_shape_directive('adversarial', True, {'single-hop'}))
        self.assertTrue(context_packet_canary.should_use_answer_shape_directive('single-hop', True, {'single-hop'}))
        self.assertFalse(context_packet_canary.should_use_answer_shape_directive('single-hop', False, {'single-hop'}))

    def test_gold_object_coverage_telemetry_reports_atoms_sources_and_conflicts(self):
        coverage = context_packet_canary.build_gold_object_coverage_telemetry(
            one_based_index=185,
            ground_truth='She plays clarinet and violin.',
            memories=[
                {'id': 'm1', 'content': 'Melanie said she plays clarinet and violin.', 'refs': {'session_index': 3}},
                {'id': 'm2', 'content': 'Caroline practiced acoustic guitar last week.', 'refs': {'session_index': 4}},
            ],
        )

        self.assertEqual(coverage['expected_atoms'], ['clarinet', 'violin'])
        self.assertEqual(coverage['present_atoms'], ['clarinet', 'violin'])
        self.assertEqual(coverage['missing_atoms'], [])
        self.assertEqual(coverage['conflict_terms_present'], ['acoustic guitar', 'guitar'])
        self.assertEqual(coverage['coverage_class'], 'all_atoms_present_with_conflicts')
        self.assertEqual(coverage['present_atom_source_ids']['clarinet'], ['m1'])
        self.assertEqual(coverage['present_atom_source_ids']['violin'], ['m1'])
        self.assertEqual(coverage['conflict_term_source_ids']['acoustic guitar'], ['m2'])

    def test_answer_question_with_frozen_context_can_add_default_off_gold_object_coverage_telemetry(self):
        class FakeModule:
            ANSWER_MODEL = 'gpt-test'
            CONTEXT_PACKET_TOP_K = 8
            CONTEXT_PACKET_MERGE_APPEND_TOP_K = 0
            USE_CONTEXT_PACKET_MERGE_REF_GATE = False

            @staticmethod
            def mcp_post(tool, payload):
                return {'episodic_evidence': []}

            @staticmethod
            def _append_packet_evidence_to_baseline(base_memories, packet, max_added=None, evidence_refs=None, ref_gate=False):
                return list(base_memories), [], 0, 0, 0

            @staticmethod
            def _memory_telemetry_projection(memory, rank=None):
                return {'rank': rank, 'id': memory.get('id'), 'content': memory.get('content', ''), 'refs': memory.get('refs', {})}

            @staticmethod
            def _context_packet_telemetry_projection(packet):
                return {'provenance_summary': {'memory_ids': []}}

            @staticmethod
            def _render_plain_context(memories, question):
                return '\n'.join(f"- {memory['content']}" for memory in memories)

            @staticmethod
            def _count_ref_coverage(evidence_refs, memories):
                return 1

            @staticmethod
            def llm_call(messages, model='gpt-test', max_tokens=200, retries=3):
                return 'Charlotte\'s Web'

        answer, _, telemetry = context_packet_canary.answer_question_with_frozen_context(
            FakeModule,
            'What books has Melanie read?',
            'locomo-conv-26',
            [{'id': 'm1', 'content': 'Melanie read Charlotte\'s Web.', 'refs': {'session_index': 2}}],
            one_based_index=24,
            ground_truth='Nothing is Impossible and Charlotte\'s Web',
            gold_object_coverage_telemetry=True,
        )

        self.assertEqual(answer, 'Charlotte\'s Web')
        self.assertTrue(telemetry['counts']['gold_object_coverage_telemetry_enabled'])
        coverage = telemetry['gold_object_coverage']
        self.assertEqual(coverage['coverage_class'], 'partial_atoms_present')
        self.assertEqual(coverage['present_atoms'], ["Charlotte's Web"])
        self.assertEqual(coverage['missing_atoms'], ['Nothing is Impossible'])
        self.assertEqual(coverage['present_atom_source_ids']["Charlotte's Web"], ['m1'])

    def test_parse_category_filter_normalizes_comma_separated_categories(self):
        self.assertEqual(
            context_packet_canary.parse_category_filter('single-hop, multi-hop,unanswerable'),
            {'single-hop', 'multi-hop', 'unanswerable'},
        )
        self.assertIsNone(context_packet_canary.parse_category_filter(None))

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
                        'answer_evidence_table_enabled': True,
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
        self.assertEqual(comparison['prompt_context_delta_source_by_row'], ['packet_transform+answer_evidence_table'])

    def test_paired_artifact_validation_reports_subject_guard_prompt_delta(self):
        fixed_rows = [{
            'one_based_index': 1,
            'question': 'Who found the sidewalk?',
            'question_sha256': 'q1',
        }]
        baseline = {
            'condition': {'context_packet': False, 'context_packet_merge': False},
            'details': [{
                'row_identity': fixed_rows[0],
                'question': fixed_rows[0]['question'],
                'score': 0.0,
                'cat': 'adversarial',
                'predicted': 'Caroline found it.',
                'answer_prompt_context_sha256': 'base',
                'frozen_baseline_context_sha256': context_packet_canary.frozen_context_hash([{'id': 'b1', 'content': 'Melanie found it.'}]),
                'recall_telemetry': {
                    'counts': {'context_packet_merge_enabled': False},
                    'final_context': [{'id': 'b1', 'content': 'Melanie found it.'}],
                    'gold_evidence_ref_coverage': {'gold_ref_count': 1, 'final_context_refs_matched': 1},
                },
            }],
        }
        treatment = {
            'condition': {'context_packet': False, 'context_packet_merge': True, 'frozen_context_replay': True},
            'details': [{
                'row_identity': fixed_rows[0],
                'question': fixed_rows[0]['question'],
                'score': 1.0,
                'cat': 'adversarial',
                'predicted': 'Melanie found it.',
                'answer_prompt_context_sha256': 'treat',
                'frozen_baseline_context_sha256': context_packet_canary.frozen_context_hash([{'id': 'b1', 'content': 'Melanie found it.'}]),
                'recall_telemetry': {
                    'counts': {
                        'context_packet_merge_enabled': True,
                        'frozen_context_replay_enabled': True,
                        'packet_episodic_added_count': 0,
                        'answer_subject_guard_enabled': True,
                    },
                    'final_context_before_packet_merge': [{'id': 'b1', 'content': 'Melanie found it.'}],
                    'final_context': [{'id': 'b1', 'content': 'Melanie found it.'}],
                    'context_packet': {'provenance_summary': {'memory_ids': []}},
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

        self.assertEqual(comparison['prompt_context_delta_source_by_row'], ['answer_subject_guard'])

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
