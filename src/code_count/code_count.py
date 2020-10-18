import json
import operator as op
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import FrozenSet, List, Sequence

import attr
from funcy import compose, merge, select_keys

from .compressed_file import GzipCompressedFile
from .const import LOG_FORMAT
from .datastructures import Commit, Count, Counts
from .serialize import commit_schema, count_schema
from .utils import LazyCache, Log, hash_path, ntext

CWD = Path.cwd()
cache = LazyCache("ccount")


_save_dir = compose(cache.joinpath, hash_path, op.attrgetter("repo_dir"))


@attr.s(auto_attribs=True, slots=True)
class Counter(object):
    repo_dir: Path = attr.ib(converter=Path)
    log: Log = attr.ib()
    output_dir: Path = attr.ib(converter=Path, default=CWD.joinpath("out"))
    save_dir: Path = attr.ib(init=False, default=attr.Factory(_save_dir, True))
    languages: FrozenSet[str] = frozenset({"Python", "TypeScript", "Sass"})
    output_file: Path = attr.ib(init=False)

    @classmethod
    def create(cls, repo_dir: str, log: Log, **kwargs) -> "Counter":
        return cls(repo_dir, log, **kwargs)

    @output_file.default
    def _output_file(self):
        return self.output_dir / ".".join([self.repo_dir.name, "html"])

    def __attrs_post_init__(self):
        if not self.save_dir.is_dir():
            self.save_dir.mkdir(parents=True)

    @property
    def save_file(self) -> Path:
        return self.save_dir / "data.json"

    def logv(self, msg: str, **kwargs):
        self.log.verbose(msg, **kwargs)

    def run_cmd(self, args: Sequence[str], **kwargs):
        defaults = {
            "check": True,
            "stdout": subprocess.PIPE,
            "text": True,
            "cwd": str(self.repo_dir),
        }
        kw = merge(defaults, kwargs)
        return subprocess.run(args, **kw)

    def get_commit_file(self, commit: Commit):
        return GzipCompressedFile(self.save_dir / f"{commit.ref}.json.gz")

    def get_commits(self, collapse: bool) -> List[Commit]:
        cmd = self.run_cmd(["git", "log", f"--format={LOG_FORMAT}"])
        lines = cmd.stdout.splitlines()
        commits = []
        for line in lines:
            commit_hash, ts, subject = line.split("\t", 2)
            commit = commit_schema.load_commit(
                {"ref": commit_hash, "dt": ts, "subject": subject}
            )
            if collapse and commits and commits[-1].dt == commit.dt:
                commits[-1] = commit
            else:
                commits.append(commit)

        return sorted(commits, key=op.itemgetter(1))

    def checkout(self, ref: str):
        self.run_cmd(["git", "checkout", ref], stderr=subprocess.DEVNULL)

    def get_raw_count(self) -> dict:
        cmd = self.run_cmd(["tokei", "--output", "json"])
        return json.loads(cmd.stdout)

    def get_raw_counts(self, refs: Sequence[Commit]) -> List[Count]:
        items = []
        hits, misses = 0, 0
        for commit in refs:  # type: Commit
            commit_file = self.get_commit_file(commit)
            if commit_file.is_file():
                self.logv(f"Loading {commit_file}")
                raw_count = json.loads(commit_file.read_text())
                hits += 1
            else:
                self.checkout(commit.ref)
                raw_count = self.get_raw_count()
                commit_file.write_text(json.dumps(raw_count))
                self.logv(f"Saving {commit_file}")
                misses += 1
            counts = select_keys(self.languages, raw_count)
            count = count_schema.load(
                {"commit": commit_schema.dump(commit), "counts": counts}
            )
            items.append(count)
        hit_str = ntext(hits, "commit", "commits")
        miss_str = ntext(misses, "commit", "commits")
        self.log(f"{hits} {hit_str} cached", fg="green")
        self.log(f"{misses} {miss_str} missed", fg="yellow")
        return items

    def get_counts(self, refs: Sequence[Commit]):
        languages = sorted(self.languages)
        raw_counts = self.get_raw_counts(refs)
        counts = Counts(raw_counts)
        self.logv("Got counts for selected commits.")
        return counts.by_lang(languages)

    def clone(self, tmp: str):
        self.log(f"Using temporary dir {tmp}", fg="blue", bold=True)
        # TODO: Clone from URL
        self.run_cmd(["git", "clone", "-n", "--local", str(self.repo_dir), tmp])
        self.repo_dir = Path(tmp)
        self.log(f"Copied repo to {self.repo_dir}", fg="blue", bold=True)

    def count(self, limit: int, branch: str, collapse: bool):
        with TemporaryDirectory(prefix=self.repo_dir.name) as tmp:
            self.clone(tmp)
            self.checkout(branch)
            refs = self.get_commits(collapse)
            n = len(refs)
            commstr = ntext(n, "commit", "commits")
            collapsed = "" if not collapse else " (collapsed)"
            self.log(f"Repo has {n} {commstr}.{collapsed}")
            if limit:
                middle = refs[1:-1]
                every = max(len(middle) // (limit - 2), 1)
                self.log.verbose(f"every={every}")
                limited = [refs[0]] + refs[1:-1:every] + [refs[-1]]
            else:
                limited = refs
            nl = len(limited)
            lstr = ntext(nl, "commit", "commits")
            self.log(f"Limited to {nl} {lstr}.")
            return self.get_counts(limited)
