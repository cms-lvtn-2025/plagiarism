# Hướng dẫn sử dụng Postman với gRPC

## Cài đặt

### 1. Tải Postman Desktop
- Tải từ: https://www.postman.com/downloads/
- **Lưu ý**: Phiên bản Web không hỗ trợ gRPC, phải dùng Desktop App

### 2. Import Proto file

1. Mở Postman Desktop
2. Click **New** → **gRPC Request**
3. Trong tab **Service definition**:
   - Chọn **Import .proto file**
   - Chọn file: `proto/plagiarism.proto`
4. Click **Next** → **Import as API**

---

## Kết nối Server

**Server URL**: `localhost:50051`

(Không có `http://` hoặc `grpc://`, chỉ cần `host:port`)

---

## Các API Methods

### 1. HealthCheck - Kiểm tra trạng thái

```
Method: plagiarism.PlagiarismService/HealthCheck
```

**Request** (để trống):
```json
{}
```

**Response**:
```json
{
    "healthy": true,
    "components": {
        "elasticsearch": {
            "healthy": true,
            "message": "yellow"
        },
        "ollama": {
            "healthy": true,
            "message": "Available"
        }
    }
}
```

---

### 2. UploadDocument - Upload tài liệu

```
Method: plagiarism.PlagiarismService/UploadDocument
```

**Request**:
```json
{
    "title": "Luận văn về Machine Learning",
    "content": "Machine Learning là một nhánh của trí tuệ nhân tạo, cho phép máy tính học từ dữ liệu mà không cần được lập trình một cách rõ ràng. Các thuật toán Machine Learning xây dựng mô hình dựa trên dữ liệu mẫu, được gọi là dữ liệu huấn luyện, để đưa ra dự đoán hoặc quyết định.",
    "metadata": {
        "author": "Nguyen Van A",
        "year": "2024",
        "university": "HCMUT"
    },
    "language": "vi"
}
```

**Response**:
```json
{
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Luận văn về Machine Learning",
    "chunks_created": 1,
    "message": "Successfully uploaded with 1 chunks",
    "success": true
}
```

---

### 3. CheckPlagiarism - Kiểm tra đạo văn

```
Method: plagiarism.PlagiarismService/CheckPlagiarism
```

**Request đơn giản**:
```json
{
    "text": "Machine Learning là một nhánh của trí tuệ nhân tạo, cho phép máy tính học từ dữ liệu."
}
```

**Request với options**:
```json
{
    "text": "Machine Learning là một nhánh của trí tuệ nhân tạo, cho phép máy tính học từ dữ liệu.",
    "options": {
        "min_similarity": 0.5,
        "top_k": 10,
        "exclude_docs": []
    }
}
```

**Response**:
```json
{
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "plagiarism_percentage": 95.5,
    "severity": "CRITICAL",
    "explanation": "Phát hiện đạo văn nghiêm trọng. Tìm thấy 3 đoạn trùng khớp cao với tài liệu trong database.",
    "matches": [
        {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "document_title": "Luận văn về Machine Learning",
            "matched_text": "Machine Learning là một nhánh của trí tuệ nhân tạo...",
            "input_text": "Machine Learning là một nhánh của trí tuệ nhân tạo...",
            "similarity_score": 0.955,
            "position": {
                "start": 0,
                "end": 150,
                "chunk_index": 0
            }
        }
    ],
    "chunks": [
        {
            "chunk_index": 0,
            "text": "Machine Learning là một nhánh...",
            "max_similarity": 0.955,
            "status": "CRITICAL",
            "best_match_doc_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    ],
    "metadata": {
        "processing_time_ms": 1234,
        "chunks_analyzed": 1,
        "documents_searched": 100
    }
}
```

#### Severity values:
| Value | Ý nghĩa | Phần trăm |
|-------|---------|-----------|
| `SAFE` | An toàn | < 50% |
| `LOW` | Thấp | 50-69% |
| `MEDIUM` | Trung bình | 70-84% |
| `HIGH` | Cao | 85-94% |
| `CRITICAL` | Nghiêm trọng | >= 95% |

---

### 4. GetDocument - Lấy thông tin tài liệu

```
Method: plagiarism.PlagiarismService/GetDocument
```

