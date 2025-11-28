#!/usr/bin/env python3
"""Test client for Plagiarism Detection Service."""

import sys
sys.path.insert(0, ".")

import grpc
from src import plagiarism_pb2, plagiarism_pb2_grpc


def get_stub():
    """Get gRPC stub."""
    channel = grpc.insecure_channel("localhost:50051")
    return plagiarism_pb2_grpc.PlagiarismServiceStub(channel)


def test_health_check():
    """Test health check."""
    print("=" * 50)
    print("TEST: Health Check")
    print("=" * 50)

    stub = get_stub()
    response = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest())

    print(f"Healthy: {response.healthy}")
    for name, health in response.components.items():
        print(f"  - {name}: {'✅' if health.healthy else '❌'} {health.message}")

    return response.healthy


def test_upload_documents():
    """Test uploading documents."""
    print("\n" + "=" * 50)
    print("TEST: Upload Documents")
    print("=" * 50)

    stub = get_stub()

    # Sample documents
    documents = [
        {
            "title": "Luận văn về Machine Learning",
            "content": """
            Machine Learning là một nhánh của trí tuệ nhân tạo, cho phép máy tính học từ dữ liệu
            mà không cần được lập trình một cách rõ ràng. Các thuật toán Machine Learning xây dựng
            mô hình dựa trên dữ liệu mẫu, được gọi là dữ liệu huấn luyện, để đưa ra dự đoán hoặc
            quyết định mà không cần được lập trình cụ thể để thực hiện nhiệm vụ đó.

            Deep Learning là một phương pháp trong Machine Learning sử dụng mạng nơ-ron nhân tạo
            với nhiều lớp ẩn. Các mạng nơ-ron sâu này có khả năng học các biểu diễn dữ liệu phức tạp
            và đã đạt được kết quả vượt trội trong nhiều tác vụ như nhận dạng hình ảnh, xử lý ngôn ngữ
            tự nhiên và chơi game.
            """,
            "metadata": {"author": "Nguyen Van A", "year": "2024", "subject": "AI"},
        },
        {
            "title": "Nghiên cứu về Natural Language Processing",
            "content": """
            Xử lý ngôn ngữ tự nhiên (NLP) là một lĩnh vực của khoa học máy tính và trí tuệ nhân tạo
            liên quan đến sự tương tác giữa máy tính và ngôn ngữ của con người. NLP giúp máy tính
            hiểu, diễn giải và tạo ra ngôn ngữ tự nhiên một cách có ý nghĩa.

            Các ứng dụng phổ biến của NLP bao gồm: dịch máy, phân tích cảm xúc, chatbot, tóm tắt văn bản,
            và nhận dạng thực thể có tên. Với sự phát triển của các mô hình ngôn ngữ lớn như GPT và BERT,
            NLP đã có những bước tiến vượt bậc trong những năm gần đây.
            """,
            "metadata": {"author": "Tran Thi B", "year": "2024", "subject": "NLP"},
        },
        {
            "title": "Bài viết về Elasticsearch",
            "content": """
            Elasticsearch là một công cụ tìm kiếm và phân tích phân tán, mã nguồn mở được xây dựng
            trên Apache Lucene. Elasticsearch cho phép lưu trữ, tìm kiếm và phân tích khối lượng lớn
            dữ liệu một cách nhanh chóng và gần như theo thời gian thực.

            Elasticsearch hỗ trợ tìm kiếm vector (vector search) cho phép tìm kiếm dựa trên độ tương đồng
            ngữ nghĩa. Điều này rất hữu ích cho các ứng dụng như tìm kiếm ngữ nghĩa, hệ thống đề xuất,
            và phát hiện đạo văn. Vector search sử dụng các thuật toán như kNN để tìm các vector gần nhất.
            """,
            "metadata": {"author": "Le Van C", "year": "2024", "subject": "Database"},
        },
    ]

    uploaded_ids = []
    for doc in documents:
        response = stub.UploadDocument(
            plagiarism_pb2.UploadRequest(
                title=doc["title"],
                content=doc["content"],
                metadata=doc["metadata"],
                language="vi",
            )
        )

        status = "✅" if response.success else "❌"
        print(f"{status} {response.title}")
        print(f"   ID: {response.document_id}")
        print(f"   Chunks: {response.chunks_created}")
        print(f"   Message: {response.message}")

        if response.success:
            uploaded_ids.append(response.document_id)

    return uploaded_ids


