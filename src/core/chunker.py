"""Text chunking utilities for plagiarism detection."""

import re
import logging
from typing import Optional
from dataclasses import dataclass

from langdetect import detect, LangDetectException

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """A chunk of text."""

    text: str
    position: int
    start_char: int
    end_char: int
    word_count: int


class TextChunker:
    """Utility for splitting text into chunks with overlap."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        min_chunk_size: Optional[int] = None,
    ):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.min_chunk_size = min_chunk_size or settings.min_chunk_size

    def chunk_text(self, text: str) -> list[TextChunk]:
        """Split text into overlapping chunks.

        Args:
            text: The text to split

        Returns:
            List of TextChunk objects
        """
        # Normalize text first
        text = self.normalize_text(text)

        if not text:
            return []

        # Split into words
        words = text.split()

        if len(words) <= self.chunk_size:
            # Text is smaller than chunk size, return as single chunk
            return [
                TextChunk(
                    text=text,
                    position=0,
                    start_char=0,
                    end_char=len(text),
                    word_count=len(words),
                )
            ]

        chunks = []
        position = 0
        word_index = 0

        while word_index < len(words):
            # Get chunk words
            chunk_words = words[word_index : word_index + self.chunk_size]

            if len(chunk_words) < self.min_chunk_size:
                # Skip chunks that are too small (except if it's the only remaining)
                if chunks:
                    break

            chunk_text = " ".join(chunk_words)

            # Calculate character positions
            start_char = self._find_char_position(text, word_index, words)
            end_char = start_char + len(chunk_text)

            chunks.append(
                TextChunk(
                    text=chunk_text,
                    position=position,
                    start_char=start_char,
                    end_char=end_char,
                    word_count=len(chunk_words),
                )
            )

            position += 1
            # Move by (chunk_size - overlap) words
            word_index += self.chunk_size - self.chunk_overlap

        return chunks

    def _find_char_position(
        self, text: str, word_index: int, words: list[str]
    ) -> int:
        """Find character position of a word in text."""
        if word_index == 0:
            return 0

        # Count characters up to this word
        char_pos = 0
        for i in range(word_index):
            char_pos += len(words[i]) + 1  # +1 for space

        return min(char_pos, len(text))

    def normalize_text(self, text: str) -> str:
        """Normalize text for processing.

        - Remove extra whitespace
        - Remove special characters (keep punctuation)
        - Lowercase (optional, disabled by default)
        """
        if not text:
            return ""

        # Replace multiple whitespace with single space
        text = re.sub(r"\s+", " ", text)

        # Remove control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def detect_language(self, text: str) -> str:
        """Detect language of text.

        Returns:
            Language code (vi, en, etc.) or 'unknown'
        """
        try:
            if len(text) < 20:
                return "unknown"
            lang = detect(text)
            return lang
        except LangDetectException:
            return "unknown"

    def split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Handles both Vietnamese and English sentence boundaries.
        """
        # Normalize first
        text = self.normalize_text(text)

        # Split on sentence-ending punctuation
        # Keep the punctuation with the sentence
        sentences = re.split(r"(?<=[.!?])\s+", text)

        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def chunk_by_sentences(
        self, text: str, max_sentences: int = 5
    ) -> list[TextChunk]:
        """Chunk text by sentences instead of words.

        Args:
            text: Text to chunk
            max_sentences: Maximum sentences per chunk

        Returns:
            List of TextChunk objects
        """
        sentences = self.split_into_sentences(text)

        if not sentences:
            return []

        chunks = []
        position = 0
        current_chunk_sentences = []

        for sentence in sentences:
            current_chunk_sentences.append(sentence)

            if len(current_chunk_sentences) >= max_sentences:
                chunk_text = " ".join(current_chunk_sentences)
                word_count = len(chunk_text.split())

                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        position=position,
                        start_char=0,  # Simplified
                        end_char=len(chunk_text),
                        word_count=word_count,
                    )
                )
                position += 1

                # Keep last sentence for overlap
                current_chunk_sentences = [current_chunk_sentences[-1]]

        # Handle remaining sentences
        if current_chunk_sentences and len(current_chunk_sentences) > 1:
            chunk_text = " ".join(current_chunk_sentences)
            word_count = len(chunk_text.split())

            if word_count >= self.min_chunk_size:
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        position=position,
                        start_char=0,
                        end_char=len(chunk_text),
                        word_count=word_count,
                    )
                )

        return chunks

    def get_word_count(self, text: str) -> int:
        """Get word count of text."""
        if not text:
            return 0
        return len(text.split())


# Singleton instance
_chunker: Optional[TextChunker] = None


def get_chunker() -> TextChunker:
    """Get singleton chunker instance."""
    global _chunker
    if _chunker is None:
        _chunker = TextChunker()
    return _chunker
