def build_summary(sentences, max_sentences=6):
    """
    Create a readable paragraph from ranked sentences.
    """

    selected = sentences[:max_sentences]

    text = " ".join(selected)

    return text


def simple_summary(paper):
    """
    Create a structured summary from extracted sentences.
    """

    sentences = paper["sentences"]

    summary_text = build_summary(sentences)

    return {
        "title": paper["title"],
        "url": paper["url"],
        "topic": paper.get("topic", "Other"),
        "tldr": summary_text
    }


def summarize_papers(papers):

    summaries = []

    for paper in papers:

        summaries.append(simple_summary(paper))

    return summaries