"""Tag handling: extracting #tags out of note text.

The seam here is `extract_tags`: it pulls `#tag` tokens out of arbitrary text,
lowercases and dedupes them, and returns both the cleaned body (tags removed)
and the ordered tag list. Tags are matched case-insensitively elsewhere by
storing/querying them lowercased.
"""

from __future__ import annotations

import re

_TAG = re.compile(r"(?:^|\s)#([\w-]+)", re.UNICODE)


def extract_tags(text: str) -> tuple[str, list[str]]:
    tags: list[str] = []

    def _replace(m: re.Match) -> str:
        tag = m.group(1)
        # Do not swallow purely-numeric token as a tag? Keep as-is: a bare
        # "#123" is unusual; treat it as a tag like any other.
        tags.append(tag.lower())
        return " "

    body = _TAG.sub(_replace, text)
    body = re.sub(r"\s{2,}", " ", body).strip(" ,")
    # De-duplicate while preserving first-seen order.
    seen: list[str] = []
    for t in tags:
        if t not in seen:
            seen.append(t)
    return body, seen