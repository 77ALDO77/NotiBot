import re


def split_text_into_chunks(text: str, max_words: int = 350) -> list[dict]:
    if not text or not text.strip():
        return []

    paragraphs = re.split(r"\n\s*\n", text.strip())
    chunks = []
    current_chunk: list[str] = []
    current_word_count = 0
    current_char_start = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_words = len(para.split())

        if current_chunk and current_word_count + para_words > max_words:
            chunk_text = "\n\n".join(current_chunk)
            char_end = current_char_start + len(chunk_text)
            chunks.append({
                "text": chunk_text,
                "word_count": current_word_count,
                "char_start": current_char_start,
                "char_end": char_end,
            })
            current_char_start = char_end + 2
            current_chunk = []
            current_word_count = 0

        if para_words > max_words:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                sent_words = len(sentence.split())
                if current_chunk and current_word_count + sent_words > max_words:
                    chunk_text = "\n\n".join(current_chunk)
                    char_end = current_char_start + len(chunk_text)
                    chunks.append({
                        "text": chunk_text,
                        "word_count": current_word_count,
                        "char_start": current_char_start,
                        "char_end": char_end,
                    })
                    current_char_start = char_end + 2
                    current_chunk = []
                    current_word_count = 0
                current_chunk.append(sentence)
                current_word_count += sent_words
        else:
            current_chunk.append(para)
            current_word_count += para_words

    if current_chunk:
        chunk_text = "\n\n".join(current_chunk)
        char_end = current_char_start + len(chunk_text)
        chunks.append({
            "text": chunk_text,
            "word_count": current_word_count,
            "char_start": current_char_start,
            "char_end": char_end,
        })

    return chunks
