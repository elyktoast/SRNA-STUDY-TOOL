"""Opt-in embeddings through the existing private signed staging relay.

No provider credentials enter the container. No network activity on import.
"""
import math
import time
from item_ai_https_transport_v2 import make_transport, TransportError

MODEL = "@cf/baai/bge-m3"
RELAY = "https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay"

def valid_vector(vector):
    return (isinstance(vector, list) and len(vector) == 1024
            and all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=1e100 for v in vector)
            and any(v != 0 for v in vector))

def make_embed_many(*, enabled, relay_secret=None, transport=None, wait=time.sleep):
    if enabled is not True:
        raise ValueError("Embedding calls require explicit opt-in")
    if transport is None:
        transport = make_transport(allowed_hosts=["api.cloudflare.com"], timeout_seconds=50,
            max_response_bytes=1048576, relay_url=RELAY, relay_secret=relay_secret)
    if not callable(transport) or not callable(wait):
        raise ValueError("Trusted embedding transport required")
    def embed_many(texts):
        if (not isinstance(texts,list) or not 1<=len(texts)<=32
                or any(not isinstance(t,str) or not t.strip() or len(t)>10000 for t in texts)
                or sum(map(len,texts))>128000):
            raise ValueError("Invalid embedding batch")
        # The endpoint identifies the approved provider; transport sends the
        # signed request to RELAY. It never uses a provider bearer credential.
        for attempt in range(4):
            try:
                response = transport(endpoint="https://api.cloudflare.com/client/v4/accounts/5a84e0fe00e430d25e901b260861381e/ai/run/"+MODEL,
                    headers={}, body={"task":"semantic_embeddings","model":MODEL,"text":texts})
                break
            except TransportError as error:
                transient={'RELAY_NETWORK','PROVIDER_NETWORK','PROVIDER_TIMEOUT','PROVIDER_RATE_LIMIT','RELAY_HTTP_429','RELAY_HTTP_503','RELAY_HTTP_504'}
                if attempt==3 or error.rule not in transient or (error.retry_after_seconds or 0)>60:
                    raise
                delay=max((2,5,10)[attempt],error.retry_after_seconds or 0)
                if error.rule in ('PROVIDER_RATE_LIMIT','RELAY_HTTP_429'):
                    delay=max(delay,60)
                wait(delay)
        data=response.get("data") if isinstance(response,dict) else None
        if (not isinstance(response,dict) or set(response)!={"model","shape","data"}
                or response["model"]!=MODEL or response["shape"]!=[len(texts),1024]
                or not isinstance(data,list) or len(data)!=len(texts)
                or any(not valid_vector(v) for v in data)):
            raise ValueError("Invalid embedding relay response")
        return data
    return embed_many
