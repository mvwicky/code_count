import hashlib
import json
import operator as op
import random
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, FrozenSet, List, Optional, Sequence, Union, cast

import attr
import click
from funcy import merge, select_keys
from marshmallow import ValidationError

from .datastructures import Commit, Count, Counts, LangDataPoint
from .plot import Plotter
from .serialize import commit_schema, count_schema, counts_schema

CWD = Path.cwd()
CACHE_HOME = CWD / ".cache"

cache_dir = CACHE_HOME
if not cache_dir.is_dir():
    cache_dir.mkdir(parents=True)


def true_with_prob(p: float) -> bool:
    x = random.uniform(0, 1)
    return x < p


def ntext(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


@attr.s(auto_attribs=True, slots=True)
class CodeCounter(object):
    repo_dir: Path = attr.ib(converter=Path)
    output_dir: Path = attr.ib(converter=Path, default=CWD.joinpath("out"))
    output_name: str = attr.ib(default="ccount.html")
    save_dir: Path = attr.ib(init=False)
    save_file: Path = attr.ib(init=False)
    file_types: FrozenSet[str] = frozenset({"Python", "TypeScript", "Sass"})

    @save_dir.default
    def _save_dir(self):
        digest = hashlib.md5(bytes(self.repo_dir)).hexdigest()
        name = f"{self.repo_dir.name}-{digest}"
        return cache_dir / name

    @save_file.default
    def _save_file(self):
        digest = hashlib.md5(bytes(self.repo_dir)).hexdigest()
        file_name = f"{self.repo_dir.name}-{digest}.json"
        return cache_dir / file_name

    @property
    def output_file(self) -> Path:
        return self.output_dir / self.output_name

    def run_cmd(self, args: Sequence[str], **kwargs):
        defaults = {
            "check": True,
            "stdout": subprocess.PIPE,
            "text": True,
            "cwd": str(self.repo_dir),
        }
        kw = merge(defaults, kwargs)
        return subprocess.run(args, **kw)

    def save_counts(self, items: dict):
        counts = Counts(items)
        self.save_file.write_text(counts_schema.dumps(counts))

    def load_counts(self, limit: int) -> Optional[Dict[str, List[LangDataPoint]]]:
        if not self.save_file.is_file():
            return None
        try:
            data = counts_schema.loads(self.save_file.read_text())
        except ValidationError as err:
            click.secho("Cached file failed validation", fg="red", bold=True)
            print(err.messages)
            self.save_file.unlink()
            return None

        data = cast(Counts, data)
        return data.by_lang(sorted(self.file_types))

    def get_commits(self) -> List[Commit]:
        fmt = r"%H%x09%aI%x09%s"
        cmd = self.run_cmd(["git", "--no-pager", "log", f"--format={fmt}"])
        lines = cmd.stdout.splitlines()
        commits = []
        for line in lines:
            commit_hash, ts, subject = line.split("\t", 2)
            commit = commit_schema.load(
                {"ref": commit_hash, "dt": ts, "subject": subject}
            )
            if commits and commits[-1].dt == commit.dt:
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
            self.checkout(commit.ref)
            counts = select_keys(self.file_types, self.get_raw_count())
            count = count_schema.load(
                {"commit": commit_schema.dump(commit), "counts": counts}
            )
            items.append(count)
        # self.save_counts(items)
        return items

    def get_counts(self, refs: Sequence[Commit]):
        file_types = sorted(self.file_types)
        raw_counts = self.get_raw_counts(refs)
        counts = Counts(raw_counts)
        return counts.by_lang(file_types)

    def relocate(self, tmp: str):
        click.secho(f"Using temporary dir {tmp}", fg="blue", bold=True)
        self.run_cmd(["git", "clone", "-n", "--local", str(self.repo_dir), tmp])
        self.repo_dir = Path(tmp)
        click.secho(f"Copied repo to {self.repo_dir}", fg="blue", bold=True)

    def run(self, limit: Union[int, float], branch: str, safe: bool):
        with TemporaryDirectory(prefix=self.repo_dir.name) as tmp:
            self.relocate(tmp)

            self.checkout(branch)
            refs = self.get_commits()
            n = len(refs)
            commstr = ntext(n, "commit", "commits")
            click.secho(f"{n} {commstr}.")
            every = max(len(refs[1:-1]) // limit - 2, 1)
            print(every)
            limited = [refs[0]] + refs[1:-1:every] + [refs[-1]]
            nl = len(limited)
            lstr = ntext(nl, "commit", "commits")
            click.secho(f"Limited to {nl} {lstr}.")
            counts = self.get_counts(refs[::every])

        plt = Plotter(self.output_file)
        plt.plot_counts(counts)
