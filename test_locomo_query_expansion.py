#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path('/home/zaddy/src/Memibrium/benchmark_scripts/locomo_bench_v2.py')
spec = importlib.util.spec_from_file_location('locomo_bench_v2', MODULE_PATH)
locomo_bench_v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locomo_bench_v2)


class QueryExpansionTests(unittest.TestCase):
    def setUp(self):
        if hasattr(locomo_bench_v2.expand_query, 'fail_count'):
            delattr(locomo_bench_v2.expand_query, 'fail_count')

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
        ), patch.object(locomo_bench_v2, 'mcp_post', side_effect=fake_mcp_post), patch.object(
            locomo_bench_v2, 'llm_call', return_value='A thing happened.'
        ):
            answer, memory_count = locomo_bench_v2.answer_question('What happened?', 'locomo-1')

        self.assertEqual(answer, 'A thing happened.')
        self.assertEqual(memory_count, 1)
        self.assertEqual(seen_queries, ['What happened?'])

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

    def test_context_rerank_and_append_context_expansion_are_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            locomo_bench_v2.validate_retrieval_modes(
                use_context_rerank=True,
                use_append_context_expansion=True,
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


if __name__ == '__main__':
    unittest.main()
