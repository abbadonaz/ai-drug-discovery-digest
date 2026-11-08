import re
from dataclasses import dataclass
from typing import Callable

from evidence.clean_sentences import clean_sentences
from evidence.selector import has_sufficient_summary_evidence
from evidence.pdf_extract import split_sentences
from evidence.pdf_document import extract_pdf_document
from digest_core.config import EVIDENCE_SELECTION_STRATEGY


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
        **{key: paper[key] for key in ("full_text_retrieval", "full_text_fallback_reason", "extraction_diagnostics", "selection_diagnostics") if key in paper},
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
    strategy=None,
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
        "evidence_mode": "abstract_only",
    }
    if strategy is not None:
        record["evidence_strategy"] = strategy

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
    extract_pdf_document: Callable[[object], dict] = extract_pdf_document
    retrieve_full_text: Callable[[dict], dict] | None = None


class FeaturedPaperEvidenceBuilder:
    def __init__(self, dependencies: EvidenceBuilderDependencies, strategy=None, summary_format=None, fallback_policy="allow"):
        self.dependencies = dependencies
        self.summary_format = summary_format
        self.fallback_policy = fallback_policy
        if fallback_policy not in {"allow", "brief_only"}:
            raise ValueError("Unknown abstract fallback policy")
        self.strategy = strategy or EVIDENCE_SELECTION_STRATEGY
        if self.strategy not in {"legacy", "section_aware"}:
            raise ValueError("Unknown evidence selection strategy")

    def build_featured_record(self, paper):
        if self.strategy == "section_aware":
            return self._build_section_record(paper)
        pdf_path = self.dependencies.download_pdf(paper)
        if not pdf_path:
            return build_abstract_record(
                paper,
                paper.get("abstract"),
                evidence_validator=self.dependencies.evidence_validator,
                strategy="legacy",
            )

        text = self.dependencies.extract_pdf_text(pdf_path)
        if not text:
            return build_abstract_record(
                paper,
                paper.get("abstract"),
                evidence_validator=self.dependencies.evidence_validator,
                strategy="legacy",
            )

        sections = self.dependencies.extract_sections(text)
        source_abstract = (paper.get("abstract") or "").strip()
        if is_informative_abstract(paper.get("title", ""), source_abstract):
            sections["abstract"] = source_abstract

        combined_text = self.dependencies.build_paper_context(sections)
        sentences = clean_sentences(split_sentences(combined_text))
        ranked = self.dependencies.rank_sentences(sentences, top_k=25)

        record = {
            "evidence_strategy": "legacy",
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
            # Describe available prepared evidence, not which snippets the
            # later abstract-first selector will choose for the summary.
            "evidence_mode": (
                "pdf_full_text" if any(value.strip() for key, value in sections.items() if key != "abstract")
                else "abstract_only" if sections.get("abstract", "").strip()
                else "unknown"
            ),
        }

        if not self.dependencies.evidence_validator(record):
            return build_abstract_record(
                paper,
                paper.get("abstract"),
                evidence_validator=self.dependencies.evidence_validator,
                strategy="legacy",
            )

        return record

    def _build_section_record(self, paper):
        from evidence.scientific_sections import abstract_passages, build_passages, detect_sections, extract_document_abstract
        from evidence.section_selection import build_section_payload
        retrieval = self.dependencies.retrieve_full_text(paper) if self.dependencies.retrieve_full_text else None
        pdf_path = retrieval.get("path") if retrieval else self.dependencies.download_pdf(paper)
        document = self.dependencies.extract_pdf_document(pdf_path) if pdf_path else {
            "status": "unavailable", "pages": [], "text": "", "raw_text": "",
            "limitations": ["pdf_unavailable"],
        }
        sections = detect_sections(document) if document["status"] == "success" else []
        if not is_informative_abstract(paper.get("title", ""), paper.get("abstract", "")):
            paper = {**paper, "abstract": extract_document_abstract(document) or paper.get("abstract", "")}
        passages = build_passages(document, paper["url"]) if sections else []
        passages += abstract_passages(paper)
        record = {**paper, "evidence_strategy": "section_aware", "passages": passages,
                  "document": document, "scientific_sections": sections,
                  "sections": {}, "context": document["text"], "sentences": [],
                  "extraction_diagnostics": {"status": document["status"], "page_count": len(document["pages"]),
                                             "quality": document.get("quality_diagnostics", {}),
                                             "available_abstract_chars": len(paper.get("abstract", "")),
                                             "limitations": document["limitations"]}}
        for section in sections:
            name = section["category"]
            record["sections"][name] = record["sections"].get(name, "") + section["text"]
        if paper.get("abstract"):
            record["sections"]["abstract"] = paper["abstract"]
        payload = build_section_payload(record)
        selected = payload["evidence"]
        record.update(selected_evidence=selected, selection_diagnostics=payload["selection_diagnostics"],
                      sentences=[item["text"] for item in selected], context=payload["context"],
                      evidence_mode="pdf_full_text" if any(p["source_type"] == "pdf" and p["section"] not in {"abstract", "references"} for p in passages)
                      else "abstract_only" if any(p["section"] == "abstract" for p in passages) else "unknown")
        if retrieval is not None:
            record["full_text_retrieval"] = {k: v for k, v in retrieval.items() if k != "path"}
        used_full_text = any(p["source_type"] == "pdf" and p["section"] != "abstract" for p in selected)
        if not used_full_text:
            record["full_text_fallback_reason"] = (
                "retrieval_" + retrieval["outcome"] if retrieval and not pdf_path else
                "extraction_" + document["status"] if document["status"] != "success" else
                "context_budget" if payload["selection_diagnostics"]["excluded"]["budget"] else
                "poor_section_detection" if not any(s["category"] not in {"unknown", "abstract", "references"} for s in sections) else
                "empty_full_text_selection")
            if self.fallback_policy == "brief_only":
                # Brief references retain diagnostics too; do not mark a missing
                # full-text review as a completed featured summary.
                paper["full_text_retrieval"] = record.get("full_text_retrieval", {})
                paper["full_text_fallback_reason"] = record["full_text_fallback_reason"]
                paper["extraction_diagnostics"] = record["extraction_diagnostics"]
                paper["selection_diagnostics"] = record["selection_diagnostics"]
                return None
        if self.summary_format:
            record["summary_format"] = self.summary_format
        return record if self.dependencies.evidence_validator(record) else None


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
