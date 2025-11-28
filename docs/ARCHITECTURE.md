# Plagiarism Detection System - Architecture Document

## 1. Tổng quan hệ thống

Hệ thống phát hiện đạo văn sử dụng kết hợp:
- **Elasticsearch**: Lưu trữ văn bản và vector embedding
- **Ollama**: Tạo embedding vectors và AI kết luận cuối cùng
- **gRPC**: API communication protocol

### 1.1 Flow xử lý

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   Client    │────▶│  gRPC API   │────▶│  Plagiarism     │────▶│ Elasticsearch│
│  (Text)     │     │  Service    │     │  Engine         │     │  (Storage)   │
└─────────────┘     └─────────────┘     └─────────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Ollama    │
                                        │ (Embedding  │
                                        │  + AI)      │
                                        └─────────────┘
```

## 2. Các thành phần chính

### 2.1 gRPC Service
- **CheckPlagiarism**: Kiểm tra 1 đoạn văn bản
- **UploadDocument**: Nạp văn bản vào database
- **BatchUpload**: Nạp nhiều văn bản cùng lúc
- **GetDocument**: Lấy thông tin văn bản
- **DeleteDocument**: Xóa văn bản

### 2.2 Elasticsearch Index
```json
{
  "mappings": {
    "properties": {
      "document_id": { "type": "keyword" },
      "title": { "type": "text" },
      "content": { "type": "text" },
      "chunks": {
        "type": "nested",
        "properties": {
          "chunk_id": { "type": "keyword" },
          "text": { "type": "text" },
          "embedding": {
            "type": "dense_vector",
            "dims": 768,
            "index": true,
            "similarity": "cosine"
          },
          "position": { "type": "integer" }
        }
      },
      "language": { "type": "keyword" },
      "created_at": { "type": "date" },
      "metadata": { "type": "object" }
    }
  }
}
```

### 2.3 Ollama Models
- **Embedding**: `nomic-embed-text` hoặc `mxbai-embed-large` (768 dims)
- **AI Analysis**: `llama3.2` hoặc `qwen2.5` cho kết luận cuối

## 3. Ngưỡng phát hiện đạo văn (Thresholds)

### 3.1 Similarity Levels
| Level | Cosine Similarity | Mô tả |
|-------|-------------------|-------|
| **CRITICAL** | >= 0.95 | Copy nguyên văn, đạo văn nghiêm trọng |
| **HIGH** | 0.85 - 0.94 | Đạo văn cao, paraphrase nhẹ |
| **MEDIUM** | 0.70 - 0.84 | Nghi ngờ đạo văn, paraphrase nhiều |
| **LOW** | 0.50 - 0.69 | Có thể trùng ý tưởng |
| **SAFE** | < 0.50 | An toàn, không đạo văn |

### 3.2 Chunk Configuration
- **Chunk size**: 200-300 từ (tối ưu cho embedding)
- **Overlap**: 50 từ (đảm bảo không mất ngữ cảnh)
- **Min chunk**: 50 từ (bỏ qua đoạn quá ngắn)

### 3.3 Search Configuration
- **Top K results**: 10 (số kết quả tương tự tối đa)
- **Min score threshold**: 0.50 (bỏ qua kết quả dưới ngưỡng)
- **Max results per source**: 3 (tránh bias từ 1 nguồn)

## 4. Tính % đạo văn cuối cùng

### 4.1 Công thức cơ bản
```python
# Bước 1: Tính similarity score cho từng chunk
chunk_scores = [search_similar(chunk) for chunk in chunks]

# Bước 2: Tính weighted average (chunk dài hơn = weight cao hơn)
weighted_score = sum(score * len(chunk) for score, chunk in zip(scores, chunks))
total_weight = sum(len(chunk) for chunk in chunks)
base_percentage = weighted_score / total_weight * 100

