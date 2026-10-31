"""Official NCE/SEE response-format validation, independent of clinical review.

Images and video are stimuli, not standalone answer formats.
"""
import math

FORMATS = ("single", "multi", "calculation", "drag_drop", "hotspot")
DRAG_MODES = ("order", "match_single_use", "match_multiple_use")


def validate(item):
    errors = []
    kind = item.get("type")
    if kind not in FORMATS:
        return ["Unknown response format"]
    if kind in ("single", "multi"):
        options, answer = item.get("options"), item.get("answer")
        min_options, max_options = (4, 4) if kind == "single" else (4, 8)
        if not isinstance(options, list) or not min_options <= len(options) <= max_options or not all(isinstance(v, str) and v.strip() for v in options):
            errors.append("Invalid options")
        elif len({v.strip().casefold() for v in options}) != len(options):
            errors.append("Duplicate options")
        if not isinstance(answer, list) or not answer or not all(type(v) is int and 0 <= v < len(options or []) for v in answer) or len(set(answer)) != len(answer):
            errors.append("Invalid answer indexes")
        elif kind == "single" and len(answer) != 1:
            errors.append("Single choice requires one answer")
        elif kind == "multi" and (len(answer) < 2 or len(answer) >= len(options)):
            errors.append("Multiple response requires two or more but not all choices")
        if kind == "multi" and item.get("selectCount") != len(answer or []):
            errors.append("Selection count must equal keyed answers")
    elif kind == "calculation":
        answer = item.get("numericAnswer")
        places = item.get("decimalPlaces")
        if type(answer) not in (int, float) or not math.isfinite(answer):
            errors.append("Finite numeric answer required")
        if type(places) is not int or places not in (0, 1, 2):
            errors.append("Decimal places must be 0, 1, or 2")
        if not isinstance(item.get("units"), str) or not item["units"].strip():
            errors.append("Units must be explicit")
    elif kind == "drag_drop":
        mode, tokens, targets = item.get("dragMode"), item.get("tokens"), item.get("targets")
        if mode not in DRAG_MODES:
            errors.append("Unknown drag-and-drop mode")
        if not isinstance(tokens, list) or len(tokens) < 2 or len(set(tokens)) != len(tokens):
            errors.append("Unique draggable tokens required")
        if not isinstance(targets, list) or len(targets) < 2 or len(set(targets)) != len(targets):
            errors.append("Unique targets required")
        mapping = item.get("mapping")
        if not isinstance(mapping, list) or len(mapping) != len(targets or []) or any(type(v) is not int or v < 0 or v >= len(tokens or []) for v in mapping):
            errors.append("Complete valid target mapping required")
        elif mode != "match_multiple_use" and len(set(mapping)) != len(mapping):
            errors.append("Repeated tokens only allowed in multiple-use matching")
        elif mode == "match_multiple_use" and set(mapping) != set(range(len(tokens))):
            errors.append("Multiple-use matching must use every token at least once")
    elif kind == "hotspot":
        asset, region = item.get("imageAssetId"), item.get("correctRegion")
        if not isinstance(asset, str) or not asset.strip():
            errors.append("Image asset required")
        if not isinstance(region, dict) or region.get("shape") != "rect" or any(type(region.get(k)) not in (int, float) or not 0 <= region[k] <= 1 for k in ("x", "y", "width", "height")):
            errors.append("Normalized rectangular answer region required")
        elif region["width"] <= 0 or region["height"] <= 0 or region["x"] + region["width"] > 1 or region["y"] + region["height"] > 1:
            errors.append("Hotspot region outside image")
    media = item.get("stimulus")
    if media is not None and (not isinstance(media, dict) or media.get("type") not in ("image", "video") or not isinstance(media.get("assetId"), str) or not media["assetId"]):
        errors.append("Invalid image/video stimulus")
    return errors
