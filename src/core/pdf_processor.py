"""PDF processing utilities using unstructured library."""

import logging
import os
import time
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import (
    Title,
    NarrativeText,
    ListItem,
    Table,
    Header,
    Footer,
    Text,
)

from src.config import get_settings
from src.core.chunker import TextChunker

logger = logging.getLogger(__name__)


@dataclass
class PdfSection:
    """A section of PDF document with title and content."""

    section_title: str
    content: str
    element_type: str  # Title, NarrativeText, ListItem, Table, etc.
    position: int
    word_count: int


@dataclass
class PdfChunk:
    """A chunk ready for indexing with embedding."""

    chunk_id: str
    section_title: str
    text: str
    element_type: str
    position: int
    word_count: int


@dataclass
class PdfProcessingResult:
    """Result of PDF processing."""

    success: bool
    document_title: str
    chunks: list[PdfChunk] = field(default_factory=list)
    total_pages: int = 0
    total_elements: int = 0
    processing_time_ms: int = 0
    pdf_metadata: dict = field(default_factory=dict)
    error_message: str = ""


class PdfProcessor:
    """Process PDF documents and extract structured content."""

    # Element types that indicate section headers/titles
    TITLE_TYPES = (Title, Header)

    # Element types to include in content
    CONTENT_TYPES = (NarrativeText, ListItem, Table, Text)

    # Element types to skip
    SKIP_TYPES = (Footer,)

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
        self.chunker = TextChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            min_chunk_size=self.min_chunk_size,
        )

    def process_pdf(
        self,
        pdf_path: str,
        document_id: str,
        extract_images: bool = False,
    ) -> PdfProcessingResult:
        """
        Process a PDF file and extract structured content with titles.

        Args:
            pdf_path: Path to the PDF file
            document_id: Unique document identifier for chunk IDs
            extract_images: Whether to extract images (requires additional deps)

        Returns:
            PdfProcessingResult with extracted chunks
        """
        start_time = time.time()

        if not os.path.exists(pdf_path):
            return PdfProcessingResult(
                success=False,
                document_title="",
                error_message=f"PDF file not found: {pdf_path}",
            )

        try:
            # Extract elements from PDF using unstructured
            logger.info(f"Processing PDF: {pdf_path}")
            print(f"[1/5] Loading PDF: {Path(pdf_path).name}...", flush=True)

            elements = partition_pdf(
                filename=pdf_path,
                strategy="hi_res",  # hi_res: with OCR + deep learning
                include_page_breaks=True,
                infer_table_structure=True,
                extract_images_in_pdf=extract_images,
            )
            print(f"[2/5] PDF loaded - extracted {len(elements)} elements", flush=True)

            if not elements:
                return PdfProcessingResult(
                    success=False,
                    document_title="",
                    error_message="No content extracted from PDF",
                )

            # Extract document title (first Title element or filename)
            print("[3/5] Extracting document title...", flush=True)
            document_title = self._extract_document_title(elements, pdf_path)

            # Group elements by sections
            print("[4/5] Grouping elements into sections...", flush=True)
            sections = self._group_into_sections(elements)
            print(f"       Created {len(sections)} sections", flush=True)

            # Convert sections to chunks
            print("[5/5] Converting sections to chunks...", flush=True)
            chunks = self._sections_to_chunks(sections, document_id)

            processing_time = int((time.time() - start_time) * 1000)
            print(f"[DONE] Processed {len(chunks)} chunks in {processing_time}ms", flush=True)

            logger.info(
                f"Processed PDF: {len(elements)} elements -> {len(chunks)} chunks "
                f"in {processing_time}ms"
            )

            return PdfProcessingResult(
                success=True,
                document_title=document_title,
                chunks=chunks,
                total_pages=self._count_pages(elements),
                total_elements=len(elements),
                processing_time_ms=processing_time,
                pdf_metadata=self._extract_metadata(elements),
            )

        except Exception as e:
            logger.error(f"Failed to process PDF: {e}", exc_info=True)
            return PdfProcessingResult(
                success=False,
                document_title="",
                error_message=str(e),
            )

    def _extract_document_title(self, elements: list, pdf_path: str) -> str:
        """Extract document title from elements or filename."""
        # Try to find first Title element
        for el in elements[:10]:  # Check first 10 elements
            if isinstance(el, Title):
                title = str(el).strip()
                if len(title) > 3:  # Avoid very short titles
                    return title

        # Fallback to filename
        return Path(pdf_path).stem

    def _group_into_sections(self, elements: list) -> list[PdfSection]:
        """
        Group elements into sections based on titles/headers.

        Strategy:
        1. When encountering a Title/Header, start a new section
        2. Accumulate content until next Title/Header
        3. If content gets too long, split using chunker
        """
        sections: list[PdfSection] = []
        current_title = "Introduction"  # Default section name
        current_content: list[str] = []
        current_types: list[str] = []
        position = 0

        for el in elements:
            el_type = type(el).__name__

            # Skip footer elements
            if isinstance(el, self.SKIP_TYPES):
                continue

            # Check if this is a title/header (new section)
            if isinstance(el, self.TITLE_TYPES):
                # Save previous section if it has content
                if current_content:
                    section = self._create_section(
                        title=current_title,
                        content_parts=current_content,
                        element_types=current_types,
                        position=position,
                    )
                    if section:
                        sections.append(section)
                        position += 1

                # Start new section
                current_title = str(el).strip() or "Untitled Section"
                current_content = []
                current_types = []

            # Add content
            elif isinstance(el, self.CONTENT_TYPES):
                text = str(el).strip()
                if text:
                    current_content.append(text)
                    current_types.append(el_type)

        # Don't forget the last section
        if current_content:
            section = self._create_section(
                title=current_title,
                content_parts=current_content,
                element_types=current_types,
                position=position,
            )
            if section:
                sections.append(section)

        return sections

    def _create_section(
        self,
        title: str,
        content_parts: list[str],
        element_types: list[str],
        position: int,
    ) -> Optional[PdfSection]:
        """Create a PdfSection from content parts."""
        content = "\n\n".join(content_parts)
        content = self.chunker.normalize_text(content)

        if not content:
            return None

        word_count = len(content.split())

        # Determine primary element type
        element_type = "Mixed"
        if element_types:
            # Most common type
            type_counts = {}
            for t in element_types:
                type_counts[t] = type_counts.get(t, 0) + 1
            element_type = max(type_counts, key=type_counts.get)

        return PdfSection(
            section_title=title,
            content=content,
            element_type=element_type,
            position=position,
            word_count=word_count,
        )

    def _sections_to_chunks(
        self, sections: list[PdfSection], document_id: str
    ) -> list[PdfChunk]:
        """
        Convert sections to chunks, splitting large sections if needed.

        Each section is chunked if it exceeds chunk_size, preserving the section title.
        """
        chunks: list[PdfChunk] = []
        chunk_position = 0

        for section in sections:
            # Check if section needs to be split
            if section.word_count <= self.chunk_size:
                # Single chunk for this section
                chunk = PdfChunk(
                    chunk_id=f"{document_id}_chunk_{chunk_position}",
                    section_title=section.section_title,
                    text=section.content,
                    element_type=section.element_type,
                    position=chunk_position,
                    word_count=section.word_count,
                )
                chunks.append(chunk)
                chunk_position += 1
            else:
                # Split section into multiple chunks
                text_chunks = self.chunker.chunk_text(section.content)

                for i, text_chunk in enumerate(text_chunks):
                    # Add section context to title for sub-chunks
                    if len(text_chunks) > 1:
                        chunk_title = f"{section.section_title} (part {i + 1}/{len(text_chunks)})"
                    else:
                        chunk_title = section.section_title

                    chunk = PdfChunk(
                        chunk_id=f"{document_id}_chunk_{chunk_position}",
                        section_title=chunk_title,
                        text=text_chunk.text,
                        element_type=section.element_type,
                        position=chunk_position,
                        word_count=text_chunk.word_count,
                    )
                    chunks.append(chunk)
                    chunk_position += 1

        return chunks

    def _count_pages(self, elements: list) -> int:
        """Count pages from page break elements."""
        from unstructured.documents.elements import PageBreak

        page_count = 1
        for el in elements:
            if isinstance(el, PageBreak):
                page_count += 1
        return page_count

    def _extract_metadata(self, elements: list) -> dict:
        """Extract any available metadata from elements."""
        metadata = {}

        # Try to get metadata from first element if available
        if elements and hasattr(elements[0], "metadata"):
            el_meta = elements[0].metadata
            if hasattr(el_meta, "filename"):
                metadata["filename"] = el_meta.filename
            if hasattr(el_meta, "filetype"):
                metadata["filetype"] = el_meta.filetype
            if hasattr(el_meta, "page_number"):
                metadata["first_page"] = el_meta.page_number

        return metadata


# Singleton instance
_pdf_processor: Optional[PdfProcessor] = None


def get_pdf_processor() -> PdfProcessor:
    """Get singleton PDF processor instance."""
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PdfProcessor()
    return _pdf_processor