# Bước 3: Ollama AI phân tích và điều chỉnh
final_percentage = ollama_analyze(text, matches, base_percentage)
```

### 4.2 Ollama AI Analysis Prompt
```
Bạn là chuyên gia phát hiện đạo văn. Phân tích văn bản sau:

VĂN BẢN GỐC:
{input_text}

CÁC KẾT QUẢ TƯƠNG TỰ TÌM THẤY:
{matched_results}

ĐIỂM TƯƠNG ĐỒNG CƠ BẢN: {base_percentage}%

Hãy đánh giá và đưa ra:
1. Phần trăm đạo văn cuối cùng (0-100%)
2. Mức độ: CRITICAL/HIGH/MEDIUM/LOW/SAFE
3. Giải thích ngắn gọn
4. Các đoạn cụ thể bị nghi ngờ

Trả lời dưới dạng JSON.
```

## 5. Cấu trúc thư mục Project

```
plagiarism/
├── proto/
│   └── plagiarism.proto          # gRPC service definitions
├── src/
│   ├── __init__.py
│   ├── server.py                 # gRPC server entry point
│   ├── services/
│   │   ├── __init__.py
│   │   └── plagiarism_service.py # gRPC service implementation
│   ├── core/
│   │   ├── __init__.py
│   │   ├── detector.py           # Main plagiarism detection logic
│   │   ├── chunker.py            # Text chunking utilities
│   │   └── analyzer.py           # Ollama AI analyzer
│   ├── storage/
│   │   ├── __init__.py
│   │   └── elasticsearch.py      # ES client wrapper
│   ├── embedding/
│   │   ├── __init__.py
│   │   └── ollama_embed.py       # Ollama embedding client
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic models
│   └── config/
│       ├── __init__.py
│       └── settings.py           # Configuration
├── tests/
│   ├── __init__.py
│   ├── test_detector.py
│   ├── test_chunker.py
│   └── test_service.py
├── scripts/
│   ├── setup_es.py               # Setup Elasticsearch index
│   └── generate_proto.sh         # Generate gRPC code
├── docs/
│   ├── ARCHITECTURE.md           # This file
│   └── API.md                    # API documentation
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 6. Dependencies

### 6.1 Python Packages
```
grpcio>=1.60.0
grpcio-tools>=1.60.0
elasticsearch>=8.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
httpx>=0.25.0          # Ollama HTTP client
tiktoken>=0.5.0        # Token counting
langdetect>=1.0.9      # Language detection
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

### 6.2 External Services
- Elasticsearch 8.x
- Ollama (local hoặc remote)

## 7. Environment Variables

```env
# Elasticsearch
ES_HOST=localhost
ES_PORT=9200
ES_INDEX=plagiarism_documents
ES_USER=elastic
ES_PASSWORD=changeme

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2

# Service
GRPC_PORT=50051
LOG_LEVEL=INFO

# Thresholds
SIMILARITY_CRITICAL=0.95
SIMILARITY_HIGH=0.85
SIMILARITY_MEDIUM=0.70
SIMILARITY_LOW=0.50
CHUNK_SIZE=250
CHUNK_OVERLAP=50
TOP_K_RESULTS=10
```

## 8. API Response Format

### 8.1 CheckPlagiarism Response
```json
{
  "request_id": "uuid-string",
  "input_text": "...",
  "result": {
    "plagiarism_percentage": 75.5,
    "severity": "HIGH",
    "explanation": "Phát hiện 3 đoạn văn tương tự cao với tài liệu trong database",
    "matches": [
      {
        "document_id": "doc-123",
        "document_title": "Luận văn ABC",
        "matched_chunk": "...",
        "similarity_score": 0.92,
        "position": {
          "start": 0,
          "end": 250
        }
      }
    ],
    "chunk_analysis": [
      {
        "chunk_index": 0,
        "text": "...",
        "max_similarity": 0.92,
        "status": "HIGH"
      }
    ]
  },
  "metadata": {
    "processing_time_ms": 1234,
    "chunks_analyzed": 5,
    "documents_searched": 1000
  }
}
```
