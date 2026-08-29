from evidence.pdf_extract import clean_text, split_sentences


def test_clean_text_removes_page_numbers_and_number_blocks():
    raw = "Intro\n12\nThis is a test paragraph.\n1 INTRODUCTION\n10 11 12 13 14"
    cleaned = clean_text(raw)

    assert "\n12\n" not in cleaned
    assert "1 INTRODUCTION" not in cleaned
    assert "10 11 12 13 14" not in cleaned


def test_split_sentences_keeps_reasonable_scientific_sentences():
    text = (
        "This sentence is intentionally long enough to be treated as scientific evidence in the pipeline. "
        "Short one. "
        "Another sufficiently detailed sentence reports an improvement in docking performance for benchmark targets."
    )

    sentences = split_sentences(text)

    assert len(sentences) == 2
