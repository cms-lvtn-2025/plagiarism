# Plagiarism Detection System - Implementation TODO List

## Phase 1: Setup & Infrastructure

### 1.1 Project Setup
- [ ] Tạo virtual environment (venv)
- [ ] Tạo file `requirements.txt`
- [ ] Tạo cấu trúc thư mục project
- [ ] Tạo file `.env.example` và `config/settings.py`
- [ ] Setup Docker Compose cho Elasticsearch + Ollama

### 1.2 Proto & gRPC Setup
- [ ] Viết file `proto/plagiarism.proto`
- [ ] Tạo script `scripts/generate_proto.sh`
- [ ] Generate gRPC Python code
- [ ] Test gRPC connection cơ bản

## Phase 2: Core Components

### 2.1 Elasticsearch Client
- [ ] Tạo `src/storage/elasticsearch.py`
- [ ] Implement connection pooling
- [ ] Implement index creation với proper mappings
- [ ] Implement CRUD operations (create, read, update, delete)
- [ ] Implement vector search với kNN
- [ ] Viết tests cho ES client

### 2.2 Ollama Integration
- [ ] Tạo `src/embedding/ollama_embed.py`
- [ ] Implement embedding generation
- [ ] Implement batch embedding (nhiều text cùng lúc)
- [ ] Tạo `src/core/analyzer.py` cho AI analysis
- [ ] Implement chat completion cho kết luận cuối
- [ ] Viết tests cho Ollama client

### 2.3 Text Processing
- [ ] Tạo `src/core/chunker.py`
- [ ] Implement text chunking với overlap
- [ ] Implement language detection
- [ ] Implement text normalization (remove special chars, etc.)
- [ ] Viết tests cho chunker

## Phase 3: Business Logic

### 3.1 Plagiarism Detector
- [ ] Tạo `src/core/detector.py`
- [ ] Implement `check_plagiarism()` method
- [ ] Implement similarity calculation
- [ ] Implement threshold checking
- [ ] Implement weighted scoring
- [ ] Implement AI-enhanced analysis
- [ ] Viết tests cho detector

### 3.2 Document Management
- [ ] Implement `upload_document()` - chunk + embed + store
- [ ] Implement `batch_upload()` với progress tracking
- [ ] Implement `get_document()`
- [ ] Implement `delete_document()`
- [ ] Implement `search_documents()` by metadata

## Phase 4: gRPC Service

### 4.1 Service Implementation
- [ ] Tạo `src/services/plagiarism_service.py`
- [ ] Implement `CheckPlagiarism` RPC
- [ ] Implement `UploadDocument` RPC
- [ ] Implement `BatchUpload` RPC (streaming)
- [ ] Implement `GetDocument` RPC
- [ ] Implement `DeleteDocument` RPC
- [ ] Implement proper error handling & status codes

### 4.2 Server Setup
- [ ] Tạo `src/server.py`
- [ ] Setup gRPC server với thread pool
- [ ] Implement graceful shutdown
- [ ] Add logging & monitoring
- [ ] Add health check endpoint

## Phase 5: Testing & Documentation

### 5.1 Testing
- [ ] Unit tests cho tất cả components
- [ ] Integration tests với ES + Ollama
- [ ] End-to-end tests cho gRPC service
- [ ] Performance tests (benchmark)
- [ ] Tạo sample data để test

### 5.2 Documentation
- [ ] Hoàn thiện README.md
- [ ] Viết API documentation (docs/API.md)
- [ ] Viết hướng dẫn deployment
- [ ] Tạo Postman/gRPC collection để test

## Phase 6: Deployment

### 6.1 Containerization
- [ ] Viết Dockerfile cho service
- [ ] Update docker-compose.yml đầy đủ
- [ ] Setup volume mounts cho data persistence
- [ ] Test deployment local

### 6.2 Production Ready
- [ ] Add rate limiting
- [ ] Add authentication (optional)
- [ ] Setup logging rotation
- [ ] Optimize Elasticsearch settings
- [ ] Document production configuration

---

## Estimated Implementation Order

```
Week 1: Phase 1 + Phase 2.1 + 2.2
Week 2: Phase 2.3 + Phase 3
Week 3: Phase 4
Week 4: Phase 5 + Phase 6
```

## Priority Tasks (MVP)

Để có MVP hoạt động được, ưu tiên theo thứ tự:

1. ✅ Architecture document
2. ⬜ Project setup + venv
3. ⬜ Proto file + generate code
4. ⬜ ES client với vector search
5. ⬜ Ollama embedding client
6. ⬜ Text chunker
7. ⬜ Plagiarism detector (basic)
8. ⬜ gRPC service + server
9. ⬜ AI analyzer (enhance kết quả)
10. ⬜ Tests + documentation
