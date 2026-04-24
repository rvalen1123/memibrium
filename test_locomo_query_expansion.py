#!/usr/bin/env python3
import importlib.util
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

        with patch.object(locomo_bench_v2, 'expand_query', return_value=[
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

    def test_answer_question_uses_neutral_analytical_system_prompt(self):
        seen_messages = []

        def fake_llm_call(messages, model=locomo_bench_v2.ANSWER_MODEL, max_tokens=200, retries=3):
            seen_messages.append(messages)
            return 'They discussed the incident.'

        with patch.object(locomo_bench_v2, 'expand_query', return_value=['What happened after the attack?']), patch.object(
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


if __name__ == '__main__':
    unittest.main()
