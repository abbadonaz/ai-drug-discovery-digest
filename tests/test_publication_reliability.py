from datetime import date
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from digest_core import atomic
from digest_core.models import PipelinePaths, PipelineSettings, PipelineRunResult
from digest_core.publication import verify_manifest
from digest_core.utils import save_json
from pipeline.research_pipeline import ResearchDigestPipeline
from web.publishing import DigestPublisher
import run_pipeline


PAPER = {"title": "Paper", "url": "https://example.org/paper", "topic": "Other",
         "tldr": "A source sentence. Another source sentence.", "generation_mode": "extractive_fallback"}


def fail(*args, **kwargs):
    raise OSError("Injected failure")


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("kind", ["json", "html"])
@pytest.mark.parametrize("failure", ["write", "flush", "replace"])
def test_atomic_write_failure_preserves_old_file_and_cleans_temp(tmp_path, monkeypatch, kind, failure):
    path = tmp_path / f"output.{kind}"
    path.write_text("old bytes", encoding="utf-8")
    if failure == "write":
        original = atomic.tempfile.NamedTemporaryFile
        @contextmanager
        def broken_stream(**kwargs):
            with original(**kwargs) as stream:
                yield SimpleNamespace(name=stream.name, write=fail)
        monkeypatch.setattr(atomic.tempfile, "NamedTemporaryFile", broken_stream)
    else:
        monkeypatch.setattr(atomic.os, "fsync" if failure == "flush" else "replace", fail)
    with pytest.raises(OSError):
        if kind == "json":
            save_json({"unicode": "molecule α"}, path)
        else:
            atomic.atomic_write_text(path, "<html>new</html>")
    assert path.read_text(encoding="utf-8") == "old bytes"
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_json_and_html_success(tmp_path):
    save_json({"unicode": "α"}, tmp_path / "data.json")
    atomic.atomic_write_text(tmp_path / "page.html", "<html>α</html>")
    assert json.loads((tmp_path / "data.json").read_text(encoding="utf-8")) == {"unicode": "α"}
    assert (tmp_path / "page.html").read_text(encoding="utf-8") == "<html>α</html>"
    assert len(list(tmp_path.iterdir())) == 2


