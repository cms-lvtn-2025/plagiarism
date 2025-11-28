"""Ollama embedding client for generating text embeddings."""

import logging
from typing import Optional

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingClient:
    """Client for generating embeddings using Ollama."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ollama_host
        self.model = self.settings.ollama_embed_model
        self.timeout = self.settings.ollama_timeout
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    def health_check(self) -> dict:
        """Check Ollama service health."""
        try:
            response = self.client.get("/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                has_embed_model = any(
                    self.model in name for name in model_names
                )
                return {
                    "healthy": True,
                    "models": model_names,
                    "embed_model_available": has_embed_model,
                }
            return {"healthy": False, "error": f"Status: {response.status_code}"}
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return {"healthy": False, "error": str(e)}

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.client.post(
                "/api/embed",
                json={
                    "model": self.model,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Ollama returns embeddings in different formats
            if "embeddings" in data:
                # New format: {"embeddings": [[...]]}
                return data["embeddings"][0]
            elif "embedding" in data:
                # Old format: {"embedding": [...]}
                return data["embedding"]
            else:
                raise ValueError(f"Unexpected response format: {data.keys()}")

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Process in batches to avoid timeout
        batch_size = self.settings.embedding_batch_size
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                response = self.client.post(
                    "/api/embed",
                    json={
                        "model": self.model,
                        "input": batch,
                    },
                )
                response.raise_for_status()
                data = response.json()

                if "embeddings" in data:
                    all_embeddings.extend(data["embeddings"])
                elif "embedding" in data:
                    # Single embedding returned
                    all_embeddings.append(data["embedding"])
                else:
                    raise ValueError(f"Unexpected response format: {data.keys()}")

            except httpx.HTTPStatusError as e:
                logger.error(f"Batch embedding failed: {e.response.text}")
                # Fall back to individual embedding
                for text in batch:
                    all_embeddings.append(self.embed(text))

        return all_embeddings

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


# Singleton instance
_ollama_client: Optional[OllamaEmbeddingClient] = None


def get_ollama_client() -> OllamaEmbeddingClient:
    """Get singleton Ollama client instance."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaEmbeddingClient()
    return _ollama_client
