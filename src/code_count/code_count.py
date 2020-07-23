import json
import operator as op
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import FrozenSet, List, Sequence

import attr
import click
from funcy import compose, merge, select_keys

from .compressed_file import GzipCompressedFile
from .const import LOG_FORMAT
from .datastructures import Commit, Count, Counts
from .plot import Plotter
from .serialize import commit_schema, count_schema
from .utils import LazyCache, hash_path, ntext

CWD = Path.cwd()
cache = LazyCache("ccount")


_save_dir = compose(cache.joinpath, hash_path, op.attrgetter("repo_dir"))


@attr.s(auto_attribs=True, slots=True)
class CodeCounter(object):
    repo_dir: Path = attr.ib(converter=Path)
    output_dir: Path = attr.ib(converter=Path, default=CWD.joinpath("out"))
    verbose: bool = attr.ib(default=False)
    save_dir: Path = attr.ib(init=False, default=attr.Factory(_save_dir, True))
    languages: FrozenSet[str] = frozenset({"Python", "TypeScript", "Sass"})

    def __attrs_post_init__(self):
        if not self.save_dir.is_dir():
            self.save_dir.mkdir(parents=True)

    @property
    def save_file(self) -> Path:
        return self.save_dir / "data.json"

    def log(self, msg: str, **kwargs):
        click.secho(" ".join([">>>", msg]), **kwargs)

    def logv(self, msg: str, **kwargs):
        if self.verbose:
            self.log(msg, **kwargs)

    @property
    def output_file(self) -> Path:
        return self.output_dir / ".".join([self.repo_dir.name, "html"])

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
        for commit in refs:  # type: Commit
            commit_file = self.get_commit_file(commit)
            if commit_file.is_file():
                self.logv(f"Loading {commit_file}")
                raw_count = json.loads(commit_file.read_text())
            else:
                self.checkout(commit.ref)
                raw_count = self.get_raw_count()
                commit_file.write_text(json.dumps(raw_count))
                self.logv(f"Saving {commit_file}")
            counts = select_keys(self.languages, raw_count)
            count = count_schema.load(
                {"commit": commit_schema.dump(commit), "counts": counts}
            )
            items.append(count)
        return items

    def get_counts(self, refs: Sequence[Commit]):
        languages = sorted(self.languages)
        raw_counts = self.get_raw_counts(refs)
        counts = Counts(raw_counts)
        self.logv("Got counts for selected commits.")
        return counts.by_lang(languages)

    def clone(self, tmp: str):
        self.log(f"Using temporary dir {tmp}", fg="blue", bold=True)
        self.run_cmd(["git", "clone", "-n", "--local", str(self.repo_dir), tmp])
        self.repo_dir = Path(tmp)
        self.log(f"Copied repo to {self.repo_dir}", fg="blue", bold=True)

    def run(self, limit: int, branch: str, collapse: bool):
        self.log(f"Examining repository {self.repo_dir}", fg="green")
        output_file = self.output_file
        with TemporaryDirectory(prefix=self.repo_dir.name) as tmp:
            self.clone(tmp)
            self.checkout(branch)
            refs = self.get_commits(collapse)
            n = len(refs)
            commstr = ntext(n, "commit", "commits")
            self.log(f"{n} {commstr}.")
            every = max(len(refs[1:-1]) // limit - 2, 1)
            limited = [refs[0]] + refs[1:-1:every] + [refs[-1]]
            nl = len(limited)
            lstr = ntext(nl, "commit", "commits")
            self.log(f"Limited to {nl} {lstr}.")
            counts = self.get_counts(refs[::every])

        plt = Plotter(output_file)
        plt.plot_counts(counts)
        self.log(f"Wrote {output_file}", fg="green")
