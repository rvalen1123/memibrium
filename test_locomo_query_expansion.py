#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).resolve().parent / 'benchmark_scripts' / 'locomo_bench_v2.py'
spec = importlib.util.spec_from_file_location('locomo_bench_v2', MODULE_PATH)
locomo_bench_v2 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(locomo_bench_v2)


class QueryExpansionTests(unittest.TestCase):
    def setUp(self):
        if hasattr(locomo_bench_v2.expand_query, 'fail_count'):
            delattr(locomo_bench_v2.expand_query, 'fail_count')

    def test_benchmark_chat_config_uses_environment_over_hardcoded_resource(self):
        with patch.dict(os.environ, {
            'AZURE_CHAT_ENDPOINT': 'https://example-foundry.services.ai.azure.com',
            'AZURE_CHAT_KEY': 'example-key',
            'JUDGE_MODEL': 'judge-deployment',
            'ANSWER_MODEL': 'answer-deployment',
        }, clear=True):
            endpoint, key, judge_model, answer_model = locomo_bench_v2.load_chat_config()

        self.assertEqual(endpoint, 'https://example-foundry.services.ai.azure.com/models')
        self.assertEqual(key, 'example-key')
        self.assertEqual(judge_model, 'judge-deployment')
        self.assertEqual(answer_model, 'answer-deployment')

    def test_benchmark_chat_config_reuses_server_style_chat_config(self):
        with patch.dict(os.environ, {
            'AZURE_CHAT_ENDPOINT': 'https://server-foundry.services.ai.azure.com/',
            'AZURE_CHAT_API_KEY': 'server-key',
            'AZURE_CHAT_DEPLOYMENT': 'server-deployment',
        }, clear=True):
            endpoint, key, judge_model, answer_model = locomo_bench_v2.load_chat_config()

        self.assertEqual(endpoint, 'https://server-foundry.services.ai.azure.com/models')
        self.assertEqual(key, 'server-key')
        self.assertEqual(judge_model, 'server-deployment')
        self.assertEqual(answer_model, 'server-deployment')

    def test_mcp_post_raises_after_non_200_or_empty_response_retries(self):
        response = Mock(status_code=503, text='Service unavailable')
        with patch.object(locomo_bench_v2.client, 'post', return_value=response), patch.object(
            locomo_bench_v2.time, 'sleep'
        ):
            with self.assertRaisesRegex(RuntimeError, 'MCP recall failed after 2 attempts.*status=503.*Service unavailable'):
                locomo_bench_v2.mcp_post('recall', {'query': 'x'}, retries=2)

    def test_mcp_post_raises_after_exception_retries(self):
        with patch.object(locomo_bench_v2.client, 'post', side_effect=TimeoutError('network down')), patch.object(
            locomo_bench_v2.time, 'sleep'
        ):
            with self.assertRaisesRegex(RuntimeError, 'MCP retain failed after 2 attempts.*network down'):
                locomo_bench_v2.mcp_post('retain', {'content': 'x'}, retries=2)

    def test_numeric_category_names_match_locomo_protocol(self):
        self.assertEqual(locomo_bench_v2._category_name(1), 'single-hop')
        self.assertEqual(locomo_bench_v2._category_name(2), 'temporal')
        self.assertEqual(locomo_bench_v2._category_name(3), 'multi-hop')
        self.assertEqual(locomo_bench_v2._category_name(4), 'unanswerable')
        self.assertEqual(locomo_bench_v2._category_name(5), 'adversarial')

    def test_skip_adversarial_honors_numeric_category_after_normalization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / 'locomo.json'
            data_path.write_text(json.dumps([
                {
                    'sample_id': 'sample',
                    'conversation': {'speaker_a': 'A', 'speaker_b': 'B'},
                    'qa': [
                        {'category': 5, 'question': 'Adversarial?', 'answer': 'skip me'},
                        {'category': 4, 'question': 'Answerable?', 'answer': 'keep me'},
                    ],
                }
            ]))
            output_path = Path(tmpdir) / 'results.json'
            answered = []

            def fake_answer_question(question, domain):
                answered.append(question)
                return ('keep me', 1)

            with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', False), patch.object(
                locomo_bench_v2, 'USE_CONTEXT_RERANK', False
            ), patch.object(
                locomo_bench_v2, 'USE_APPEND_CONTEXT_EXPANSION', False
            ), patch.object(
                locomo_bench_v2, 'result_output_path', return_value=str(output_path)
            ), patch.object(locomo_bench_v2, 'mcp_get', return_value={'total_memories': 0}), patch.object(
                locomo_bench_v2, 'ingest_conversation', return_value=(1, 'locomo-sample')
            ), patch.object(locomo_bench_v2, 'answer_question', side_effect=fake_answer_question), patch.object(
                locomo_bench_v2, 'judge_answer', return_value=1
            ), patch.object(locomo_bench_v2.time, 'sleep'), patch('builtins.print'):
                locomo_bench_v2.run_benchmark(str(data_path), skip_cats={5}, cleaned=True)

            self.assertEqual(answered, ['Answerable?'])
            payload = json.loads(output_path.read_text())
            self.assertEqual([row['question'] for row in payload['details']], ['Answerable?'])

    def test_judge_answer_uses_configured_judge_model(self):
        calls = []

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            calls.append({'messages': messages, 'model': model, 'max_tokens': max_tokens})
            return '1'

        with patch.object(locomo_bench_v2, 'JUDGE_MODEL', 'fast-judge-model'), patch.object(
            locomo_bench_v2, 'ANSWER_MODEL', 'answer-model'
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            score = locomo_bench_v2.judge_answer('Q?', 'A', 'A')

        self.assertEqual(score, 1)
        self.assertEqual(calls[0]['model'], 'fast-judge-model')
        self.assertEqual(calls[0]['max_tokens'], 5)

    def test_expand_query_includes_original_and_limits_to_three_paraphrases(self):
        with patch.object(
            locomo_bench_v2,
            'llm_call',
            return_value='["entity-focused", "time-focused", "relationship-focused", "extra"]',
        ):
            queries = locomo_bench_v2.expand_query('When did John see Maria?')

        self.assertEqual(
            queries,
            [
                'When did John see Maria?',
                'entity-focused',
                'time-focused',
                'relationship-focused',
            ],
        )
        self.assertEqual(getattr(locomo_bench_v2.expand_query, 'fail_count', 0), 0)

    def test_expand_query_fails_open_and_counts_fallbacks(self):
        with patch.object(locomo_bench_v2, 'llm_call', side_effect=RuntimeError('boom')):
            queries = locomo_bench_v2.expand_query('When did John see Maria?')

        self.assertEqual(queries, ['When did John see Maria?'])
        self.assertEqual(locomo_bench_v2.expand_query.fail_count, 1)

    def test_expand_query_rejects_bare_json_string_and_counts_fallback(self):
        with patch.object(locomo_bench_v2, 'llm_call', return_value='"When did John see Maria?"'):
            queries = locomo_bench_v2.expand_query('When did John see Maria?')

        self.assertEqual(queries, ['When did John see Maria?'])
        self.assertEqual(locomo_bench_v2.expand_query.fail_count, 1)

    def test_expand_query_rejects_dict_non_string_elements_and_empty_lists(self):
        invalid_payloads = [
            '{"queries": ["entity-focused", "time-focused"]}',
            '["entity-focused", {"bad": "shape"}]',
            '[]',
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                if hasattr(locomo_bench_v2.expand_query, 'fail_count'):
                    delattr(locomo_bench_v2.expand_query, 'fail_count')
                with patch.object(locomo_bench_v2, 'llm_call', return_value=payload):
                    queries = locomo_bench_v2.expand_query('When did John see Maria?')

                self.assertEqual(queries, ['When did John see Maria?'])
                self.assertEqual(locomo_bench_v2.expand_query.fail_count, 1)

    def test_answer_question_fuses_multi_query_recall_dedups_and_caps_to_15(self):
        recalls = {
            'When did John see Maria?': {
                'results': [
                    {'id': 'm01', 'content': 'base memory 1'},
                    {'id': 'm02', 'content': 'base memory 2'},
                    {'id': 'm03', 'content': 'base memory 3'},
                    {'id': 'm04', 'content': 'base memory 4'},
                    {'id': 'm05', 'content': 'base memory 5'},
                ]
            },
            'entity-focused': {
                'results': [
                    {'id': 'm03', 'content': 'base memory 3'},
                    {'id': 'm06', 'content': 'entity memory 6'},
                    {'id': 'm07', 'content': 'entity memory 7'},
                    {'id': 'm08', 'content': 'entity memory 8'},
                    {'id': 'm09', 'content': 'entity memory 9'},
                ]
            },
            'time-focused': {
                'results': [
                    {'id': 'm10', 'content': 'time memory 10'},
                    {'id': 'm11', 'content': 'time memory 11'},
                    {'id': 'm12', 'content': 'time memory 12'},
                    {'id': 'm13', 'content': 'time memory 13'},
                    {'id': 'm14', 'content': 'time memory 14'},
                ]
            },
            'relationship-focused': {
                'results': [
                    {'id': 'm15', 'content': 'relationship memory 15'},
                    {'id': 'm16', 'content': 'relationship memory 16'},
                    {'id': 'm17', 'content': 'relationship memory 17'},
                    {'id': 'm18', 'content': 'relationship memory 18'},
                ]
            },
        }
        seen_messages = []

        def fake_mcp_post(tool, payload, retries=3):
            self.assertEqual(tool, 'recall')
            return recalls[payload['query']]

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'July 21, 2022'

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True), patch.object(locomo_bench_v2, 'expand_query', return_value=[
            'When did John see Maria?',
            'entity-focused',
            'time-focused',
            'relationship-focused',
        ], create=True), patch.object(locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post), patch.object(
            locomo_bench_v2, 'llm_call', side_effect=fake_llm_call
        ):
            answer, memory_count = locomo_bench_v2.answer_question('When did John see Maria?', 'locomo-1')

        self.assertEqual(answer, 'July 21, 2022')
        self.assertEqual(memory_count, 15)
        prompt_text = seen_messages[0][1]['content']
        self.assertIn('relationship memory 15', prompt_text)
        self.assertNotIn('relationship memory 16', prompt_text)
        self.assertEqual(prompt_text.count('base memory 3'), 1)

    def test_answer_question_uses_original_query_only_when_expansion_disabled(self):
        seen_queries = []

        def fake_mcp_post(tool, payload, retries=3):
            seen_queries.append(payload['query'])
            return {'results': [{'id': 'm1', 'content': 'base memory'}]}

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', False), patch.object(
            locomo_bench_v2,
            'expand_query',
            return_value=['What happened?', 'alt one', 'alt two'],
        ) as expand_mock, patch.object(locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post), patch.object(
            locomo_bench_v2, 'llm_call', return_value='A thing happened.'
        ):
            answer, memory_count = locomo_bench_v2.answer_question('What happened?', 'locomo-1')

        self.assertEqual(answer, 'A thing happened.')
        self.assertEqual(memory_count, 1)
        self.assertEqual(seen_queries, ['What happened?'])
        expand_mock.assert_not_called()


    def test_answer_question_telemetry_disabled_keeps_recall_payload_and_return_shape(self):
        seen_payloads = []

        def fake_mcp_post(tool, payload, retries=3):
            self.assertEqual(tool, 'recall')
            seen_payloads.append(dict(payload))
            return {'results': [{'id': 'm1', 'content': 'base memory'}]}

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', False), patch.object(
            locomo_bench_v2, 'INCLUDE_RECALL_TELEMETRY', False
        ), patch.object(locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post), patch.object(
            locomo_bench_v2, 'llm_call', return_value='answer'
        ):
            answer, memory_count = locomo_bench_v2.answer_question('What happened?', 'locomo-1')

        self.assertEqual(answer, 'answer')
        self.assertEqual(memory_count, 1)
        self.assertEqual(seen_payloads, [{'query': 'What happened?', 'top_k': locomo_bench_v2.RECALL_TOP_K, 'domain': 'locomo-1'}])

    def test_answer_question_telemetry_enabled_records_expanded_query_and_final_context_metadata(self):
        def fake_mcp_post(tool, payload, retries=3):
            self.assertEqual(tool, 'recall')
            self.assertTrue(payload['include_telemetry'])
            query = payload['query']
            return {
                'results': [
                    {'id': f'{query}-1', 'content': f'{query} memory one', 'refs': {'turn_start': 1}},
                    {'id': 'shared', 'content': 'shared memory', 'refs': {'turn_start': 2}},
                ],
                'telemetry': {'query': query, 'final': {'returned_count': 2}},
            }

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True), patch.object(
            locomo_bench_v2, 'INCLUDE_RECALL_TELEMETRY', True
        ), patch.object(locomo_bench_v2, 'expand_query', return_value=['base', 'expanded']), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', return_value='answer'):
            answer, memory_count, telemetry = locomo_bench_v2.answer_question(
                'base',
                'locomo-1',
                return_telemetry=True,
                evidence_refs=[{'turn_start': 2}],
            )

        self.assertEqual(answer, 'answer')
        self.assertEqual(memory_count, 3)
        self.assertEqual(telemetry['expanded_queries'], ['base', 'expanded'])
        self.assertEqual([entry['result_count'] for entry in telemetry['per_query_recall']], [2, 2])
        self.assertEqual([item['id'] for item in telemetry['final_context']], ['base-1', 'shared', 'expanded-1'])
        self.assertEqual(telemetry['counts']['candidate_memories_before_dedupe'], 4)
        self.assertEqual(telemetry['counts']['base_candidate_count_after_dedupe'], 3)
        self.assertEqual(telemetry['gold_evidence_ref_coverage']['final_context_refs_matched'], 1)

    def test_context_rerank_prefers_query_relevant_memories_when_enabled(self):
        memories = [
            {'id': 'm1', 'content': 'Caroline discussed generic travel plans.'},
            {'id': 'm2', 'content': 'The dentist appointment happened on 12 July 2023.'},
            {'id': 'm3', 'content': 'Unrelated lunch details.'},
        ]

        ranked = locomo_bench_v2.rerank_memories_for_question(
            'When was the dentist appointment?',
            memories,
            top_k=2,
            preserve_prefix_k=0,
        )

        self.assertEqual([m['id'] for m in ranked], ['m2', 'm1'])

    def test_answer_question_uses_reranked_memories_when_enabled(self):
        seen_messages = []
        seen_payloads = []

        def fake_mcp_post(tool, payload, retries=3):
            seen_payloads.append(payload)
            return {
                'results': [
                    {'id': 'm1', 'content': 'Caroline discussed generic travel plans.'},
                    {'id': 'm2', 'content': 'The dentist appointment happened on 12 July 2023.'},
                    {'id': 'm3', 'content': 'Unrelated lunch details.'},
                ]
            }

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return '12 July 2023'

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', False), patch.object(
            locomo_bench_v2, 'USE_CONTEXT_RERANK', True
        ), patch.object(
            locomo_bench_v2,
            'mcp_post',
            side_effect=fake_mcp_post,
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            answer, memory_count = locomo_bench_v2.answer_question('When was the dentist appointment?', 'locomo-1')

        self.assertEqual(answer, '12 July 2023')
        self.assertEqual(memory_count, 3)
        self.assertEqual(seen_payloads[0]['top_k'], locomo_bench_v2.RERANK_RECALL_TOP_K)
        prompt_text = seen_messages[0][1]['content']
        self.assertLess(prompt_text.index('generic travel'), prompt_text.index('dentist appointment'))

    def test_rerank_preserves_original_prefix_before_lexical_fill(self):
        memories = [
            {'id': 'm1', 'content': 'Original top evidence needed for unanswerable or multi-hop context.'},
            {'id': 'm2', 'content': 'Second original evidence also needed for context.'},
            {'id': 'm3', 'content': 'Generic distractor.'},
            {'id': 'm4', 'content': 'The dentist appointment happened on 12 July 2023.'},
        ]

        ranked = locomo_bench_v2.rerank_memories_for_question(
            'When was the dentist appointment?',
            memories,
            top_k=3,
        )

        self.assertEqual([m['id'] for m in ranked], ['m1', 'm2', 'm4'])

    def test_rerank_does_not_duplicate_original_prefix_items_in_fill(self):
        memories = [
            {'id': 'm1', 'content': 'The dentist appointment happened on 12 July 2023.'},
            {'id': 'm2', 'content': 'Second original context.'},
            {'id': 'm3', 'content': 'More dentist appointment evidence.'},
        ]

        ranked = locomo_bench_v2.rerank_memories_for_question(
            'When was the dentist appointment?',
            memories,
            top_k=3,
        )

        self.assertEqual([m['id'] for m in ranked], ['m1', 'm2', 'm3'])

    def test_append_context_preserves_original_top15_and_appends_lexical_candidates(self):
        original = [
            {'id': f'm{i:02d}', 'content': f'original context memory {i:02d}'}
            for i in range(1, 16)
        ]
        candidates = original + [
            {'id': 'm16', 'content': 'generic extra candidate'},
            {'id': 'm17', 'content': 'The dentist appointment was discussed in detail.'},
            {'id': 'm18', 'content': 'Follow-up notes about the dentist appointment.'},
        ]

        expanded = locomo_bench_v2.append_memories_for_question(
            'When was the dentist appointment?',
            original,
            candidates,
            extra_k=2,
        )

        self.assertEqual([m['id'] for m in expanded[:15]], [m['id'] for m in original])
        self.assertEqual([m['id'] for m in expanded[15:]], ['m17', 'm18'])
        self.assertEqual(len({m['id'] for m in expanded}), len(expanded))

    def test_answer_question_append_context_preserves_original_context_then_appends(self):
        seen_messages = []
        seen_payloads = []

        def fake_mcp_post(tool, payload, retries=3):
            self.assertEqual(tool, 'recall')
            seen_payloads.append(payload)
            if payload['query'] == 'base query':
                return {'results': [
                    {
                        'id': f'b{i:02d}',
                        'content': (
                            'dentist appointment extra evidence b16'
                            if i == 16
                            else f'base memory {i:02d}'
                        ),
                        'combined_score': 1.0 if i == 16 else 0.0,
                    }
                    for i in range(1, 21)
                ]}
            return {'results': [
                {
                    'id': f'e{i:02d}',
                    'content': (
                        f'dentist appointment expanded memory {i:02d}'
                        if i <= 2
                        else f'expanded memory {i:02d}'
                    ),
                    'combined_score': 2.0 if i <= 2 else 0.0,
                }
                for i in range(1, 21)
            ]}

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'answer'

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True), patch.object(
            locomo_bench_v2, 'USE_CONTEXT_RERANK', False
        ), patch.object(
            locomo_bench_v2, 'USE_APPEND_CONTEXT_EXPANSION', True
        ), patch.object(
            locomo_bench_v2, 'expand_query', return_value=['base query', 'expanded query']
        ), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            answer, memory_count = locomo_bench_v2.answer_question('When was the dentist appointment?', 'locomo-1')

        self.assertEqual(answer, 'answer')
        self.assertEqual([p['top_k'] for p in seen_payloads], [locomo_bench_v2.APPEND_CONTEXT_RECALL_TOP_K] * 2)
        self.assertEqual(memory_count, locomo_bench_v2.ANSWER_CONTEXT_TOP_K + locomo_bench_v2.APPEND_CONTEXT_EXTRA_K)
        prompt_text = seen_messages[0][1]['content']
        self.assertLess(prompt_text.index('base memory 01'), prompt_text.index('base memory 10'))
        self.assertLess(prompt_text.index('base memory 10'), prompt_text.index('dentist appointment expanded memory 01'))
        self.assertLess(prompt_text.index('dentist appointment expanded memory 02'), prompt_text.index('dentist appointment extra evidence b16'))
        self.assertNotIn('base memory 16\n', prompt_text)

    def test_answer_question_with_expansion_and_rerank_recalls_all_expanded_queries(self):
        seen_queries = []

        def fake_mcp_post(tool, payload, retries=3):
            seen_queries.append(payload['query'])
            offset = len(seen_queries) * 100
            return {
                'results': [
                    {'id': f'm{offset + i}', 'content': f'memory {offset + i}'}
                    for i in range(locomo_bench_v2.RERANK_RECALL_TOP_K)
                ]
            }

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True), patch.object(
            locomo_bench_v2, 'USE_CONTEXT_RERANK', True
        ), patch.object(
            locomo_bench_v2, 'expand_query', return_value=['base query', 'expanded query']
        ), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', return_value='answer'):
            answer, memory_count = locomo_bench_v2.answer_question('base query', 'locomo-1')

        self.assertEqual(answer, 'answer')
        self.assertEqual(seen_queries, ['base query', 'expanded query'])
        self.assertEqual(memory_count, locomo_bench_v2.ANSWER_CONTEXT_TOP_K)

    def test_answer_question_uses_neutral_analytical_system_prompt(self):
        seen_messages = []

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'They discussed the incident.'

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True), patch.object(locomo_bench_v2, 'expand_query', return_value=['What happened after the attack?']), patch.object(
            locomo_bench_v2,
            'mcp_post',
            return_value={'results': [{'id': 'm1', 'content': 'She described the attack in detail.'}]},
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            answer, memory_count = locomo_bench_v2.answer_question('What happened after the attack?', 'locomo-1')

        self.assertEqual(answer, 'They discussed the incident.')
        self.assertEqual(memory_count, 1)
        self.assertEqual(len(seen_messages), 1)
        system_prompt = seen_messages[0][0]['content']
        self.assertIn('extracting factual information from conversation transcripts', system_prompt)
        self.assertIn('academic benchmark on long-term memory evaluation', system_prompt)
        self.assertNotIn('You are answering questions about past conversations', system_prompt)

    def test_query_expansion_is_disabled_by_default(self):
        self.assertFalse(locomo_bench_v2._env_flag('MISSING_FLAG_FOR_TEST', default=False))

    def test_output_path_is_condition_specific_for_normalized_query_expansion(self):
        self.assertEqual(
            locomo_bench_v2.result_output_path(normalize_dates=True, use_query_expansion=True),
            '/tmp/locomo_results_query_expansion.json',
        )

    def test_output_path_is_condition_specific_for_normalized_without_expansion(self):
        self.assertEqual(
            locomo_bench_v2.result_output_path(normalize_dates=True, use_query_expansion=False),
            '/tmp/locomo_results_normalized.json',
        )

    def test_explicit_no_expansion_output_path_does_not_overwrite_normalized_baseline(self):
        self.assertEqual(
            locomo_bench_v2.result_output_path(
                normalize_dates=True,
                use_query_expansion=False,
                no_expansion_arm_b=True,
            ),
            '/tmp/locomo_results_no_expansion.json',
        )
        self.assertNotEqual(
            locomo_bench_v2.result_output_path(
                normalize_dates=True,
                use_query_expansion=False,
                no_expansion_arm_b=True,
            ),
            locomo_bench_v2.result_output_path(normalize_dates=True, use_query_expansion=False),
        )

    def test_no_expansion_arm_b_path_implies_query_expansion_disabled(self):
        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True):
            self.assertEqual(
                locomo_bench_v2.result_output_path(normalize_dates=True, no_expansion_arm_b=True),
                '/tmp/locomo_results_no_expansion.json',
            )
            payload = locomo_bench_v2.build_results_payload(
                all_scores=[1],
                cat_scores={'single-hop': [1]},
                query_times=[0.1],
                results_log=[],
                normalize_dates=True,
                no_expansion_arm_b=True,
            )
            self.assertFalse(payload['condition']['query_expansion'])
            self.assertTrue(payload['condition']['no_expansion_arm_b'])

    def test_cli_exposes_no_expansion_arm_b_flag(self):
        proc = subprocess.run(
            [sys.executable, str(MODULE_PATH), '--help'],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn('--no-expansion-arm-b', proc.stdout)

    def test_cli_exposes_legacy_context_assembly_flag(self):
        proc = subprocess.run(
            [sys.executable, str(MODULE_PATH), '--help'],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn('--legacy-context-assembly', proc.stdout)

    def test_legacy_context_assembly_stops_after_context_budget_and_skips_later_expansions(self):
        seen_queries = []
        seen_messages = []

        def memories(prefix, count):
            return [
                {'id': f'{prefix}{i:02d}', 'content': f'{prefix} memory {i:02d}'}
                for i in range(1, count + 1)
            ]

        recalls = {
            'base query': {'results': memories('base', locomo_bench_v2.RECALL_TOP_K)},
            'expanded one': {'results': memories('exp1', locomo_bench_v2.RECALL_TOP_K)},
            'expanded two': {'results': memories('exp2', locomo_bench_v2.RECALL_TOP_K)},
        }

        def fake_mcp_post(tool, payload, retries=3):
            self.assertEqual(tool, 'recall')
            seen_queries.append(payload['query'])
            return recalls[payload['query']]

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'answer'

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True), patch.object(
            locomo_bench_v2, 'USE_CONTEXT_RERANK', False
        ), patch.object(
            locomo_bench_v2, 'USE_APPEND_CONTEXT_EXPANSION', False
        ), patch.object(
            locomo_bench_v2, 'USE_GATED_APPEND_CONTEXT_EXPANSION', False
        ), patch.object(
            locomo_bench_v2, 'USE_LEGACY_CONTEXT_ASSEMBLY', True
        ), patch.object(
            locomo_bench_v2, 'expand_query', return_value=['base query', 'expanded one', 'expanded two']
        ), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            answer, memory_count = locomo_bench_v2.answer_question('base query', 'locomo-1')

        self.assertEqual(answer, 'answer')
        self.assertEqual(seen_queries, ['base query', 'expanded one'])
        self.assertEqual(memory_count, locomo_bench_v2.ANSWER_CONTEXT_TOP_K)
        prompt_text = seen_messages[0][1]['content']
        self.assertIn('exp1 memory 05', prompt_text)
        self.assertNotIn('exp2 memory 01', prompt_text)

    def test_output_path_and_payload_are_condition_specific_for_legacy_context_assembly(self):
        self.assertEqual(
            locomo_bench_v2.result_output_path(
                normalize_dates=True,
                use_query_expansion=True,
                use_legacy_context_assembly=True,
            ),
            '/tmp/locomo_results_query_expansion_legacy_context.json',
        )

        payload = locomo_bench_v2.build_results_payload(
            all_scores=[1],
            cat_scores={'temporal': [1]},
            query_times=[1.0],
            results_log=[],
            normalize_dates=True,
            use_query_expansion=True,
            use_legacy_context_assembly=True,
            cleaned=True,
        )
        self.assertTrue(payload['condition']['legacy_context_assembly'])
        self.assertTrue(payload['condition']['query_expansion'])
        self.assertFalse(payload['condition']['context_rerank'])
        self.assertTrue(payload['condition']['cleaned'])

    def test_legacy_context_assembly_is_mutually_exclusive_with_new_context_modes(self):
        for kwargs in [
            {'use_context_rerank': True},
            {'use_append_context_expansion': True},
            {'use_gated_append_context_expansion': True},
        ]:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    locomo_bench_v2.validate_retrieval_modes(
                        use_legacy_context_assembly=True,
                        **kwargs,
                    )

    def test_run_benchmark_explicit_legacy_context_assembly_sets_runtime_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / 'locomo.json'
            output_path = Path(tmpdir) / 'results.json'
            data_path.write_text(json.dumps([
                {
                    'sample_id': 'sample',
                    'conversation': {'speaker_a': 'A', 'speaker_b': 'B'},
                    'qa': [{'category': 'single-hop', 'question': 'What happened?', 'answer': 'A thing happened.'}],
                }
            ]))
            seen_legacy_values = []

            def fake_answer_question(question, domain):
                seen_legacy_values.append(locomo_bench_v2.USE_LEGACY_CONTEXT_ASSEMBLY)
                return ('A thing happened.', 1)

            with patch.object(locomo_bench_v2, 'USE_LEGACY_CONTEXT_ASSEMBLY', False), patch.object(
                locomo_bench_v2, 'result_output_path', return_value=str(output_path)
            ), patch.object(locomo_bench_v2, 'mcp_get', return_value={'total_memories': 0}), patch.object(
                locomo_bench_v2, 'ingest_conversation', return_value=(1, 'locomo-sample')
            ), patch.object(
                locomo_bench_v2, 'answer_question', side_effect=fake_answer_question
            ), patch.object(locomo_bench_v2, 'judge_answer', return_value=1), patch.object(
                locomo_bench_v2.time, 'sleep'
            ), patch('builtins.print'):
                locomo_bench_v2.run_benchmark(
                    str(data_path),
                    normalize_dates=True,
                    cleaned=True,
                    use_legacy_context_assembly=True,
                )

            self.assertEqual(seen_legacy_values, [True])
            payload = json.loads(output_path.read_text())
            self.assertTrue(payload['condition']['legacy_context_assembly'])

    def test_no_expansion_arm_b_run_bypasses_expand_query_even_if_global_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / 'locomo.json'
            output_path = Path(tmpdir) / 'results.json'
            data_path.write_text(json.dumps([
                {
                    'sample_id': 'sample',
                    'conversation': {'speaker_a': 'A', 'speaker_b': 'B'},
                    'qa': [{'category': 'single-hop', 'question': 'What happened?', 'answer': 'A thing happened.'}],
                }
            ]))
            seen_queries = []

            def fake_mcp_post(tool, payload, retries=3):
                self.assertEqual(tool, 'recall')
                seen_queries.append(payload['query'])
                return {'results': [{'id': 'm1', 'content': 'base memory'}]}

            with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True), patch.object(
                locomo_bench_v2, 'result_output_path', return_value=str(output_path)
            ), patch.object(locomo_bench_v2, 'mcp_get', return_value={'total_memories': 0}), patch.object(
                locomo_bench_v2, 'ingest_conversation', return_value=(1, 'locomo-sample')
            ), patch.object(locomo_bench_v2, 'expand_query', return_value=['What happened?', 'expanded']) as expand_mock, patch.object(
                locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
            ), patch.object(locomo_bench_v2, 'llm_call', return_value='A thing happened.'), patch.object(
                locomo_bench_v2, 'judge_answer', return_value=1
            ), patch.object(locomo_bench_v2.time, 'sleep'), patch('builtins.print'):
                locomo_bench_v2.run_benchmark(str(data_path), normalize_dates=True, cleaned=True, no_expansion_arm_b=True)

            expand_mock.assert_not_called()
            self.assertEqual(seen_queries, ['What happened?'])
            payload = json.loads(output_path.read_text())
            self.assertFalse(payload['condition']['query_expansion'])
            self.assertTrue(payload['condition']['no_expansion_arm_b'])

    def test_max_questions_caps_evaluated_questions_for_smoke_tests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / 'locomo.json'
            output_path = Path(tmpdir) / 'results.json'
            data_path.write_text(json.dumps([
                {
                    'sample_id': 'sample',
                    'conversation': {'speaker_a': 'A', 'speaker_b': 'B'},
                    'qa': [
                        {'category': 'single-hop', 'question': 'Q1?', 'answer': 'A1'},
                        {'category': 'temporal', 'question': 'Q2?', 'answer': 'A2'},
                        {'category': 'multi-hop', 'question': 'Q3?', 'answer': 'A3'},
                    ],
                }
            ]))
            answered = []

            def fake_answer_question(question, domain):
                answered.append(question)
                return (f'answer for {question}', 1)

            with patch.object(locomo_bench_v2, 'result_output_path', return_value=str(output_path)), patch.object(
                locomo_bench_v2, 'mcp_get', return_value={'total_memories': 0}
            ), patch.object(locomo_bench_v2, 'ingest_conversation', return_value=(1, 'locomo-sample')), patch.object(
                locomo_bench_v2, 'answer_question', side_effect=fake_answer_question
            ), patch.object(locomo_bench_v2, 'judge_answer', return_value=1), patch.object(
                locomo_bench_v2.time, 'sleep'
            ), patch('builtins.print'):
                locomo_bench_v2.run_benchmark(str(data_path), max_questions=2, cleaned=True)

            self.assertEqual(answered, ['Q1?', 'Q2?'])
            payload = json.loads(output_path.read_text())
            self.assertEqual(payload['total_questions'], 2)
            self.assertEqual([row['question'] for row in payload['details']], ['Q1?', 'Q2?'])

    def test_cli_exposes_max_questions_for_smoke_tests(self):
        proc = subprocess.run(
            [sys.executable, str(MODULE_PATH), '--help'],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn('--max-questions', proc.stdout)

    def test_cli_rejects_non_positive_max_questions(self):
        proc = subprocess.run(
            [sys.executable, str(MODULE_PATH), '--max-questions', '0'],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('--max-questions must be a positive integer', proc.stderr)

    def test_run_benchmark_passes_explicit_query_expansion_to_all_output_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / 'locomo.json'
            output_path = Path(tmpdir) / 'results.json'
            data_path.write_text(json.dumps([
                {
                    'sample_id': 'prior',
                    'conversation': {'speaker_a': 'A', 'speaker_b': 'B'},
                    'qa': [],
                },
                {
                    'sample_id': 'new',
                    'conversation': {'speaker_a': 'A', 'speaker_b': 'B'},
                    'qa': [{'category': 'single-hop', 'question': 'What happened?', 'answer': 'A thing happened.'}],
                },
            ]))
            output_path.write_text(json.dumps({
                'details': [{'score': 1, 'cat': 'single-hop', 'query_time_ms': 100}],
            }))
            path_conditions = []

            def fake_result_output_path(*args, **kwargs):
                if 'normalize_dates' in kwargs:
                    normalize_dates = kwargs['normalize_dates']
                elif args:
                    normalize_dates = args[0]
                else:
                    normalize_dates = False

                if 'use_query_expansion' in kwargs:
                    use_query_expansion = kwargs['use_query_expansion']
                elif len(args) >= 2:
                    use_query_expansion = args[1]
                else:
                    use_query_expansion = None

                if 'use_context_rerank' in kwargs:
                    use_context_rerank = kwargs['use_context_rerank']
                elif len(args) >= 3:
                    use_context_rerank = args[2]
                else:
                    use_context_rerank = None

                path_conditions.append((normalize_dates, use_query_expansion, use_context_rerank))
                locomo_bench_v2.USE_QUERY_EXPANSION = True
                locomo_bench_v2.USE_CONTEXT_RERANK = True
                return str(output_path)

            with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', False), patch.object(
                locomo_bench_v2, 'USE_CONTEXT_RERANK', False
            ), patch.object(
                locomo_bench_v2, 'result_output_path', side_effect=fake_result_output_path
            ), patch.object(locomo_bench_v2, 'mcp_get', return_value={'total_memories': 0}), patch.object(
                locomo_bench_v2, 'ingest_conversation', return_value=(1, 'locomo-new')
            ), patch.object(locomo_bench_v2, 'answer_question', return_value=('A thing happened.', 1)), patch.object(
                locomo_bench_v2, 'judge_answer', return_value=1
            ), patch.object(locomo_bench_v2.time, 'sleep'), patch('builtins.print'):
                locomo_bench_v2.run_benchmark(str(data_path), start_conv=1, normalize_dates=True, cleaned=True)

            self.assertEqual(path_conditions, [(True, False, False), (True, False, False), (True, False, False)])
            payload = json.loads(output_path.read_text())
            self.assertFalse(payload['condition']['query_expansion'])
            self.assertFalse(payload['condition']['context_rerank'])
            self.assertTrue(payload['condition']['cleaned'])

    def test_output_path_and_payload_are_condition_specific_for_rerank(self):
        self.assertEqual(
            locomo_bench_v2.result_output_path(
                normalize_dates=True,
                use_query_expansion=True,
                use_context_rerank=True,
            ),
            '/tmp/locomo_results_query_expansion_reranked.json',
        )

        payload = locomo_bench_v2.build_results_payload(
            all_scores=[1],
            cat_scores={'temporal': [1]},
            query_times=[1.0],
            results_log=[],
            normalize_dates=True,
            use_query_expansion=True,
            use_context_rerank=True,
            cleaned=True,
        )
        self.assertTrue(payload['condition']['context_rerank'])
        self.assertTrue(payload['condition']['cleaned'])

    def test_append_context_preserves_non_append_query_expansion_prefix(self):
        recalls = {
            'base query': {'results': [
                {'id': f'b{i:02d}', 'content': f'base memory {i:02d}'}
                for i in range(1, 21)
            ]},
            'expanded query': {'results': [
                {'id': f'e{i:02d}', 'content': f'dentist appointment expanded memory {i:02d}', 'combined_score': 2.0}
                for i in range(1, 21)
            ]},
        }
        seen_messages = []

        def fake_mcp_post(tool, payload, retries=3):
            self.assertEqual(tool, 'recall')
            return recalls[payload['query']]

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'answer'

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True), patch.object(
            locomo_bench_v2, 'USE_CONTEXT_RERANK', False
        ), patch.object(
            locomo_bench_v2, 'USE_APPEND_CONTEXT_EXPANSION', False
        ), patch.object(
            locomo_bench_v2, 'expand_query', return_value=['base query', 'expanded query']
        ), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            locomo_bench_v2.answer_question('When was the dentist appointment?', 'locomo-1')
        non_append_prompt = seen_messages[-1][1]['content']

        seen_messages.clear()
        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', True), patch.object(
            locomo_bench_v2, 'USE_CONTEXT_RERANK', False
        ), patch.object(
            locomo_bench_v2, 'USE_APPEND_CONTEXT_EXPANSION', True
        ), patch.object(
            locomo_bench_v2, 'expand_query', return_value=['base query', 'expanded query']
        ), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            answer, memory_count = locomo_bench_v2.answer_question('When was the dentist appointment?', 'locomo-1')
        append_prompt = seen_messages[-1][1]['content']

        non_append_lines = [line for line in non_append_prompt.splitlines() if line.startswith('- ')]
        append_lines = [line for line in append_prompt.splitlines() if line.startswith('- ')]
        self.assertEqual(answer, 'answer')
        self.assertEqual(append_lines[:locomo_bench_v2.ANSWER_CONTEXT_TOP_K], non_append_lines)
        self.assertEqual(memory_count, locomo_bench_v2.ANSWER_CONTEXT_TOP_K + locomo_bench_v2.APPEND_CONTEXT_EXTRA_K)

    def test_append_context_deduplicates_no_id_memories_by_content(self):
        original = [{'content': 'original context memory'}]
        candidates = original + [
            {'content': 'dentist appointment duplicate evidence'},
            {'content': 'dentist appointment duplicate evidence'},
            {'content': 'dentist appointment unique evidence'},
        ]

        expanded = locomo_bench_v2.append_memories_for_question(
            'When was the dentist appointment?',
            original,
            candidates,
            extra_k=3,
        )

        contents = [m['content'] for m in expanded]
        self.assertEqual(contents.count('dentist appointment duplicate evidence'), 1)
        self.assertEqual(contents.count('dentist appointment unique evidence'), 1)

    def test_append_context_without_query_expansion_preserves_base_recall_prefix_then_appends(self):
        seen_messages = []
        seen_payloads = []

        def fake_mcp_post(tool, payload, retries=3):
            self.assertEqual(tool, 'recall')
            seen_payloads.append(payload)
            return {'results': [
                {
                    'id': f'm{i:02d}',
                    'content': (
                        f'dentist appointment extra memory {i:02d}'
                        if i > locomo_bench_v2.RECALL_TOP_K
                        else f'base memory {i:02d}'
                    ),
                    'combined_score': 1.0 if i > locomo_bench_v2.RECALL_TOP_K else 0.0,
                }
                for i in range(1, locomo_bench_v2.APPEND_CONTEXT_RECALL_TOP_K + 1)
            ]}

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'answer'

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', False), patch.object(
            locomo_bench_v2, 'USE_CONTEXT_RERANK', False
        ), patch.object(
            locomo_bench_v2, 'USE_APPEND_CONTEXT_EXPANSION', True
        ), patch.object(
            locomo_bench_v2, 'expand_query', return_value=['base query', 'expanded query']
        ), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            answer, memory_count = locomo_bench_v2.answer_question('When was the dentist appointment?', 'locomo-1')

        self.assertEqual(answer, 'answer')
        self.assertEqual([p['query'] for p in seen_payloads], ['When was the dentist appointment?'])
        self.assertEqual(seen_payloads[0]['top_k'], locomo_bench_v2.APPEND_CONTEXT_RECALL_TOP_K)
        self.assertEqual(memory_count, locomo_bench_v2.RECALL_TOP_K + locomo_bench_v2.APPEND_CONTEXT_EXTRA_K)
        prompt_lines = [line for line in seen_messages[0][1]['content'].splitlines() if line.startswith('- ')]
        self.assertEqual(
            prompt_lines[:locomo_bench_v2.RECALL_TOP_K],
            [f'- base memory {i:02d}' for i in range(1, locomo_bench_v2.RECALL_TOP_K + 1)],
        )
        self.assertTrue(all('dentist appointment extra memory' in line for line in prompt_lines[locomo_bench_v2.RECALL_TOP_K:]))

    def test_context_packet_mode_calls_context_packet_and_uses_packet_evidence(self):
        calls = []
        seen_messages = []

        def fake_mcp_post(tool, payload, retries=3):
            calls.append((tool, payload))
            self.assertEqual(tool, 'context_packet')
            self.assertEqual(payload['query'], 'What does Ricky value?')
            self.assertEqual(payload['domain'], 'locomo-1')
            self.assertEqual(payload['top_k'], locomo_bench_v2.CONTEXT_PACKET_TOP_K)
            return {
                'schema': 'memibrium.context_packet.v1',
                'episodic_evidence': [
                    {'memory_id': 'mem_ctx_1', 'content': 'Ricky repeatedly values defensible preregistration.'},
                    {'memory_id': 'mem_ctx_1', 'content': 'Ricky repeatedly values defensible preregistration.'},
                    {'id': 'mem_ctx_2', 'content': 'Ricky wants source-backed benchmark changes.'},
                ],
                'self_model_observations': [
                    {'observation_id': 'obs_ctx_1', 'claim_text': 'Ricky values evidence before features.'},
                ],
                'decision_traces': [
                    {'trace_id': 'trace_ctx_1', 'answer': 'Use context packets only behind a default-off flag.'},
                ],
                'answer_guidance': ['Use source-backed evidence first.'],
                'provenance_summary': {
                    'memory_ids': ['mem_ctx_1'],
                    'self_model_observation_ids': ['obs_ctx_1'],
                },
            }

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'defensible preregistration'

        with patch.object(locomo_bench_v2, 'USE_CONTEXT_PACKET', True), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            answer, memory_count, telemetry = locomo_bench_v2.answer_question(
                'What does Ricky value?',
                'locomo-1',
                return_telemetry=True,
            )

        self.assertEqual(answer, 'defensible preregistration')
        self.assertEqual(memory_count, 2)
        self.assertEqual(calls[0][0], 'context_packet')
        prompt_text = seen_messages[0][1]['content']
        self.assertEqual(prompt_text.count('Ricky repeatedly values defensible preregistration.'), 1)
        self.assertIn('[mem_ctx_1] Ricky repeatedly values defensible preregistration.', prompt_text)
        self.assertIn('[mem_ctx_2] Ricky wants source-backed benchmark changes.', prompt_text)
        self.assertIn('Context Packet (self-model observations):', prompt_text)
        self.assertIn('Ricky values evidence before features.', prompt_text)
        self.assertIn('Context Packet (decision traces):', prompt_text)
        self.assertIn('Use context packets only behind a default-off flag.', prompt_text)
        self.assertEqual(telemetry['counts']['context_packet_enabled'], True)
        self.assertEqual([item['id'] for item in telemetry['final_context']], ['mem_ctx_1', 'mem_ctx_2'])
        self.assertEqual(telemetry['context_packet']['schema'], 'memibrium.context_packet.v1')
        self.assertEqual(telemetry['context_packet']['episodic_evidence_count'], 2)
        self.assertEqual(telemetry['context_packet']['deduped_episodic_evidence_count'], 1)
        self.assertEqual(telemetry['context_packet']['provenance_summary']['memory_ids'], ['mem_ctx_1'])

    def test_context_packet_condition_is_default_off_and_condition_specific(self):
        self.assertFalse(locomo_bench_v2.USE_CONTEXT_PACKET)
        self.assertEqual(
            locomo_bench_v2.result_output_path(
                normalize_dates=True,
                use_query_expansion=True,
                use_context_packet=True,
            ),
            '/tmp/locomo_results_query_expansion_context_packet.json',
        )

        payload = locomo_bench_v2.build_results_payload(
            all_scores=[1],
            cat_scores={'single-hop': [1]},
            query_times=[1.0],
            results_log=[],
            normalize_dates=True,
            use_query_expansion=True,
            use_context_packet=True,
        )
        self.assertTrue(payload['condition']['context_packet'])

    def test_context_packet_mode_rejects_other_context_modes(self):
        with self.assertRaises(ValueError):
            locomo_bench_v2.validate_retrieval_modes(
                use_context_packet=True,
                use_context_rerank=True,
            )
        with self.assertRaises(ValueError):
            locomo_bench_v2.validate_retrieval_modes(
                use_context_packet=True,
                use_full_domain_context=True,
            )

    def test_gated_append_skips_extras_when_base_context_is_strong(self):
        seen_messages = []

        def fake_mcp_post(tool, payload, retries=3):
            self.assertEqual(tool, 'recall')
            return {'results': [
                {
                    'id': f'm{i:02d}',
                    'content': (
                        f'dentist appointment strong base memory {i:02d}'
                        if i <= 2
                        else f'base memory {i:02d}'
                    ),
                    'combined_score': 0.9 if i <= 2 else 0.1,
                }
                for i in range(1, locomo_bench_v2.APPEND_CONTEXT_RECALL_TOP_K + 1)
            ]}

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'answer'

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', False), patch.object(
            locomo_bench_v2, 'USE_CONTEXT_RERANK', False
        ), patch.object(
            locomo_bench_v2, 'USE_APPEND_CONTEXT_EXPANSION', False
        ), patch.object(
            locomo_bench_v2, 'USE_GATED_APPEND_CONTEXT_EXPANSION', True
        ), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            answer, memory_count = locomo_bench_v2.answer_question('When was the dentist appointment?', 'locomo-1')

        self.assertEqual(answer, 'answer')
        self.assertEqual(memory_count, locomo_bench_v2.RECALL_TOP_K)
        prompt_text = seen_messages[0][1]['content']
        self.assertNotIn('base memory 11', prompt_text)

    def test_gated_append_requires_lexical_overlap_for_extras_when_base_is_weak(self):
        seen_messages = []

        def fake_mcp_post(tool, payload, retries=3):
            self.assertEqual(tool, 'recall')
            return {'results': [
                *[
                    {'id': f'b{i:02d}', 'content': f'weak base memory {i:02d}', 'combined_score': 0.1}
                    for i in range(1, locomo_bench_v2.RECALL_TOP_K + 1)
                ],
                {'id': 'e01', 'content': 'The dentist appointment was discussed in detail.', 'combined_score': 0.0},
                {'id': 'e02', 'content': 'generic extra candidate with high retriever score only', 'combined_score': 0.99},
            ]}

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'answer'

        with patch.object(locomo_bench_v2, 'USE_QUERY_EXPANSION', False), patch.object(
            locomo_bench_v2, 'USE_CONTEXT_RERANK', False
        ), patch.object(
            locomo_bench_v2, 'USE_APPEND_CONTEXT_EXPANSION', False
        ), patch.object(
            locomo_bench_v2, 'USE_GATED_APPEND_CONTEXT_EXPANSION', True
        ), patch.object(
            locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post
        ), patch.object(locomo_bench_v2, 'llm_call', side_effect=fake_llm_call):
            answer, memory_count = locomo_bench_v2.answer_question('When was the dentist appointment?', 'locomo-1')

        self.assertEqual(answer, 'answer')
        self.assertEqual(memory_count, locomo_bench_v2.RECALL_TOP_K + 1)
        prompt_text = seen_messages[0][1]['content']
        self.assertIn('The dentist appointment was discussed in detail.', prompt_text)
        self.assertNotIn('generic extra candidate with high retriever score only', prompt_text)

    def test_output_path_and_payload_are_condition_specific_for_gated_append_context_expansion(self):
        self.assertEqual(
            locomo_bench_v2.result_output_path(
                normalize_dates=True,
                use_query_expansion=True,
                use_gated_append_context_expansion=True,
            ),
            '/tmp/locomo_results_query_expansion_gated_appended.json',
        )

        payload = locomo_bench_v2.build_results_payload(
            all_scores=[1],
            cat_scores={'temporal': [1]},
            query_times=[1.0],
            results_log=[],
            normalize_dates=True,
            use_query_expansion=True,
            use_gated_append_context_expansion=True,
            cleaned=True,
        )
        self.assertTrue(payload['condition']['append_context_expansion'])
        self.assertTrue(payload['condition']['gated_append_context_expansion'])
        self.assertFalse(payload['condition']['context_rerank'])
        self.assertTrue(payload['condition']['cleaned'])

    def test_context_rerank_and_append_context_expansion_are_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            locomo_bench_v2.validate_retrieval_modes(
                use_context_rerank=True,
                use_append_context_expansion=True,
            )
        with self.assertRaises(ValueError):
            locomo_bench_v2.validate_retrieval_modes(
                use_context_rerank=True,
                use_gated_append_context_expansion=True,
            )

    def test_result_suffix_rejects_combined_rerank_and_append_context_expansion(self):
        with self.assertRaises(ValueError):
            locomo_bench_v2.result_suffix(
                normalize_dates=True,
                use_query_expansion=True,
                use_context_rerank=True,
                use_append_context_expansion=True,
            )

    def test_result_output_path_rejects_combined_rerank_and_append_context_expansion(self):
        with self.assertRaises(ValueError):
            locomo_bench_v2.result_output_path(
                normalize_dates=True,
                use_query_expansion=True,
                use_context_rerank=True,
                use_append_context_expansion=True,
            )

    def test_output_path_and_payload_are_condition_specific_for_append_context_expansion(self):
        self.assertEqual(
            locomo_bench_v2.result_output_path(
                normalize_dates=True,
                use_query_expansion=True,
                use_append_context_expansion=True,
            ),
            '/tmp/locomo_results_query_expansion_appended.json',
        )

        payload = locomo_bench_v2.build_results_payload(
            all_scores=[1],
            cat_scores={'temporal': [1]},
            query_times=[1.0],
            results_log=[],
            normalize_dates=True,
            use_query_expansion=True,
            use_append_context_expansion=True,
            cleaned=True,
        )
        self.assertTrue(payload['condition']['append_context_expansion'])
        self.assertFalse(payload['condition']['context_rerank'])
        self.assertTrue(payload['condition']['cleaned'])

    def test_results_payload_includes_condition_and_protocol_scores(self):
        payload = locomo_bench_v2.build_results_payload(
            all_scores=[1, 0, 1, 0],
            cat_scores={
                'temporal': [1, 0],
                '5': [0],
                'single-hop': [1],
            },
            query_times=[1.0, 2.0],
            results_log=[],
            normalize_dates=True,
            use_query_expansion=True,
            expand_fallback_count=1,
            expand_fallback_rate=0.25,
            use_context_rerank=True,
        )

        self.assertEqual(payload['condition']['normalize_dates'], True)
        self.assertEqual(payload['condition']['query_expansion'], True)
        self.assertEqual(payload['condition']['context_rerank'], True)
        self.assertEqual(payload['full_5cat_overall'], 50.0)
        self.assertEqual(payload['protocol_4cat_overall'], 66.67)
        self.assertEqual(payload['expand_query_fallback_count'], 1)


