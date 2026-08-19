"""Extraction layer: Gemini turns crawled text into job objects."""

from app.extractors.base import BaseExtractor
from app.extractors.gemini_extractor import GeminiExtractor

__all__ = ["BaseExtractor", "GeminiExtractor"]