**Request cơ bản**:
```json
{
    "document_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Request đầy đủ**:
```json
{
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "include_content": true,
    "include_chunks": true
}
```

**Response**:
```json
{
    "document": {
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Luận văn về Machine Learning",
        "content": "Machine Learning là...",
        "metadata": {
            "author": "Nguyen Van A",
            "year": "2024"
        },
        "language": "vi",
        "chunk_count": 1,
        "chunks": [
            {
                "chunk_id": "550e8400..._chunk_0",
                "text": "Machine Learning là...",
                "position": 0,
                "word_count": 50
            }
        ],
        "created_at": "2024-01-15T10:30:00Z"
    },
    "found": true
}
```

---

### 5. DeleteDocument - Xóa tài liệu

```
Method: plagiarism.PlagiarismService/DeleteDocument
```

**Request**:
```json
{
    "document_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response**:
```json
{
    "success": true,
    "message": "Document deleted"
}
```

---

### 6. SearchDocuments - Tìm kiếm tài liệu

```
Method: plagiarism.PlagiarismService/SearchDocuments
```

**Tìm theo từ khóa**:
```json
{
    "query": "Machine Learning",
    "limit": 10,
    "offset": 0
}
```

**Tìm theo metadata**:
```json
{
    "filters": {
        "author": "Nguyen Van A",
        "year": "2024"
    },
    "limit": 20
}
```

**Response**:
```json
{
    "documents": [
        {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Luận văn về Machine Learning",
            "metadata": {
                "author": "Nguyen Van A"
            },
            "language": "vi",
            "chunk_count": 1,
            "created_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total": 1
}
```

---

## Postman Collection

### Import Collection

Tạo file `plagiarism.postman_collection.json` và import vào Postman:

```json
{
    "info": {
        "name": "Plagiarism Detection API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "Health Check",
            "request": {
                "method": "POST",
                "header": [],
                "body": {
                    "mode": "raw",
                    "raw": "{}"
                },
                "url": {
                    "raw": "grpc://localhost:50051/plagiarism.PlagiarismService/HealthCheck",
                    "protocol": "grpc",
                    "host": ["localhost"],
                    "port": "50051",
                    "path": ["plagiarism.PlagiarismService", "HealthCheck"]
                }
            }
        }
    ]
}
```

---

## Sử dụng grpcurl (Command Line)

Nếu không muốn dùng Postman, có thể dùng `grpcurl`:

### Cài đặt
```bash
# macOS
brew install grpcurl

# Linux
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
```

### Các lệnh

```bash
# Health Check
grpcurl -plaintext -import-path ./proto -proto plagiarism.proto \
    localhost:50051 plagiarism.PlagiarismService/HealthCheck

# Upload Document
grpcurl -plaintext -import-path ./proto -proto plagiarism.proto \
    -d '{"title": "Test Doc", "content": "Test content here", "language": "vi"}' \
    localhost:50051 plagiarism.PlagiarismService/UploadDocument

# Check Plagiarism
grpcurl -plaintext -import-path ./proto -proto plagiarism.proto \
    -d '{"text": "Machine Learning là trí tuệ nhân tạo"}' \
    localhost:50051 plagiarism.PlagiarismService/CheckPlagiarism

# Search Documents
grpcurl -plaintext -import-path ./proto -proto plagiarism.proto \
    -d '{"query": "Machine Learning", "limit": 10}' \
    localhost:50051 plagiarism.PlagiarismService/SearchDocuments

# Get Document
grpcurl -plaintext -import-path ./proto -proto plagiarism.proto \
    -d '{"document_id": "YOUR_DOC_ID", "include_content": true}' \
    localhost:50051 plagiarism.PlagiarismService/GetDocument

# Delete Document
grpcurl -plaintext -import-path ./proto -proto plagiarism.proto \
    -d '{"document_id": "YOUR_DOC_ID"}' \
    localhost:50051 plagiarism.PlagiarismService/DeleteDocument
```

---

## Lưu ý

1. **Timeout**: CheckPlagiarism có thể mất 1-5 phút nếu bật AI analysis
2. **Server**: Đảm bảo server đang chạy trước khi test
3. **Proto file**: Cần import proto file vào Postman để sử dụng gRPC
