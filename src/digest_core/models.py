from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator


@dataclass(frozen=True)
class PipelinePaths:
    raw_papers: str = "data/raw_papers.json"
    filtered_papers: str = "data/filtered_papers.json"
    clustered_papers: str = "data/clustered_papers.json"
    paper_sentences: str = "data/paper_sentences.json"
    summaries: str = "data/summaries.json"
    posts_dir: str = "docs/posts"
    index: str = "docs/index.html"
    archive: str = "docs/archive.html"


@dataclass(frozen=True)
class PipelineSettings:
    days_back: int = 7
    arxiv_max_results: int = 75
    pubmed_max_results: int = 100
    source_cache_ttl_hours: int = 24
    source_retry_attempts: int = 2
    enable_cluster_selection: bool = True
    cluster_relevance_weight: float = 0.65
    cluster_representativeness_weight: float = 0.35
    max_featured_papers: int = 12
    max_brief_papers: int = 13
    process_all_when_no_new: bool = True


@dataclass(frozen=True)
class PipelineRunResult:
    fetched_count: int
    new_count: int
    filtered_count: int
    featured_count: int
    brief_count: int
    weekly_post: str | None = None


class PaperRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = Field(min_length=1)
    abstract: str = ""
    url: HttpUrl
    source: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    published: str = ""
    pdf_url: HttpUrl | None = None
    topic: str | None = None

    @field_validator("title", "abstract", "source", "published", mode="before")
    @classmethod
    def normalize_text_field(cls, value):
        if value is None:
            return ""
        return str(value).strip()

    @field_serializer("url", "pdf_url")
    def serialize_urls(self, value):
        return str(value) if value is not None else None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class SummaryRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = Field(min_length=1)
    url: HttpUrl
    topic: str = "Other"
    tldr: str = ""
    score: float | int | None = None
    brief: bool = False
    cluster_id: int | None = None
    cluster_label: str | None = None
    cluster_size: int | None = None
    cluster_overview: str | None = None
    provenance: list[dict[str, Any]] = Field(default_factory=list)

    @field_serializer("url")
    def serialize_url(self, value):
        return str(value)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)
