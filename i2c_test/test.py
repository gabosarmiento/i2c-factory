# sample_module.py

def analyze_text(text):
    words = text.split()
    word_count = len(words)
    char_count = sum(len(word) for word in words)
    avg_word_length = char_count / word_count if word_count else 0
    return {
        "word_count": word_count,
        "avg_word_length": round(avg_word_length, 2)
    }