@pytest.fixture
def publisher(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    publisher = DigestPublisher(PipelinePaths())
    publisher.ensure_dirs()
    Path("docs/posts/2020-01-01.html").write_text("Historical bytes", encoding="utf-8")
    publisher.publish([PAPER], "Old narrative", run_id="old-run")
    return publisher


@pytest.mark.parametrize("number", [1, 2, 3, 4, 5])
def test_publication_replacement_failure_restores_entire_previous_state(publisher, tmp_path, monkeypatch, number):
    before = snapshot(tmp_path)
    original = atomic.os.replace
    count = 0
    def replace(source, target):
        nonlocal count
        count += 1
        if count == number:
            raise OSError("Injected commit failure")
        original(source, target)
    monkeypatch.setattr(atomic.os, "replace", replace)
    with pytest.raises(OSError):
        publisher.publish([{**PAPER, "title": "New title"}], "New narrative", run_id="new-run")
    assert snapshot(tmp_path) == before
    verify_manifest("docs/publication.json", "old-run")
    with pytest.raises(ValueError):
        verify_manifest("docs/publication.json", "new-run")


def test_new_post_is_removed_on_failure_and_history_survives(publisher, tmp_path, monkeypatch):
    class Tomorrow:
        @staticmethod
        def today():
            return date(2099, 1, 1)
    before = snapshot(tmp_path)
    monkeypatch.setattr("web.publishing.date", Tomorrow)
    original = atomic.os.replace
    failed = False
    def replace(source, target):
        nonlocal failed
        if Path(target).name == "archive.html" and not failed:
            failed = True
            raise OSError("archive failed")
        original(source, target)
    monkeypatch.setattr(atomic.os, "replace", replace)
    with pytest.raises(OSError):
        publisher.publish([PAPER], "New", run_id="new")
    assert snapshot(tmp_path) == before


def test_generation_and_validation_fail_before_destinations_change(publisher, tmp_path, monkeypatch):
    before = snapshot(tmp_path)
    monkeypatch.setattr("web.publishing.render_blog", lambda *a, **k: "<html>truncated")
    with pytest.raises(ValueError):
        publisher.publish([PAPER], "New")
    assert snapshot(tmp_path) == before


def test_failure_placeholders_cannot_be_published(publisher, tmp_path):
    before = snapshot(tmp_path)
    with pytest.raises(ValueError):
        publisher.publish([{**PAPER, "generation_mode": "unavailable"}], "")
    assert snapshot(tmp_path) == before


def test_successful_group_is_readable_and_manifest_detects_tampering(publisher):
    post = publisher.publish([PAPER], "New narrative", artifacts={"data/raw_papers.json": json.dumps([PAPER])}, run_id="new")
    manifest = verify_manifest("docs/publication.json", "new")
    assert manifest["generation_modes"] == {"extractive_fallback": 1}
    assert "New narrative" in Path(post).read_text(encoding="utf-8")
    assert Path(post).name in Path("docs/archive.html").read_text(encoding="utf-8")
    assert "2020-01-01.html" in Path("docs/archive.html").read_text(encoding="utf-8")
    Path("docs/index.html").write_text("damaged", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        verify_manifest("docs/publication.json", "new")


def test_rollback_failure_retains_backups_and_blocks_next_run(publisher, monkeypatch):
    original = atomic.os.replace
    calls = 0
    def replace(source, target):
        nonlocal calls
        calls += 1
        if calls in (2, 3):
            raise OSError("commit and rollback failure")
        original(source, target)
    monkeypatch.setattr(atomic.os, "replace", replace)
    with pytest.raises(atomic.PublicationRollbackError):
        publisher.publish([PAPER], "New")
    assert Path("docs/.publication.lock").exists()
    assert list(Path("data").glob("*.backup"))
    with pytest.raises(FileExistsError):
        publisher.publish([PAPER], "Retry")
    with pytest.raises(ValueError, match="lock"):
        verify_manifest("docs/publication.json", "old-run")


def make_pipeline():
    retriever = SimpleNamespace(fetch_all=lambda: [PAPER], last_report={"outcome": "success"})
    return ResearchDigestPipeline(
        retriever, SimpleNamespace(prepare=lambda papers: (papers, [])),
        DigestPublisher(PipelinePaths()), PipelinePaths(), PipelineSettings(enable_cluster_selection=False),
        summarizer=lambda papers: papers, relevance_filter=lambda papers: papers,
        narrative_generator=lambda papers: "Narrative",
    )


@pytest.mark.parametrize("failure_target", ["index.html", "archive.html", "paper_archive.json", "summaries.json"])
def test_pipeline_rollback_preserves_state_and_retryability(publisher, tmp_path, monkeypatch, failure_target):
    save_json({"https://example.org/old": True}, "data/paper_archive.json")
    before = snapshot(tmp_path)
    original = atomic.os.replace
    failed = False
    def replace(source, target):
        nonlocal failed
        if Path(target).name == failure_target and not failed:
            failed = True
            raise OSError("injected")
        original(source, target)
    monkeypatch.setattr(atomic.os, "replace", replace)
    with pytest.raises(OSError):
        make_pipeline().run()
    assert snapshot(tmp_path) == before
    result = make_pipeline().run()
    assert result.status == "published"
    assert json.loads(Path("data/paper_archive.json").read_text()) == {"https://example.org/old": True, PAPER["url"]: True}
    verify_manifest("docs/publication.json", result.run_id)


def test_processing_failure_and_corrupt_history_do_not_mark_papers(publisher, tmp_path):
    before = snapshot(tmp_path)
    pipeline = make_pipeline()
    pipeline.relevance_filter = fail
    with pytest.raises(OSError):
        pipeline.run()
    assert snapshot(tmp_path) == before
    Path("data/paper_archive.json").write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        make_pipeline().run()
    assert Path("data/paper_archive.json").read_text() == "not json"


def test_success_only_marks_published_urls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pipeline = make_pipeline()
    pipeline.retriever.fetch_all = lambda: [PAPER, {**PAPER, "url": "https://example.org/rejected"}]
    pipeline.relevance_filter = lambda papers: papers[:1]
    result = pipeline.run()
    assert result.status == "published"
    assert json.loads(Path("data/paper_archive.json").read_text()) == {PAPER["url"]: True}


@pytest.mark.parametrize("status,retrieval,post,expected", [
    ("published", "success", "post.html", 0), ("published", "partial", "post.html", 0),
    ("failed", "failed", None, 1), ("no_publication", "empty", None, 2),
])
def test_cli_result_policy(monkeypatch, status, retrieval, post, expected):
    result = PipelineRunResult(0, 0, 0, 0, 0, weekly_post=post, retrieval={"outcome": retrieval}, status=status)
    monkeypatch.setattr(run_pipeline, "build_pipeline", lambda: SimpleNamespace(run=lambda: result))
    assert run_pipeline.main() == expected


def test_cli_publication_exception_nonzero(monkeypatch):
    monkeypatch.setattr(run_pipeline, "build_pipeline", lambda: SimpleNamespace(run=fail))
    assert run_pipeline.main() == 1


@pytest.mark.parametrize("outcome,expected", [("published", 0), ("failed", 1), ("no_publication", 2), ("exception", 1)])
def test_real_cli_process_exit_codes(tmp_path, outcome, expected):
    source = Path(__file__).resolve().parents[1] / "src"
    script = f'''
import sys
sys.path.insert(0, {str(source)!r})
import run_pipeline
from types import SimpleNamespace
from digest_core.models import PipelineRunResult
def execute():
    if {outcome!r} == 'exception':
        raise OSError('publication failed')
    return PipelineRunResult(0,0,0,0,0, status={outcome!r}, weekly_post='post.html' if {outcome!r} == 'published' else None)
run_pipeline.build_pipeline = lambda: SimpleNamespace(run=execute)
raise SystemExit(run_pipeline.main())
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=tmp_path, capture_output=True, timeout=120)
    assert result.returncode == expected, result.stderr.decode(errors="replace")
