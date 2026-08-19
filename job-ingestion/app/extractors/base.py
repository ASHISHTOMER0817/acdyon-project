"""Extractor contract — convert crawled text into raw job dicts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseExtractor(ABC):
    """Downstream validators consume the list of dicts this returns."""

    name: str = "base"

    @abstractmethod
    def extract(self, content: str, page_url: str, source_name: str) -> list[dict[str, Any]]:
        """Return Gemini (or equivalent) job objects. May be empty; must not silently invent required fields."""
