import re
from dataclasses import dataclass
from typing import Callable

from evidence.clean_sentences import clean_sentences
from evidence.selector import has_sufficient_summary_evidence
from evidence.pdf_extract import split_sentences


def normalize_text(text):
    return re.sub(r"\W+", " ", (text or "").lower()).strip()


def is_informative_abstract(title, abstract):
    abstract = (abstract or "").strip()
    if not abstract:
        return False

    if normalize_text(title) == normalize_text(abstract):
        return False

    return len(abstract) >= 120 and any(char in abstract for char in ".!?")


def make_brief_record(paper):
    return {
        "title": paper["title"],
        "url": paper["url"],
        "topic": paper.get("topic", "Other"),
        "cluster_id": paper.get("cluster_id"),
        "cluster_label": paper.get("cluster_label"),
        "cluster_size": paper.get("cluster_size"),
        "selection_score": paper.get("selection_score"),
        "brief": True,
    }


def build_abstract_record(
    paper,
    abstract,
    evidence_validator=has_sufficient_summary_evidence,
):
    abstract = (abstract or "").strip()
    if not is_informative_abstract(paper.get("title", ""), abstract):
        return None

    abstract_sentences = clean_sentences(split_sentences(abstract, min_chars=0, max_chars=1000))
    if not abstract_sentences:
        abstract_sentences = [abstract]

    record = {
        "title": paper["title"],
        "url": paper["url"],
        "topic": paper.get("topic", "Other"),
        "cluster_id": paper.get("cluster_id"),
        "cluster_label": paper.get("cluster_label"),
        "cluster_size": paper.get("cluster_size"),
        "selection_score": paper.get("selection_score"),
        "sentences": abstract_sentences[:10],
        "context": abstract,
        "sections": {"abstract": abstract},
    }

    if not evidence_validator(record):
        return None

    return record


@dataclass(frozen=True)
class EvidenceBuilderDependencies:
    download_pdf: Callable[[dict], object]
    extract_pdf_text: Callable[[object], str]
    extract_sections: Callable[[str], dict]
    build_paper_context: Callable[[dict], str]
    rank_sentences: Callable[[list[str], int], list[str]]
    evidence_validator: Callable[[dict], bool] = has_sufficient_summary_evidence


class FeaturedPaperEvidenceBuilder:
    def __init__(self, dependencies: EvidenceBuilderDependencies):
        self.dependencies = dependencies

    def build_featured_record(self, paper):
        pdf_path = self.dependencies.download_pdf(paper)
        if not pdf_path:
            return build_abstract_record(
                paper,
                paper.get("abstract"),
                evidence_validator=self.dependencies.evidence_validator,
            )

        text = self.dependencies.extract_pdf_text(pdf_path)
        if not text:
            return build_abstract_record(
                paper,
                paper.get("abstract"),
                evidence_validator=self.dependencies.evidence_validator,
            )

        sections = self.dependencies.extract_sections(text)
        source_abstract = (paper.get("abstract") or "").strip()
        if is_informative_abstract(paper.get("title", ""), source_abstract):
            sections["abstract"] = source_abstract

        combined_text = self.dependencies.build_paper_context(sections)
        sentences = clean_sentences(split_sentences(combined_text))
        ranked = self.dependencies.rank_sentences(sentences, top_k=25)

        record = {
            "title": paper["title"],
            "url": paper["url"],
            "topic": paper.get("topic", "Other"),
            "cluster_id": paper.get("cluster_id"),
            "cluster_label": paper.get("cluster_label"),
            "cluster_size": paper.get("cluster_size"),
            "selection_score": paper.get("selection_score"),
            "sentences": ranked,
            "context": combined_text,
            "sections": sections,
        }

        if not self.dependencies.evidence_validator(record):
            return build_abstract_record(
                paper,
                paper.get("abstract"),
                evidence_validator=self.dependencies.evidence_validator,
            )

        return record


class EvidencePreparationPipeline:
    def __init__(self, evidence_builder, max_featured_papers, max_brief_papers):
        self.evidence_builder = evidence_builder
        self.max_featured_papers = max_featured_papers
        self.max_brief_papers = max_brief_papers

    def prepare(self, papers):
        featured_records = []
        brief_records = []

        for paper in papers[:self.max_featured_papers]:
            featured = self.evidence_builder.build_featured_record(paper)
            if featured:
                featured_records.append(featured)
            elif len(brief_records) < self.max_brief_papers:
                brief_records.append(make_brief_record(paper))

        for paper in papers[self.max_featured_papers:]:
            if len(brief_records) >= self.max_brief_papers:
                break
            brief_records.append(make_brief_record(paper))

        return featured_records, brief_records
