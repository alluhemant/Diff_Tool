# app/core/compare.py

from difflib import unified_diff


def compare_responses(resp1: str, resp2: str) -> tuple[str, str]:
    lines1 = resp1.splitlines()
    lines2 = resp2.splitlines()

    diff = list(unified_diff(lines1, lines2, lineterm=""))

    diff_output = "\n".join(diff)
    metrics = str(len(diff))  # total number of diff lines

    return diff_output, metrics
