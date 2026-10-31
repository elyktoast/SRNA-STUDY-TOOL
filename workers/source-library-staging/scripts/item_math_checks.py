"""Fail-closed numeric verification for v2.0 SA items.

The calculation specification is reviewer-supplied, not AI self-attested.
Only explicit supported operations are recomputed; no eval.
"""
import math
import operator

OPERATIONS = {
    "add": operator.add, "subtract": operator.sub,
    "multiply": operator.mul, "divide": operator.truediv,
}

def check(item, calculation=None):
    if item.get("format") != "SA":
        return []
    if not isinstance(calculation, dict):
        return [{"rule_id": "R-7.3.4", "message": "Independent calculation specification required"}]
    op = OPERATIONS.get(calculation.get("operation"))
    operands = calculation.get("operands")
    if op is None or not isinstance(operands, list) or len(operands) != 2 or any(
        type(v) not in (int, float) or not math.isfinite(v) for v in operands
    ):
        return [{"rule_id": "R-7.3.4", "message": "Unsupported calculation or invalid operands"}]
    try:
        result = op(*operands)
    except (ZeroDivisionError, OverflowError):
        return [{"rule_id": "R-7.3.4", "message": "Calculation failed"}]
    if not math.isfinite(result):
        return [{"rule_id": "R-7.3.4", "message": "Nonfinite calculation"}]
    sa = item.get("sa")
    if not isinstance(sa, dict) or type(sa.get("answer")) not in (int, float) or type(sa.get("tolerance")) not in (int, float):
        return [{"rule_id": "R-7.3.5", "message": "Numeric answer or tolerance missing"}]
    if not math.isfinite(sa["answer"]) or not math.isfinite(sa["tolerance"]) or sa["tolerance"] < 0:
        return [{"rule_id": "R-7.3.5", "message": "Invalid numeric answer or tolerance"}]
    if abs(result - sa["answer"]) > sa["tolerance"] + 1e-12:
        return [{"rule_id": "R-7.3.5", "message": "Independent result differs from keyed answer"}]
    return []
