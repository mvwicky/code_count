from datetime import datetime
from typing import Dict, List, NamedTuple, Sequence

from .const import SCHEMA_VERSION


class Commit(NamedTuple):
    ref: str
    dt: datetime
    subject: str = ""


class LangDataPoint(NamedTuple):
    commit: Commit
    code: int = 0


class LanguageCount(NamedTuple):
    blanks: int
    code: int
    comments: int


class Count(NamedTuple):
    commit: Commit
    counts: Dict[str, LanguageCount]


class Counts(NamedTuple):
    counts: List[Count]
    version: str = SCHEMA_VERSION

    def by_lang(self, languages: Sequence[str]) -> Dict[str, List[LangDataPoint]]:
        lang_stats = {lang: [] for lang in languages}
        for count in self.counts:
            for lang in languages:
                stats = lang_stats[lang]
                kw = {"commit": count.commit}
                if lang in count.counts:
                    kw["code"] = count.counts[lang].code
                stats.append(LangDataPoint(**kw))
        return lang_stats
