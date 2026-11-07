from pipeline import deduplication
from pipeline.deduplication import split_new_and_seen_papers
from digest_core.atomic import publication_lock
from pathlib import Path
import json
import os
import uuid
from triage.filtering import filter_relevant_papers
from summarization.narrative import generate_weekly_narrative
from triage.clustering import build_cluster_overviews, cluster_and_select_papers
from triage.scoring import rank_papers
from digest_core.logging import NullRunLogger
from digest_core.models import PipelineRunResult


class ResearchDigestPipeline:
    def __init__(
        self,
        retriever,
        evidence_pipeline,
        publisher,
        paths,
        settings,
        summarizer,
        relevance_filter=filter_relevant_papers,
        paper_ranker=rank_papers,
        narrative_generator=generate_weekly_narrative,
        cluster_selector=cluster_and_select_papers,
        logger=None,
        runtime_metadata=None,
    ):
        self.retriever = retriever
        self.evidence_pipeline = evidence_pipeline
        self.publisher = publisher
        self.paths = paths
        self.settings = settings
        self.summarizer = summarizer
        self.relevance_filter = relevance_filter
        self.paper_ranker = paper_ranker
        self.narrative_generator = narrative_generator
        self.cluster_selector = cluster_selector
        self.logger = logger or NullRunLogger()
        self.runtime_metadata = runtime_metadata or {}

    def run(self):
        with publication_lock(Path(self.paths.index).parent / ".publication.lock"):
            return self._run()

    def _run(self):
        run_id = os.getenv("DIGEST_RUN_ID") or uuid.uuid4().hex
        if hasattr(self.logger, "run_id"):
            self.logger.run_id = run_id
        artifacts = {}
        def stage_json(data, path):
            artifacts[path] = json.dumps(data, indent=2, ensure_ascii=False)
        run_timer = self.logger.timer("pipeline")
        self.publisher.ensure_dirs()

        fetched_papers = self.retriever.fetch_all()
        retrieval = getattr(self.retriever, "last_report", None) or {"outcome": "unknown"}
        self.logger.info("retrieval", "papers_fetched", count=len(fetched_papers), health=retrieval)
        if retrieval["outcome"] == "failed":
            self.logger.error("pipeline", "halted_retrieval_failed")
            result = PipelineRunResult(0, 0, 0, 0, 0, retrieval=retrieval, status="failed", run_id=run_id)
            run_timer.finish(**result.__dict__)
            return result

        papers_to_process, new_count = self._select_papers_to_process(fetched_papers)
        stage_json(papers_to_process, self.paths.raw_papers)

        if not papers_to_process:
            self.logger.warning("pipeline", "halted_no_papers")
            result = PipelineRunResult(
                status="no_publication", run_id=run_id,
                retrieval=retrieval,
                fetched_count=len(fetched_papers),
                new_count=new_count,
                filtered_count=0,
                featured_count=0,
                brief_count=0,
            )
            run_timer.finish(**result.__dict__)
            return result

        filter_timer = self.logger.timer("filtering")
        filtered = self.relevance_filter(papers_to_process)
        filter_timer.finish(input_count=len(papers_to_process), output_count=len(filtered))
        stage_json(filtered, self.paths.filtered_papers)

        selection_input = filtered
        cluster_overviews = {}
        if self.settings.enable_cluster_selection:
            cluster_timer = self.logger.timer("clustering")
            clustered, selection_input = self.cluster_selector(filtered, self.settings)
            cluster_overviews = build_cluster_overviews(clustered)
            cluster_timer.finish(cluster_count=len(cluster_overviews), selected_count=min(len(selection_input), self.settings.max_featured_papers))
            stage_json(clustered, self.paths.clustered_papers)

        evidence_timer = self.logger.timer("evidence")
        featured, brief = self.evidence_pipeline.prepare(selection_input)
        self._attach_cluster_overviews(featured, cluster_overviews)
        evidence_timer.finish(featured_count=len(featured), brief_count=len(brief))
        stage_json(featured, self.paths.paper_sentences)

        if not featured:
            self.logger.warning("pipeline", "halted_no_featured_evidence")
            result = PipelineRunResult(
                status="no_publication", run_id=run_id,
                retrieval=retrieval,
                fetched_count=len(fetched_papers),
                new_count=new_count,
                filtered_count=len(filtered),
                featured_count=0,
                brief_count=len(brief),
            )
            run_timer.finish(**result.__dict__)
            return result

        summaries = self._summarize_and_rank(featured, brief)
        stage_json(summaries, self.paths.summaries)

        narrative_timer = self.logger.timer("narrative")
        narrative = self.narrative_generator(summaries)
        narrative_timer.finish(summary_count=len(summaries), chars=len(narrative or ""))

        publish_timer = self.logger.timer("publishing")
        # Only papers actually included in this digest become seen. Stage the
        # merged history in the same rollback boundary as HTML and snapshots.
        stage_json(deduplication.archive_with_seen(summaries), deduplication.ARCHIVE_FILE)
        weekly_post = self.publisher.publish(
            summaries, narrative, artifacts=artifacts, run_id=run_id,
            metadata={"retrieval": retrieval, **self.runtime_metadata},
        )
        publish_timer.finish(weekly_post=weekly_post)

        result = PipelineRunResult(
            status="published", run_id=run_id,
            retrieval=retrieval,
            fetched_count=len(fetched_papers),
            new_count=new_count,
            filtered_count=len(filtered),
            featured_count=len(featured),
            brief_count=len(brief),
            weekly_post=weekly_post,
        )
        run_timer.finish(**result.__dict__)
        return result

    def _attach_cluster_overviews(self, papers, cluster_overviews):
        for paper in papers:
            cluster_id = paper.get("cluster_id")
            if cluster_id in cluster_overviews:
                paper["cluster_overview"] = cluster_overviews[cluster_id]

    def _select_papers_to_process(self, fetched_papers):
        new_papers, seen_papers = split_new_and_seen_papers(fetched_papers)
        self.logger.info("deduplication", "completed", new_count=len(new_papers), seen_count=len(seen_papers))

        if new_papers:
            return new_papers, len(new_papers)

        if self.settings.process_all_when_no_new:
            self.logger.info("deduplication", "rebuilding_from_seen")
            return seen_papers, 0

        return [], 0

    def _summarize_and_rank(self, featured, brief):
        summary_timer = self.logger.timer("summarization")
        try:
            summaries = self.summarizer(featured)
        except Exception as error:
            self.logger.error("summarization", "failed", error=str(error))
            summaries = [
                {
                    "title": paper["title"],
                    "url": paper["url"],
                    "topic": paper.get("topic", "Other"),
                    "tldr": "Automatic summarization failed for this paper, so please review the original source directly.",
                    "cluster_id": paper.get("cluster_id"),
                    "cluster_label": paper.get("cluster_label"),
                    "cluster_size": paper.get("cluster_size"),
                    "cluster_overview": paper.get("cluster_overview"),
                    "provenance": [],
                    "generation_mode": "unavailable",
                    "evidence_mode": paper.get("evidence_mode", "unknown"),
                }
                for paper in featured
            ]

        summaries = self.paper_ranker(summaries)

        for paper in brief:
            summaries.append({
                "title": paper["title"],
                "url": paper["url"],
                "topic": paper.get("topic", "Other"),
                "cluster_id": paper.get("cluster_id"),
                "cluster_label": paper.get("cluster_label"),
                "cluster_size": paper.get("cluster_size"),
                "tldr": "",
                "brief": True,
                "score": 0,
                "provenance": [],
                "generation_mode": "not_generated",
                "evidence_mode": paper.get("evidence_mode", "unknown"),
            })

        summary_timer.finish(featured_count=len(featured), brief_count=len(brief), total_count=len(summaries))
        return summaries