class ScriptReviewRegressionTests(unittest.TestCase):
    def test_archive_conv26_uses_query_expansion_source_for_exp_case(self):
        script = (Path(__file__).resolve().parent / 'scripts' / 'archive_conv26_ab_results.sh').read_text()
        self.assertRegex(script, r"exp\)\s*src=/tmp/locomo_results_query_expansion\.json\s+dst=/tmp/locomo_results_conv26_exp\.json")
        self.assertRegex(script, r"noexp\)\s*src=/tmp/locomo_results_normalized\.json\s+dst=/tmp/locomo_results_conv26_noexp\.json")
        self.assertRegex(script, r"arm-b\)\s*src=/tmp/locomo_results_no_expansion\.json\s+dst=/tmp/locomo_results_conv26_no_expansion\.json")

    def test_audit_retrieve_candidates_dedupes_idless_memories_with_benchmark_key(self):
        audit_path = Path(__file__).resolve().parent / 'scripts' / 'audit_locomo_rerank_harms.py'
        spec = importlib.util.spec_from_file_location('audit_locomo_rerank_harms_test', audit_path)
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        class BenchStub:
            def expand_query(self, question):
                return [question, f'{question} expanded']

            def _memory_dedupe_key(self, memory):
                return locomo_bench_v2._memory_dedupe_key(memory)

        duplicate_without_id = {'content': 'same memory content', 'refs': {'turn': 1}, 'created_at': '2026-04-26'}
        recall_payloads = [
            {'results': [duplicate_without_id]},
            {'results': [dict(duplicate_without_id)]},
        ]
        with patch.object(audit, 'mcp_post', side_effect=recall_payloads):
            _queries, candidates, _stats = audit.retrieve_candidates('question', 'locomo-conv-26', BenchStub())

        self.assertEqual(len(candidates), 1)

    def test_clear_locomo_domains_cleans_entity_graph_state(self):
        script = (Path(__file__).resolve().parent / 'scripts' / 'clear_locomo_domains.sh').read_text()
        self.assertIn('UPDATE entities', script)
        self.assertIn('memory_ids', script)
        self.assertIn('jsonb_array_elements_text', script)
        self.assertIn('DELETE FROM entities', script)
        self.assertIn('DELETE FROM entity_relationships', script)

    def test_server_related_memories_uses_union_all_for_ruvector_rows(self):
        server = (Path(__file__).resolve().parent / 'server.py').read_text()
        start = server.index('async def get_related_memories')
        end = server.index('async def get_prefetch_candidates')
        method = server[start:end]
        self.assertIn('UNION ALL', method)
        self.assertNotIn('\n                UNION\n', method)

    def test_server_has_eval_toggles_for_expensive_background_ingest_tasks(self):
        server = (Path(__file__).resolve().parent / 'server.py').read_text()
        self.assertIn('ENABLE_BACKGROUND_SCORING', server)
        self.assertIn('ENABLE_CONTRADICTION_DETECTION', server)
        self.assertIn('ENABLE_HIERARCHY_PROCESSING', server)
        self.assertIn('if not ENABLE_BACKGROUND_SCORING:', server)
        self.assertIn('if ENABLE_BACKGROUND_SCORING:', server)
        self.assertIn('if ENABLE_CONTRADICTION_DETECTION and memory_type == "semantic":', server)
        self.assertIn('if ENABLE_HIERARCHY_PROCESSING and hierarchy_manager:', server)

    def test_compose_passes_background_ingest_toggles_to_server(self):
        compose = (Path(__file__).resolve().parent / 'docker-compose.ruvector.yml').read_text()
        self.assertIn('ENABLE_BACKGROUND_SCORING: ${ENABLE_BACKGROUND_SCORING:-true}', compose)
        self.assertIn('ENABLE_CONTRADICTION_DETECTION: ${ENABLE_CONTRADICTION_DETECTION:-true}', compose)
        self.assertIn('ENABLE_HIERARCHY_PROCESSING: ${ENABLE_HIERARCHY_PROCESSING:-true}', compose)

    def test_audit_writes_contaminated_report_before_raising(self):
        script = (Path(__file__).resolve().parent / 'scripts' / 'audit_locomo_rerank_harms.py').read_text()
        self.assertIn('"contaminated": expand_fallback_count > 0', script)
        self.assertLess(script.index('json_path.write_text'), script.rindex('raise RuntimeError'))


if __name__ == '__main__':
    unittest.main()
