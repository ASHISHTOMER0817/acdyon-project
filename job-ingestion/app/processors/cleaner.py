"""
Strip page chrome and collapse whitespace before Gemini sees the text.

Doing this deterministically cuts token cost and keeps the model focused
on listing-like content.
"""

from __future__ import annotations

import re


class ContentCleaner:
    """Best-effort HTML/text cleanup. Not a full readability engine."""

    _script_re = re.compile(r"<script[\s\S]*?</script>", re.IGNORECASE)
    _style_re = re.compile(r"<style[\s\S]*?</style>", re.IGNORECASE)
    _comment_re = re.compile(r"<!--[\s\S]*?-->")
    _tag_re = re.compile(r"<[^>]+>")
    _space_re = re.compile(r"[ \t]+")
    _blank_re = re.compile(r"\n{3,}")

    def clean(self, raw: str) -> str:
        """
        Return a compact text blob suitable for the extraction prompt.

        JSON payloads (public APIs) are left mostly intact so structure
        survives; HTML is de-tagged.
        """
        if not raw:
            return ""
        text = raw.strip()
        # Heuristic: JSON/API bodies should not be HTML-stripped.
        if text[:1] in ("{", "["):
            return text[:100_000]

        text = self._script_re.sub(" ", text)
        text = self._style_re.sub(" ", text)
        text = self._comment_re.sub(" ", text)
        text = self._tag_re.sub(" ", text)
        text = text.replace("\xa0", " ")
        text = self._space_re.sub(" ", text)
        text = self._blank_re.sub("\n\n", text)
        return text.strip()[:100_000]
