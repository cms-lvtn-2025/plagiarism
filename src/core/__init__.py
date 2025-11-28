# Core business logic
from .chunker import TextChunker, TextChunk, get_chunker
from .analyzer import OllamaAnalyzer, AnalysisResult, get_analyzer
from .detector import PlagiarismDetector, PlagiarismResult, get_detector
from .document_manager import DocumentManager, UploadResult, get_document_manager

__all__ = [
    "TextChunker",
    "TextChunk",
    "get_chunker",
    "OllamaAnalyzer",
    "AnalysisResult",
    "get_analyzer",
    "PlagiarismDetector",
    "PlagiarismResult",
    "get_detector",
    "DocumentManager",
    "UploadResult",
    "get_document_manager",
]
