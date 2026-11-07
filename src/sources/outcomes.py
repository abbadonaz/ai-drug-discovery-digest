"""List-compatible adapter results with explicit retrieval diagnostics."""
from collections import Counter


def error_diagnostic(stage, error):
    # Exception text/URLs may contain credentials, request queries or emails.
    result = {"stage": stage, "error_type": type(error).__name__}
    status = getattr(getattr(error, "response", None), "status_code", None)
    if isinstance(status, int):
        result["http_status"] = status
    return result


class SourceResult(list):
    def __init__(self, papers=(), *, source="", errors=(), completed=True,
                 date_rejections=None, cache_usage="none", cache_created_at=None,
                 validation_rejected=0):
        super().__init__(papers)
        self.source = source
        self.errors = list(errors)
        self.completed = completed
        self.date_rejections = dict(date_rejections or {})
        self.cache_usage = cache_usage
        self.cache_created_at = cache_created_at
        self.validation_rejected = validation_rejected

    @property
    def outcome(self):
        if not self.completed and not self:
            return "failed"
        if self.cache_usage != "none":
            return "cached"
        if self.errors or not self.completed:
            return "partial"
        return "success" if self else "empty"

    def diagnostics(self):
        return {
            "source": self.source, "outcome": self.outcome, "paper_count": len(self),
            "completed": self.completed, "errors": self.errors,
            "cache_usage": self.cache_usage, "cache_created_at": self.cache_created_at,
            "date_rejected_count": sum(self.date_rejections.values()),
            "date_rejections": self.date_rejections,
            "validation_rejected_count": self.validation_rejected,
        }


def eligible_result(papers, window, *, source, errors=(), completed=True):
    accepted, rejected = window.filter(papers)
    if isinstance(papers, SourceResult):
        rejected = dict(Counter(rejected) + Counter(papers.date_rejections))
    return SourceResult(accepted, source=source, errors=errors,
                        completed=completed, date_rejections=rejected)
