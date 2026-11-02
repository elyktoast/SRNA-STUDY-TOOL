"""Only accepts backend-signed blind results for staging screening handoff."""
from item_blind_attestation_v2 import verify
from item_screening_blind_handoff_v2 import attach

def attach_verified(screening, envelope, *, item_id, run_id, secret):
    result = verify(envelope, item_id=item_id, run_id=run_id, secret=secret)
    return attach(screening, result)
