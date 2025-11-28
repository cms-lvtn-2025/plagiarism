"""AI Analyzer using Ollama for plagiarism analysis."""

import json
import logging
from typing import Optional
from dataclasses import dataclass

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result from AI analysis."""

    plagiarism_percentage: float
    severity: str
    explanation: str
    suspicious_segments: list[dict]
    confidence: float


class OllamaAnalyzer:
    """AI analyzer using Ollama chat model for plagiarism analysis."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ollama_host
        self.model = self.settings.ollama_chat_model
        self.timeout = self.settings.ollama_timeout
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout * 2),  # Longer timeout for chat
            )
        return self._client

    def analyze(
        self,
        input_text: str,
        matches: list[dict],
        base_percentage: float,
    ) -> AnalysisResult:
        """Analyze plagiarism using AI.

        Args:
            input_text: The text being checked
            matches: List of matched results from vector search
            base_percentage: Base plagiarism percentage from similarity scores

        Returns:
            AnalysisResult with AI-enhanced analysis
        """
        # Format matches for prompt
        matches_text = self._format_matches(matches)

        prompt = self._build_prompt(input_text, matches_text, base_percentage)

        try:
            response = self.client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistency
                        "num_predict": 1024,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            # Parse JSON response
            result_text = data.get("response", "{}")
            return self._parse_response(result_text, base_percentage)

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.text}")
            return self._fallback_result(base_percentage)
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._fallback_result(base_percentage)

    def _format_matches(self, matches: list[dict]) -> str:
        """Format matches for the prompt."""
        if not matches:
            return "Không tìm thấy kết quả tương tự."

        formatted = []
        for i, match in enumerate(matches[:5], 1):  # Limit to top 5
            formatted.append(
                f"""
Kết quả {i}:
- Nguồn: {match.get('document_title', 'Unknown')}
- Độ tương đồng: {match.get('similarity_score', 0):.1%}
- Nội dung trùng khớp:
\"\"\"{match.get('matched_text', '')[:500]}\"\"\"
"""
            )
        return "\n".join(formatted)

    def _build_prompt(
        self, input_text: str, matches_text: str, base_percentage: float
    ) -> str:
        """Build the analysis prompt."""
        # Truncate input text if too long
        truncated_input = input_text[:2000] + "..." if len(input_text) > 2000 else input_text

        return f"""Bạn là chuyên gia phát hiện đạo văn. Phân tích văn bản sau và đưa ra đánh giá.

VĂN BẢN CẦN KIỂM TRA:
\"\"\"{truncated_input}\"\"\"

CÁC KẾT QUẢ TƯƠNG TỰ TÌM THẤY:
{matches_text}

ĐIỂM TƯƠNG ĐỒNG CƠ BẢN: {base_percentage:.1f}%

Hãy phân tích và trả lời theo format JSON sau:
{{
    "plagiarism_percentage": <số từ 0-100>,
    "severity": "<SAFE|LOW|MEDIUM|HIGH|CRITICAL>",
    "explanation": "<giải thích ngắn gọn bằng tiếng Việt>",
    "suspicious_segments": [
        {{
            "text": "<đoạn văn bị nghi ngờ>",
            "reason": "<lý do nghi ngờ>"
        }}
    ],
    "confidence": <độ tin cậy từ 0-1>
}}

Lưu ý:
- CRITICAL (>=95%): Copy nguyên văn, đạo văn nghiêm trọng
- HIGH (85-94%): Đạo văn cao, paraphrase nhẹ
- MEDIUM (70-84%): Nghi ngờ đạo văn, paraphrase nhiều
- LOW (50-69%): Có thể trùng ý tưởng
- SAFE (<50%): An toàn, không đạo văn

Chỉ trả về JSON, không có text khác."""

    def _parse_response(
        self, response_text: str, base_percentage: float
    ) -> AnalysisResult:
        """Parse AI response to AnalysisResult."""
        try:
            # Clean response text
            response_text = response_text.strip()

            # Try to parse JSON
            data = json.loads(response_text)

            return AnalysisResult(
                plagiarism_percentage=float(data.get("plagiarism_percentage", base_percentage)),
                severity=data.get("severity", self._get_severity(base_percentage)),
                explanation=data.get("explanation", "Không có phân tích chi tiết."),
                suspicious_segments=data.get("suspicious_segments", []),
                confidence=float(data.get("confidence", 0.8)),
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return self._fallback_result(base_percentage)

    def _fallback_result(self, base_percentage: float) -> AnalysisResult:
        """Generate fallback result when AI analysis fails."""
        return AnalysisResult(
            plagiarism_percentage=base_percentage,
            severity=self._get_severity(base_percentage),
            explanation="Phân tích dựa trên độ tương đồng vector. AI analysis không khả dụng.",
            suspicious_segments=[],
            confidence=0.6,
        )

    def _get_severity(self, percentage: float) -> str:
        """Get severity level from percentage."""
        if percentage >= 95:
            return "CRITICAL"
        elif percentage >= 85:
            return "HIGH"
        elif percentage >= 70:
            return "MEDIUM"
        elif percentage >= 50:
            return "LOW"
        return "SAFE"

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


# Singleton instance
_analyzer: Optional[OllamaAnalyzer] = None


def get_analyzer() -> OllamaAnalyzer:
    """Get singleton analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = OllamaAnalyzer()
    return _analyzer