def test_check_plagiarism():
    """Test plagiarism checking."""
    print("\n" + "=" * 50)
    print("TEST: Check Plagiarism")
    print("=" * 50)

    stub = get_stub()

    # Test cases
    test_cases = [
        {
            "name": "Copy nguyên văn (CRITICAL)",
            "text": """
            Machine Learning là một nhánh của trí tuệ nhân tạo, cho phép máy tính học từ dữ liệu
            mà không cần được lập trình một cách rõ ràng. Các thuật toán Machine Learning xây dựng
            mô hình dựa trên dữ liệu mẫu, được gọi là dữ liệu huấn luyện.
            """,
        },
        {
            "name": "Paraphrase nhẹ (HIGH/MEDIUM)",
            "text": """
            Học máy là một phân ngành của AI, giúp computer có thể học hỏi từ data
            mà không cần lập trình cụ thể. Các algorithm ML tạo model từ training data
            để đưa ra các prediction hoặc decision.
            """,
        },
        {
            "name": "Nội dung mới (SAFE)",
            "text": """
            Blockchain là một công nghệ sổ cái phân tán, cho phép lưu trữ dữ liệu một cách
            an toàn và minh bạch. Bitcoin là ứng dụng đầu tiên và nổi tiếng nhất của blockchain.
            Smart contract trên Ethereum mở ra nhiều khả năng mới cho các ứng dụng phi tập trung.
            """,
        },
    ]

    for case in test_cases:
        print(f"\n📝 {case['name']}")
        print("-" * 40)

        response = stub.CheckPlagiarism(
            plagiarism_pb2.CheckRequest(
                text=case["text"],
            )
        )

        severity_icons = {
            0: "🟢 SAFE",
            1: "🟡 LOW",
            2: "🟠 MEDIUM",
            3: "🔴 HIGH",
            4: "⛔ CRITICAL",
        }

        print(f"Plagiarism: {response.plagiarism_percentage:.1f}%")
        print(f"Severity: {severity_icons.get(response.severity, 'UNKNOWN')}")
        print(f"Explanation: {response.explanation[:200]}...")

        if response.matches:
            print(f"Matches found: {len(response.matches)}")
            for i, match in enumerate(response.matches[:3], 1):
                print(f"  {i}. {match.document_title} ({match.similarity_score:.1%})")

        print(f"Processing time: {response.metadata.processing_time_ms}ms")


def test_search_documents():
    """Test document search."""
    print("\n" + "=" * 50)
    print("TEST: Search Documents")
    print("=" * 50)

    stub = get_stub()

    response = stub.SearchDocuments(
        plagiarism_pb2.SearchRequest(
            query="Machine Learning",
            limit=10,
        )
    )

    print(f"Found: {response.total} documents")
    for doc in response.documents:
        print(f"  - {doc.title} ({doc.chunk_count} chunks)")


def main():
    """Run all tests."""
    print("\n🚀 PLAGIARISM DETECTION SERVICE - TEST CLIENT\n")

    # Test 1: Health check
    if not test_health_check():
        print("❌ Service not healthy, aborting tests")
        return

    # Test 2: Upload documents
    uploaded_ids = test_upload_documents()

    if not uploaded_ids:
        print("❌ No documents uploaded, aborting tests")
        return

    # Test 3: Search documents
    test_search_documents()

    # Test 4: Check plagiarism
    test_check_plagiarism()

    print("\n" + "=" * 50)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 50)


if __name__ == "__main__":
    main()
