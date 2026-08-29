from pipeline.deduplication import mark_papers_seen, split_new_and_seen_papers
from triage.filtering import filter_relevant_papers
from summarization.narrative import generate_weekly_narrative
from triage.clustering import build_cluster_overviews, cluster_and_select_papers
from triage.scoring import rank_papers
from digest_core.logging import NullRunLogger
from digest_core.models import PipelineRunResult
from digest_core.utils import save_json


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

    def run(self):
        run_timer = self.logger.timer("pipeline")
        self.publisher.ensure_dirs()

        fetched_papers = self.retriever.fetch_all()
        self.logger.info("retrieval", "papers_fetched", count=len(fetched_papers))

        papers_to_process, new_count = self._select_papers_to_process(fetched_papers)
        save_json(papers_to_process, self.paths.raw_papers)

        if not papers_to_process:
            self.logger.warning("pipeline", "halted_no_papers")
            result = PipelineRunResult(
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
        save_json(filtered, self.paths.filtered_papers)

        selection_input = filtered
        cluster_overviews = {}
        if self.settings.enable_cluster_selection:
            cluster_timer = self.logger.timer("clustering")
            clustered, selection_input = self.cluster_selector(filtered, self.settings)
            cluster_overviews = build_cluster_overviews(clustered)
            cluster_timer.finish(cluster_count=len(cluster_overviews), selected_count=min(len(selection_input), self.settings.max_featured_papers))
            save_json(clustered, self.paths.clustered_papers)

        evidence_timer = self.logger.timer("evidence")
        featured, brief = self.evidence_pipeline.prepare(selection_input)
        self._attach_cluster_overviews(featured, cluster_overviews)
        evidence_timer.finish(featured_count=len(featured), brief_count=len(brief))
        save_json(featured, self.paths.paper_sentences)

        if not featured:
            self.logger.warning("pipeline", "halted_no_featured_evidence")
            result = PipelineRunResult(
                fetched_count=len(fetched_papers),
                new_count=new_count,
                filtered_count=len(filtered),
                featured_count=0,
                brief_count=len(brief),
            )
            run_timer.finish(**result.__dict__)
            return result

        summaries = self._summarize_and_rank(featured, brief)
        save_json(summaries, self.paths.summaries)

        narrative_timer = self.logger.timer("narrative")
        narrative = self.narrative_generator(summaries)
        narrative_timer.finish(summary_count=len(summaries), chars=len(narrative or ""))

        publish_timer = self.logger.timer("publishing")
        weekly_post = self.publisher.publish(summaries, narrative)
        publish_timer.finish(weekly_post=weekly_post)

        result = PipelineRunResult(
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
            mark_papers_seen(new_papers)
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
            })

        summary_timer.finish(featured_count=len(featured), brief_count=len(brief), total_count=len(summaries))
        return summaries
