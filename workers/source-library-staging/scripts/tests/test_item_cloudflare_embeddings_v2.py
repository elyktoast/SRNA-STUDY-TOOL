import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from item_cloudflare_embeddings_v2 import MODEL, make_embed_many

VECTOR=[1.0]+[0.0]*1023
class CloudflareEmbeddingTests(unittest.TestCase):
    def test_opt_in_is_required_before_transport_construction(self):
        with self.assertRaises(ValueError):
            make_embed_many(enabled=False,transport=lambda **kw:self.fail('must not call'))

    def test_batch_uses_only_fixed_model_and_preserves_input_order(self):
        seen=[]
        def transport(**kw):
            seen.append(kw)
            return {'model':MODEL,'shape':[2,1024],'data':[VECTOR,VECTOR]}
        embed=make_embed_many(enabled=True,transport=transport)
        self.assertEqual(embed(['First synthetic stem','Second synthetic stem']),[VECTOR,VECTOR])
        self.assertEqual(seen[0]['body'],{'task':'semantic_embeddings','model':MODEL,'text':['First synthetic stem','Second synthetic stem']})
        self.assertEqual(seen[0]['headers'],{})

    def test_input_bounds_fail_before_any_provider_call(self):
        embed=make_embed_many(enabled=True,transport=lambda **kw:self.fail('must not call'))
        for values in ([],[''],['x']*33,['x'*10001],['x'*5000]*32,[None]):
            with self.assertRaises(ValueError):
                embed(values)

    def test_malformed_vectors_or_different_models_cannot_enter_index(self):
        for vector in ([0.0]*1024,[1.0], [float('nan')]+[0.0]*1023,[True]+[0.0]*1023):
            embed=make_embed_many(enabled=True,transport=lambda **kw:{'model':MODEL,'shape':[1,1024],'data':[vector]})
            with self.assertRaises(ValueError):
                embed(['Synthetic stem'])
        embed=make_embed_many(enabled=True,transport=lambda **kw:{'model':'other-model','shape':[1,1024],'data':[VECTOR]})
        with self.assertRaises(ValueError):
            embed(['Synthetic stem'])
