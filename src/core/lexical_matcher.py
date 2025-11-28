"""Lexical matching utilities to reduce false positives."""

import re
from typing import Optional
from difflib import SequenceMatcher


def calculate_lexical_similarity(text1: str, text2: str) -> float:
    """Calculate lexical similarity using multiple methods.

    Returns a score between 0 and 1.
    """
    # Normalize texts
    text1 = normalize_for_comparison(text1)
    text2 = normalize_for_comparison(text2)

    if not text1 or not text2:
        return 0.0

    # Method 1: Jaccard similarity (word overlap)
    jaccard = jaccard_similarity(text1, text2)

    # Method 2: Sequence matcher (longest common subsequence ratio)
    sequence = SequenceMatcher(None, text1, text2).ratio()

    # Method 3: N-gram overlap (bigrams)
    ngram = ngram_similarity(text1, text2, n=2)

    # Weighted average
    return (jaccard * 0.3) + (sequence * 0.4) + (ngram * 0.3)


def normalize_for_comparison(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""

    # Lowercase
    text = text.lower()

    # Remove citations like (Nguyen, 2024), (Phát và đtg, 2024)
    text = re.sub(r'\([^)]*\d{4}[^)]*\)', '', text)

    # Remove special characters, keep only letters and spaces
    text = re.sub(r'[^\w\s]', ' ', text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity based on word sets."""
    words1 = set(text1.split())
    words2 = set(text2.split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def ngram_similarity(text1: str, text2: str, n: int = 2) -> float:
    """Calculate n-gram overlap similarity."""
    def get_ngrams(text: str, n: int) -> set:
        words = text.split()
        if len(words) < n:
            return set()
        return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))

    ngrams1 = get_ngrams(text1, n)
    ngrams2 = get_ngrams(text2, n)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = ngrams1 & ngrams2
    union = ngrams1 | ngrams2

    return len(intersection) / len(union)


def has_citation(text: str) -> bool:
    """Check if text contains citations."""
    # Common citation patterns
    patterns = [
        r'\([^)]*\d{4}[^)]*\)',  # (Author, 2024)
        r'\[[\d,\s]+\]',         # [1], [1, 2]
        r'Nguồn:',               # Nguồn:
        r'theo\s+\w+',           # theo Nguyen
        r'và\s+đtg',             # và đtg (và đồng tác giả)
        r'et\s+al',              # et al
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def calculate_combined_similarity(
    semantic_score: float,
    input_text: str,
    matched_text: str,
    semantic_weight: float = 0.4,
    lexical_weight: float = 0.6,
) -> tuple[float, dict]:
    """Calculate combined similarity score.

    Args:
        semantic_score: Cosine similarity from embedding (0-1)
        input_text: Original input text
        matched_text: Matched text from database
        semantic_weight: Weight for semantic score
        lexical_weight: Weight for lexical score

    Returns:
        Tuple of (combined_score, details_dict)
    """
    lexical_score = calculate_lexical_similarity(input_text, matched_text)

    # If input has citation, reduce the score
    citation_penalty = 0.0
    if has_citation(input_text):
        citation_penalty = 0.15  # Reduce 15% if properly cited

    combined = (semantic_score * semantic_weight) + (lexical_score * lexical_weight)
    combined = max(0, combined - citation_penalty)

    details = {
        "semantic_score": semantic_score,
        "lexical_score": lexical_score,
        "combined_score": combined,
        "has_citation": has_citation(input_text),
        "citation_penalty": citation_penalty,
    }

    return combined, details


# Quick test
if __name__ == "__main__":
    input_text = """Ba trụ cột chính gồm: hiệu quả của công tác khuyến nông,
    mạng lưới trao đổi thông tin và ý thức vệ sinh thực phẩm đã được xác định
    là những động lực mạnh mẽ nhất (Nguồn: Phát và đtg, 2024)"""

    matched_text = """chín vàng, căng mọng, tỏa hương thơm đặc trưng,
    tạo nên nét đặc sắc riêng cho vùng đất này. Nhờ điều kiện tự nhiên
    thuận lợi cùng kinh nghiệm canh tác lâu đời của người dân địa phương,
    xoài Cát Hòa Lộc đã trở thành một trong những loại trái cây đặc sản"""

    semantic = 0.956  # From your result

    combined, details = calculate_combined_similarity(semantic, input_text, matched_text)

    print(f"Semantic score: {details['semantic_score']:.2%}")
    print(f"Lexical score: {details['lexical_score']:.2%}")
    print(f"Has citation: {details['has_citation']}")
    print(f"Citation penalty: {details['citation_penalty']:.2%}")
    print(f"Combined score: {details['combined_score']:.2%}")
