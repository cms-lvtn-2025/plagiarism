"""Document management for plagiarism detection system."""

import logging
from typing import Optional, Generator
from dataclasses import dataclass
from uuid import uuid4
from datetime import datetime

from src.config import get_settings
from src.storage import get_es_client, DocumentData, DocumentChunk
from src.embedding import get_ollama_client
from src.core.chunker import get_chunker

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of document upload."""

    document_id: str
    title: str
    chunks_created: int
    success: bool
    message: str
    error: Optional[str] = None


@dataclass
class BatchUploadResult:
    """Result of batch upload."""

    total_documents: int
    successful: int
    failed: int
    results: list[UploadResult]


class DocumentManager:
    """Manages document upload and retrieval."""

    def __init__(self):
        self.settings = get_settings()
        self.es_client = get_es_client()
        self.ollama_client = get_ollama_client()
        self.chunker = get_chunker()

    def upload_document(
        self,
        title: str,
        content: str,
        metadata: Optional[dict[str, str]] = None,
        language: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> UploadResult:
        """Upload a single document.

        Args:
            title: Document title
            content: Document content (plain text)
            metadata: Optional metadata dict
            language: Language code (auto-detect if not provided)
            document_id: Optional custom document ID

        Returns:
            UploadResult with status
        """
        try:
            # Generate document ID if not provided
            doc_id = document_id or str(uuid4())

            # Detect language if not provided
            if not language or language == "auto":
                language = self.chunker.detect_language(content)

            # Chunk the document
            chunks = self.chunker.chunk_text(content)

            if not chunks:
                return UploadResult(
                    document_id=doc_id,
                    title=title,
                    chunks_created=0,
                    success=False,
                    message="Document content too short to process",
                )

            # Generate embeddings for chunks
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.ollama_client.embed_batch(chunk_texts)

            # Create document chunks with embeddings
            doc_chunks = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_chunks.append(
                    DocumentChunk(
                        chunk_id=f"{doc_id}_chunk_{i}",
                        text=chunk.text,
                        embedding=embedding,
                        position=chunk.position,
                        word_count=chunk.word_count,
                    )
                )

            # Create document data
            doc_data = DocumentData(
                document_id=doc_id,
                title=title,
                content=content,
                chunks=doc_chunks,
                language=language,
                metadata=metadata or {},
                created_at=datetime.utcnow(),
            )

            # Index document
            success = self.es_client.index_document(doc_data)

            if success:
                logger.info(f"Uploaded document: {doc_id} ({len(doc_chunks)} chunks)")
                return UploadResult(
                    document_id=doc_id,
                    title=title,
                    chunks_created=len(doc_chunks),
                    success=True,
                    message=f"Successfully uploaded with {len(doc_chunks)} chunks",
                )
            else:
                return UploadResult(
                    document_id=doc_id,
                    title=title,
                    chunks_created=0,
                    success=False,
                    message="Failed to index document",
                    error="Elasticsearch indexing failed",
                )

        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            return UploadResult(
                document_id=document_id or "",
                title=title,
                chunks_created=0,
                success=False,
                message="Upload failed",
                error=str(e),
            )

    def batch_upload(
        self,
        documents: list[dict],
        on_progress: Optional[callable] = None,
    ) -> BatchUploadResult:
        """Upload multiple documents.

        Args:
            documents: List of dicts with keys: title, content, metadata, language
            on_progress: Optional callback for progress updates

        Returns:
            BatchUploadResult with all results
        """
        results = []
        successful = 0
        failed = 0

        for i, doc in enumerate(documents):
            result = self.upload_document(
                title=doc.get("title", f"Document {i + 1}"),
                content=doc.get("content", ""),
                metadata=doc.get("metadata"),
                language=doc.get("language"),
            )

            results.append(result)

            if result.success:
                successful += 1
            else:
                failed += 1

            if on_progress:
                on_progress(i + 1, len(documents), result)

        return BatchUploadResult(
            total_documents=len(documents),
            successful=successful,
            failed=failed,
            results=results,
        )

    def batch_upload_stream(
        self,
        documents: Generator[dict, None, None],
    ) -> Generator[UploadResult, None, None]:
        """Stream upload documents one by one.

        Args:
            documents: Generator of document dicts

        Yields:
            UploadResult for each document
        """
        for doc in documents:
            result = self.upload_document(
                title=doc.get("title", "Untitled"),
                content=doc.get("content", ""),
                metadata=doc.get("metadata"),
                language=doc.get("language"),
            )
            yield result

    def get_document(
        self,
        document_id: str,
        include_content: bool = False,
        include_chunks: bool = False,
    ) -> Optional[dict]:
        """Get document by ID.

        Args:
            document_id: Document ID
            include_content: Include full content
            include_chunks: Include chunk details

        Returns:
            Document dict or None
        """
        doc = self.es_client.get_document(document_id, include_chunks=include_chunks)

        if doc and not include_content:
            doc.pop("content", None)

        return doc

    def delete_document(self, document_id: str) -> bool:
        """Delete document and its chunks.

        Args:
            document_id: Document ID to delete

        Returns:
            True if deleted, False otherwise
        """
        return self.es_client.delete_document(document_id)

    def search_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[dict[str, str]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Search documents.

        Args:
            query: Text query
            filters: Metadata filters
            limit: Max results
            offset: Pagination offset

        Returns:
            Tuple of (documents list, total count)
        """
        return self.es_client.search_documents(
            query=query,
            filters=filters,
            limit=limit,
            offset=offset,
        )

    def get_stats(self) -> dict:
        """Get system statistics."""
        return {
            "total_documents": self.es_client.get_document_count(),
            "es_health": self.es_client.health_check(),
            "ollama_health": self.ollama_client.health_check(),
        }


# Singleton instance
_document_manager: Optional[DocumentManager] = None


def get_document_manager() -> DocumentManager:
    """Get singleton document manager instance."""
    global _document_manager
    if _document_manager is None:
        _document_manager = DocumentManager()
    return _document_manager
