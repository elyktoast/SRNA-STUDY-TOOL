"""No-network tests for staged hybrid adapter routing."""
import unittest
from item_ai_hybrid_v2 import make_hybrid_adapter


class HybridRoutingTests(unittest.TestCase):
    def test_routes_each_step_once(self):
        seen = []
        def adapter(name):
            def call(request):
                seen.append(name)
                return {'step': name}
            return call
        hybrid = make_hybrid_adapter(concept_adapter=adapter('gemini'),
                                     draft_adapter=adapter('groq'),
                                     rationale_adapter=adapter('cloudflare'))
        for step in ('concept_card', 'item_draft', 'rationale'):
            self.assertIsInstance(hybrid({'step': step}), dict)
        self.assertEqual(seen, ['gemini', 'groq', 'cloudflare'])

    def test_rejects_unconfigured_or_unknown_step(self):
        with self.assertRaises(ValueError):
            make_hybrid_adapter(concept_adapter=None, draft_adapter=lambda r: r,
                                rationale_adapter=lambda r: r)
        adapter = lambda r: r
        hybrid = make_hybrid_adapter(concept_adapter=adapter,
                                     draft_adapter=adapter, rationale_adapter=adapter)
        with self.assertRaises(ValueError):
            hybrid({'step': 'publish'})


if __name__ == '__main__':
    unittest.main()
