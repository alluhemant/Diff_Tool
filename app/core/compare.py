# app/core/compare.py
from difflib import unified_diff
import json
from typing import Tuple, Dict, Any
import xml.etree.ElementTree as ET
from xml.dom import minidom


"""
compare_responses() detects content-type → calls:
    compare_json() → normalize + diff
    
    compare_xml() → pretty format + diff
    
    compare_text() → fallback diff
"""


def compare_responses(resp1: str, resp2: str) -> Tuple[str, Dict[str, Any]]:
    # determining the content types
    content_type1 = detect_content_type(resp1)
    content_type2 = detect_content_type(resp2)

    # If the types don't match returns early with the type mismatch info.
    if content_type1 != content_type2:
        return (
            f"Content type mismatch:\n- Response 1: {content_type1}\n- Response 2: {content_type2}",
            {
                "content_type1": content_type1,
                "content_type2": content_type2,
                "difference_count": -1,
                "type_mismatch": True
            }
        )

    # handles based on a content type we received.
    if content_type1 == "json":
        return compare_json(resp1, resp2)
    elif content_type1 == "xml":
        return compare_xml(resp1, resp2)
    else:
        return compare_text(resp1, resp2)


def detect_content_type(response: str) -> str:
    # detects if the content-type is JSON, XML, or plain text.
    response = response.strip()

    # checks for JSON.
    if response.startswith(('{', '[')) or response.lstrip().startswith(('{', '[')):
        try:
            json.loads(response)
            return "json"
        except json.JSONDecodeError:
            pass

    # checks for XML.
    if response.startswith('<') or response.lstrip().startswith('<'):
        try:
            ET.fromstring(response)
            return "xml"
        except ET.ParseError:
            pass

    return "text"


def deep_json_normalize(json_str: str) -> str:
    try:
        data = json.loads(json_str)

        # attempting to normalize any nested stringifies JSON
        def recursively_parse(obj):
            if isinstance(obj, str):
                try:
                    parsed = json.loads(obj)
                    return recursively_parse(parsed)
                except json.JSONDecodeError:
                    return obj
            elif isinstance(obj, dict):
                return {k: recursively_parse(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [recursively_parse(item) for item in obj]
            return obj

        normalized = recursively_parse(data)
        return json.dumps(normalized, indent=2, sort_keys=True)
    except Exception:
        return json_str


def compare_json(resp1: str, resp2: str) -> Tuple[str, Dict[str, Any]]:
    try:
        norm1 = deep_json_normalize(resp1)
        norm2 = deep_json_normalize(resp2)

        lines1 = norm1.splitlines()
        lines2 = norm2.splitlines()
        diff = list(unified_diff(lines1, lines2, lineterm=""))

        return (
            "\n".join(diff),
            {
                "difference_count": len(diff),
                "response1_length": len(resp1),
                "response2_length": len(resp2),
                "content_type": "json",
                "normalized_identical": norm1 == norm2
            }
        )
    except Exception as e:
        return compare_text(resp1, resp2, {"json_parse_error": str(e)})


def compare_xml(resp1: str, resp2: str) -> Tuple[str, Dict[str, Any]]:
    try:
        def normalize_xml(xml_str: str) -> str:
            try:
                xml = minidom.parseString(xml_str)
                return xml.toprettyxml(indent="  ")
            except Exception:
                return xml_str

        norm1 = normalize_xml(resp1)
        norm2 = normalize_xml(resp2)

        lines1 = norm1.splitlines()
        lines2 = norm2.splitlines()
        diff = list(unified_diff(lines1, lines2, lineterm=""))

        return (
            "\n".join(diff),
            {
                "difference_count": len(diff),
                "response1_length": len(resp1),
                "response2_length": len(resp2),
                "content_type": "xml",
                "normalized_identical": norm1 == norm2
            }
        )
    except Exception as e:
        return compare_text(resp1, resp2, {"xml_parse_error": str(e)})


def compare_text(resp1: str, resp2: str, extra_metrics: dict = None) -> Tuple[str, Dict[str, Any]]:
    lines1 = resp1.splitlines()
    lines2 = resp2.splitlines()
    diff = list(unified_diff(lines1, lines2, lineterm=""))

    metrics = {
        "difference_count": len(diff),
        "response1_length": len(resp1),
        "response2_length": len(resp2),
        "content_type": "text"
    }

    if extra_metrics:
        metrics.update(extra_metrics)

    return "\n".join(diff), metrics
