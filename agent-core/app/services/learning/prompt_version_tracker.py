from __future__ import annotations

from dataclasses import dataclass, field

from app.services.learning.feedback_reader import FeedbackReader, ImageFeedbackRecord


@dataclass
class PromptVersionReport:
    version: str
    total: int = 0
    positive: int = 0
    negative: int = 0
    tags: dict[str, int] = field(default_factory=dict)


class PromptVersionTracker:
    def __init__(self, reader: FeedbackReader | None = None):
        self.reader = reader or FeedbackReader()

    async def compare_versions(self, versions: list[str]) -> dict[str, PromptVersionReport]:
        reports: dict[str, PromptVersionReport] = {}
        for version in versions:
            records = await self.reader.list_image_feedback_by_version(version)
            report = PromptVersionReport(version=version)
            for r in records:
                report.total += 1
                report.tags[r.tag] = report.tags.get(r.tag, 0) + 1
                if self._is_positive(r):
                    report.positive += 1
                elif self._is_negative(r):
                    report.negative += 1
            reports[version] = report
        return reports

    def _is_positive(self, record: ImageFeedbackRecord) -> bool:
        return record.comment is not None and any(
            word in record.comment for word in ["good", "满意", "好", "喜欢"]
        )

    def _is_negative(self, record: ImageFeedbackRecord) -> bool:
        return record.comment is not None and any(
            word in record.comment for word in ["bad", "不", "差", "主体不突出"]
        )
