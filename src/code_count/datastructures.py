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

    def by_lang(self, file_types: Sequence[str]) -> Dict[str, List[LangDataPoint]]:
        lang_stats = {ft: [] for ft in file_types}
        for count in self.counts:
            for ft in file_types:
                lang = lang_stats[ft]
                kw = {"commit": count.commit}
                if ft in count.counts:
                    kw["code"] = count.counts[ft].code
                lang.append(LangDataPoint(**kw))
        return lang_stats
