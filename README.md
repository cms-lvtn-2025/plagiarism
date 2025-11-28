# Plagiarism Detection System

Hệ thống phát hiện đạo văn sử dụng Elasticsearch, Ollama AI và gRPC.

## Tính năng

- **Check đạo văn**: Kiểm tra văn bản có trùng lặp với database không
- **Vector Search**: Sử dụng embedding để tìm kiếm ngữ nghĩa
- **AI Analysis**: Ollama AI phân tích và đưa ra kết luận cuối cùng
- **gRPC API**: High-performance API communication
- **Đa ngôn ngữ**: Hỗ trợ Tiếng Việt và Tiếng Anh

## Tech Stack

- **Python 3.10+**
- **gRPC**: API protocol
- **Elasticsearch 8.x**: Vector storage & search
- **Ollama**: Embedding + AI analysis
  - Embedding: `nomic-embed-text` / `mxbai-embed-large`
  - Chat: `llama3.2` / `qwen2.5`

## Quick Start

### 1. Prerequisites

```bash
# Install Docker & Docker Compose
# Install Python 3.10+
# Install Ollama: https://ollama.ai
```

### 2. Setup Ollama Models

```bash
# Pull embedding model
ollama pull nomic-embed-text

# Pull chat model for analysis
ollama pull llama3.2
```

### 3. Start Services

```bash
# Start Elasticsearch
docker-compose up -d elasticsearch

# Wait for ES to be ready
curl -X GET "localhost:9200/_cluster/health?wait_for_status=yellow"
```

### 4. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
```

### 6. Generate gRPC Code

```bash
./scripts/generate_proto.sh
```

### 7. Setup Elasticsearch Index

```bash
python scripts/setup_es.py
```

### 8. Start Server

```bash
python -m src.server
```

## Usage

### Upload Document

```python
import grpc
from proto import plagiarism_pb2, plagiarism_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = plagiarism_pb2_grpc.PlagiarismServiceStub(channel)

# Upload a document
response = stub.UploadDocument(plagiarism_pb2.UploadRequest(
    title="My Document",
    content="This is the document content...",
    metadata={"author": "John Doe", "year": "2024"}
))
print(f"Document ID: {response.document_id}")
```

### Check Plagiarism

```python
# Check for plagiarism
response = stub.CheckPlagiarism(plagiarism_pb2.CheckRequest(
    text="Text to check for plagiarism..."
))

print(f"Plagiarism: {response.plagiarism_percentage}%")
print(f"Severity: {response.severity}")
print(f"Explanation: {response.explanation}")

for match in response.matches:
    print(f"  - {match.document_title}: {match.similarity_score:.2%}")
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ES_HOST` | localhost | Elasticsearch host |
| `ES_PORT` | 9200 | Elasticsearch port |
| `OLLAMA_HOST` | http://localhost:11434 | Ollama API URL |
| `OLLAMA_EMBED_MODEL` | nomic-embed-text | Embedding model |
| `OLLAMA_CHAT_MODEL` | llama3.2 | Chat model for analysis |
| `GRPC_PORT` | 50051 | gRPC server port |
| `CHUNK_SIZE` | 250 | Words per chunk |
| `CHUNK_OVERLAP` | 50 | Overlap between chunks |

## Plagiarism Thresholds

| Level | Similarity | Description |
|-------|------------|-------------|
| CRITICAL | >= 95% | Copy nguyên văn |
| HIGH | 85-94% | Paraphrase nhẹ |
| MEDIUM | 70-84% | Nghi ngờ đạo văn |
| LOW | 50-69% | Có thể trùng ý |
| SAFE | < 50% | An toàn |

## Project Structure

```
plagiarism/
├── proto/                  # gRPC definitions
├── src/
│   ├── services/          # gRPC service implementation
│   ├── core/              # Business logic
│   ├── storage/           # Elasticsearch client
│   ├── embedding/         # Ollama embedding
│   ├── models/            # Data models
│   └── config/            # Configuration
├── tests/                 # Unit & integration tests
├── scripts/               # Setup scripts
└── docs/                  # Documentation
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design & details
- [TODO](docs/TODO.md) - Implementation tasks
- [API](docs/API.md) - API reference

## Development

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Format code
black src/ tests/

# Lint
flake8 src/ tests/
```

## License

MIT License
