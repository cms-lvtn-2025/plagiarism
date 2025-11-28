"""gRPC Server for Plagiarism Detection Service."""

import logging
import signal
import sys
from concurrent import futures

import grpc

from src import plagiarism_pb2_grpc
from src.config import get_settings
from src.services.plagiarism_service import PlagiarismServicer
from src.storage import get_es_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PlagiarismServer:
    """gRPC server for plagiarism detection."""

    def __init__(self):
        self.settings = get_settings()
        self.server = None
        self._shutdown_event = False

    def setup_elasticsearch(self) -> bool:
        """Setup Elasticsearch index."""
        try:
            es_client = get_es_client()

            # Check connection
            health = es_client.health_check()
            if not health.get("healthy"):
                logger.error(f"Elasticsearch not healthy: {health}")
                return False

            logger.info(f"Connected to Elasticsearch: {health.get('cluster_name')}")

            # Create index if not exists
            es_client.create_index(force=False)
            logger.info(f"Elasticsearch index ready: {self.settings.es_index}")

            return True
        except Exception as e:
            logger.error(f"Failed to setup Elasticsearch: {e}")
            return False

    def start(self):
        """Start the gRPC server."""
        # Setup Elasticsearch
        if not self.setup_elasticsearch():
            logger.warning("Elasticsearch setup failed, continuing anyway...")

        # Create gRPC server
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=self.settings.grpc_max_workers),
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
            ],
        )

        # Add servicer
        plagiarism_pb2_grpc.add_PlagiarismServiceServicer_to_server(
            PlagiarismServicer(), self.server
        )

        # Bind to address
        address = f"{self.settings.grpc_host}:{self.settings.grpc_port}"
        self.server.add_insecure_port(address)

        # Start server
        self.server.start()
        logger.info(f"Plagiarism Detection Service started on {address}")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Wait for shutdown
        try:
            self.server.wait_for_termination()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the gRPC server gracefully."""
        if self.server and not self._shutdown_event:
            self._shutdown_event = True
            logger.info("Shutting down server...")

            # Grace period for ongoing requests
            self.server.stop(grace=5)

            # Close connections
            get_es_client().close()

            logger.info("Server stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)


def main():
    """Main entry point."""
    settings = get_settings()

    # Update log level
    logging.getLogger().setLevel(settings.log_level)

    logger.info("=" * 50)
    logger.info("Plagiarism Detection Service")
    logger.info("=" * 50)
    logger.info(f"Elasticsearch: {settings.es_url}")
    logger.info(f"Ollama: {settings.ollama_host}")
    logger.info(f"gRPC Port: {settings.grpc_port}")
    logger.info("=" * 50)

    server = PlagiarismServer()
    server.start()


if __name__ == "__main__":
    main()
