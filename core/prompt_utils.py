from typing import List

def split_text_by_words(text: str, max_words: int = 200) -> List[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i:i+max_words]))
    return chunks

def approx_tokens(text: str) -> int:
    # Approximate tokens by words * 1.3 to be conservative
    return int(len(text.split()) * 1.3)
