"""gRPC Service implementation for Plagiarism Detection."""

import logging
from typing import Iterator

import grpc

from src import plagiarism_pb2, plagiarism_pb2_grpc
from src.core import (
    get_detector,
    get_document_manager,
    PlagiarismResult,
)
from src.storage import get_es_client

logger = logging.getLogger(__name__)


class PlagiarismServicer(plagiarism_pb2_grpc.PlagiarismServiceServicer):
    """gRPC service implementation for plagiarism detection."""

    def __init__(self):
        self.detector = get_detector()
        self.doc_manager = get_document_manager()
        self.es_client = get_es_client()

    def CheckPlagiarism(
        self,
        request: plagiarism_pb2.CheckRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.CheckResponse:
        """Check text for plagiarism."""
        try:
            logger.info(f"CheckPlagiarism request: {len(request.text)} chars")

            # Extract options
            options = request.options
            min_similarity = options.min_similarity if options.min_similarity > 0 else None
            top_k = options.top_k if options.top_k > 0 else None
            include_ai = options.include_ai_analysis if options.include_ai_analysis else True
            exclude_docs = list(options.exclude_docs) if options.exclude_docs else None

            # Run plagiarism check
            result = self.detector.check_plagiarism(
                text=request.text,
                min_similarity=min_similarity,
                top_k=top_k,
                include_ai_analysis=include_ai,
                exclude_doc_ids=exclude_docs,
            )

            return self._build_check_response(result)

        except Exception as e:
            logger.error(f"CheckPlagiarism error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.CheckResponse()

    def _build_check_response(
        self, result: PlagiarismResult
    ) -> plagiarism_pb2.CheckResponse:
        """Build gRPC response from PlagiarismResult."""
        # Convert severity string to enum
        severity_map = {
            "SAFE": plagiarism_pb2.SAFE,
            "LOW": plagiarism_pb2.LOW,
            "MEDIUM": plagiarism_pb2.MEDIUM,
            "HIGH": plagiarism_pb2.HIGH,
            "CRITICAL": plagiarism_pb2.CRITICAL,
        }

        # Build matches
        matches = []
        for m in result.matches:
            matches.append(
                plagiarism_pb2.Match(
                    document_id=m.document_id,
                    document_title=m.document_title,
                    matched_text=m.matched_text,
                    input_text=m.input_text,
                    similarity_score=m.similarity_score,
                    position=plagiarism_pb2.Position(
                        start=m.position_start,
                        end=m.position_end,
                        chunk_index=m.chunk_index,
                    ),
                )
            )

        # Build chunk analysis
        chunks = []
        for c in result.chunk_analysis:
            chunks.append(
                plagiarism_pb2.ChunkAnalysis(
                    chunk_index=c.chunk_index,
                    text=c.text,
                    max_similarity=c.max_similarity,
                    status=severity_map.get(c.status, plagiarism_pb2.SAFE),
                    best_match_doc_id=c.best_match_doc_id or "",
                )
            )

        # Build metadata
        metadata = plagiarism_pb2.Metadata(
            processing_time_ms=result.processing_time_ms,
            chunks_analyzed=result.chunks_analyzed,
            documents_searched=result.documents_searched,
        )

        return plagiarism_pb2.CheckResponse(
            request_id=result.request_id,
            plagiarism_percentage=result.plagiarism_percentage,
            severity=severity_map.get(result.severity, plagiarism_pb2.SAFE),
            explanation=result.explanation,
            matches=matches,
            chunks=chunks,
            metadata=metadata,
        )

    def UploadDocument(
        self,
        request: plagiarism_pb2.UploadRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.UploadResponse:
        """Upload a document to the database."""
        try:
            logger.info(f"UploadDocument: {request.title}")

            # Convert metadata
            metadata = dict(request.metadata) if request.metadata else {}

            result = self.doc_manager.upload_document(
                title=request.title,
                content=request.content,
                metadata=metadata,
                language=request.language or None,
            )

            return plagiarism_pb2.UploadResponse(
                document_id=result.document_id,
                title=result.title,
                chunks_created=result.chunks_created,
                message=result.message,
                success=result.success,
            )

        except Exception as e:
            logger.error(f"UploadDocument error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.UploadResponse(success=False, message=str(e))

    def BatchUpload(
        self,
        request_iterator: Iterator[plagiarism_pb2.UploadRequest],
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.BatchUploadResponse:
        """Batch upload documents using streaming."""
        try:
            results = []
            successful = 0
            failed = 0

            for request in request_iterator:
                metadata = dict(request.metadata) if request.metadata else {}

                result = self.doc_manager.upload_document(
                    title=request.title,
                    content=request.content,
                    metadata=metadata,
                    language=request.language or None,
                )

                results.append(
                    plagiarism_pb2.UploadResult(
                        document_id=result.document_id,
                        title=result.title,
                        success=result.success,
                        error=result.error or "",
                    )
                )

                if result.success:
                    successful += 1
                else:
                    failed += 1

            return plagiarism_pb2.BatchUploadResponse(
                total_documents=len(results),
                successful=successful,
                failed=failed,
                results=results,
            )

        except Exception as e:
            logger.error(f"BatchUpload error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.BatchUploadResponse()

    def GetDocument(
        self,
        request: plagiarism_pb2.GetDocumentRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.GetDocumentResponse:
        """Get document by ID."""
        try:
            doc = self.doc_manager.get_document(
                document_id=request.document_id,
                include_content=request.include_content,
                include_chunks=request.include_chunks,
            )

            if not doc:
                return plagiarism_pb2.GetDocumentResponse(found=False)

            # Build chunks if included
            chunks = []
            if request.include_chunks and "chunks" in doc:
                for c in doc["chunks"]:
                    chunks.append(
                        plagiarism_pb2.Chunk(
                            chunk_id=c.get("chunk_id", ""),
                            text=c.get("text", ""),
                            position=c.get("position", 0),
                            word_count=c.get("word_count", 0),
                        )
                    )

            document = plagiarism_pb2.Document(
                document_id=doc.get("document_id", ""),
                title=doc.get("title", ""),
                content=doc.get("content", "") if request.include_content else "",
                metadata=doc.get("metadata", {}),
                language=doc.get("language", ""),
                chunk_count=doc.get("chunk_count", 0),
                chunks=chunks,
                created_at=str(doc.get("created_at", "")),
                updated_at=str(doc.get("updated_at", "")),
            )

            return plagiarism_pb2.GetDocumentResponse(document=document, found=True)

        except Exception as e:
            logger.error(f"GetDocument error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.GetDocumentResponse(found=False)

    def DeleteDocument(
        self,
        request: plagiarism_pb2.DeleteDocumentRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.DeleteDocumentResponse:
        """Delete a document."""
        try:
            success = self.doc_manager.delete_document(request.document_id)

            return plagiarism_pb2.DeleteDocumentResponse(
                success=success,
                message="Document deleted" if success else "Document not found",
            )

        except Exception as e:
            logger.error(f"DeleteDocument error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.DeleteDocumentResponse(
                success=False, message=str(e)
            )

    def SearchDocuments(
        self,
        request: plagiarism_pb2.SearchRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.SearchResponse:
        """Search documents."""
        try:
            filters = dict(request.filters) if request.filters else None
            limit = request.limit if request.limit > 0 else 10
            offset = request.offset if request.offset >= 0 else 0

            docs, total = self.doc_manager.search_documents(
                query=request.query or None,
                filters=filters,
                limit=limit,
                offset=offset,
            )

            documents = []
            for doc in docs:
                documents.append(
                    plagiarism_pb2.DocumentSummary(
                        document_id=doc.get("document_id", ""),
                        title=doc.get("title", ""),
                        metadata=doc.get("metadata", {}),
                        language=doc.get("language", ""),
                        chunk_count=doc.get("chunk_count", 0),
                        created_at=str(doc.get("created_at", "")),
                    )
                )

            return plagiarism_pb2.SearchResponse(documents=documents, total=total)

        except Exception as e:
            logger.error(f"SearchDocuments error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.SearchResponse()

    def HealthCheck(
        self,
        request: plagiarism_pb2.HealthCheckRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.HealthCheckResponse:
        """Check service health."""
        try:
            stats = self.doc_manager.get_stats()

            components = {}

            # Elasticsearch health
            es_health = stats.get("es_health", {})
            components["elasticsearch"] = plagiarism_pb2.ComponentHealth(
                healthy=es_health.get("healthy", False),
                message=es_health.get("status", es_health.get("error", "Unknown")),
            )

            # Ollama health
            ollama_health = stats.get("ollama_health", {})
            components["ollama"] = plagiarism_pb2.ComponentHealth(
                healthy=ollama_health.get("healthy", False),
                message="Available" if ollama_health.get("healthy") else ollama_health.get("error", "Unknown"),
            )

            overall_healthy = all(c.healthy for c in components.values())

            return plagiarism_pb2.HealthCheckResponse(
                healthy=overall_healthy,
                components=components,
            )

        except Exception as e:
            logger.error(f"HealthCheck error: {e}")
            return plagiarism_pb2.HealthCheckResponse(healthy=False)
