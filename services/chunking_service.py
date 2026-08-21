import re
from typing import List

class ChunkingService:
    def __init__(self, max_chunk_size: int = 500, overlap: int = 50):
        """
        Initialize the chunking service.
        :param max_chunk_size: Maximum number of characters per chunk
        :param overlap: Number of characters to overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into semantic chunks.
        We'll split by paragraphs (double newline) and then combine paragraphs into chunks
        of approximately max_chunk_size characters, with overlap.
        """
        if not text:
            return []

        # Split by paragraphs (one or more blank lines)
        paragraphs = re.split(r'\n\s*\n', text.strip())
        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""
        current_length = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If adding this paragraph would exceed the max size and we already have content,
            # finalize the current chunk and start a new one with overlap
            if current_length + len(paragraph) > self.max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap from the end of the current chunk
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = overlap_text + (" " if overlap_text and not overlap_text.endswith(" ") else "") + paragraph
                current_length = len(current_chunk)
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += " " + paragraph
                else:
                    current_chunk = paragraph
                current_length = len(current_chunk)

        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _get_overlap(self, text: str) -> str:
        """
        Get the overlap text from the end of the chunk.
        """
        if len(text) <= self.overlap:
            return text
        # Try to break at a word boundary near the overlap point
        overlap_start = len(text) - self.overlap
        # Look for a space to avoid breaking words
        space_pos = text.rfind(' ', overlap_start, len(text))
        if space_pos == -1:
            return text[overlap_start:]
        return text[space_pos:]