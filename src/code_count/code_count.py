import argparse
import hashlib
import json
import operator as op
import os
import subprocess
from datetime import datetime
from itertools import cycle
from pathlib import Path
from typing import Optional, Sequence, Tuple

from bokeh.plotting import ColumnDataSource, figure, output_file, save
from funcy import get_in, merge, select_keys

HERE = Path(__file__).resolve().parent
CWD = Path.cwd()
COLORS = cycle(["cadetblue", "crimson", "peru", "olive"])

SCHEMA_VERSION = "4.3"
CACHE_HOME = CWD / ".cache"
cache_dir = CACHE_HOME
if not cache_dir.is_dir():
    cache_dir.mkdir(parents=True)

TOOLS = "pan,hover,wheel_zoom,box_zoom,save,reset,help"


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return {"__datetime__": True, "value": o.isoformat()}
        return super().default(o)


def load_datetime(dct: dict):
    if "__datetime__" in dct:
        return datetime.fromisoformat(dct["value"])
    return dct


def dir_arg(value: str):
    p = Path(value).resolve()
    if not p.is_dir():
        raise argparse.ArgumentTypeError("Not a directory")
    if ".git" not in {e.name for e in p.iterdir()}:
        raise argparse.ArgumentTypeError(f"{p} Doesn't appear to be a git repo.")
    return p


class CodeCounter(object):
    def __init__(self, repo_dir: os.PathLike):
        self.repo_dir = Path(repo_dir)
        digest = hashlib.md5(bytes(self.repo_dir)).hexdigest()
        file_name = f"{self.repo_dir.name}-{digest}.json"
        self.save_file: Path = cache_dir / file_name
        self.file_types = {"Python", "TypeScript", "Sass"}

    def run_cmd(self, args: Sequence[str], **kwargs):
        return subprocess.run(
            args,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
            cwd=self.repo_dir,
            **kwargs,
        )

    def save_counts(self, items: dict):
        data = {"counts": items, "version": SCHEMA_VERSION}
        self.save_file.write_text(json.dumps(data, cls=JSONEncoder))

    def load_counts(self) -> Optional[dict]:
        if not self.save_file.is_file():
            return None
        data = json.loads(self.save_file.read_text(), object_hook=load_datetime)
        if data.get("version") != SCHEMA_VERSION:
            self.save_file.unlink()
            return None
        items = []
        counts = data["counts"]
        file_types = sorted(self.file_types)
        for tag in counts:
            cc = counts[tag].pop("cc")
            elem_count = {}
            for ft in file_types:
                get_in(counts, [tag, "cc", ft, "code"])
                elem_count[ft] = cc[ft]["code"]
            items.append(merge(counts[tag], {"counts": elem_count}))
        return items

    def get_commits(self, limit: int = 50):
        fmt = r"%H %at"
        cmd = self.run_cmd(["git", "log", f"--format={fmt}", "HEAD"])
        lines = cmd.stdout.splitlines()
        commits = []
        every = len(lines) // limit
        for line in lines[::every]:
            name, ts = line.rsplit(" ", 1)
            commits.append((name, datetime.utcfromtimestamp(int(ts))))
        return sorted(commits, key=op.itemgetter(1))

    def get_tags(self):
        fmt = "%(refname:strip=2) %(creatordate:unix)"
        cmd = self.run_cmd(["git", "tag", f"--format='{fmt}'"])
        lines = cmd.stdout.splitlines()
        tags = []
        for line in lines:
            name, ts = line.replace("'", "").rsplit(" ", 1)
            tags.append((name, datetime.utcfromtimestamp(int(ts))))
        return sorted(tags, key=op.itemgetter(1))

    def checkout(self, ref: str):
        self.run_cmd(["git", "checkout", ref], stderr=subprocess.DEVNULL)

    def get_raw_count(self):
        cmd = self.run_cmd(["tokei", "--output", "json"])
        return json.loads(cmd.stdout)

    def get_raw_counts(self, refs: Sequence[Tuple[str, datetime]]):
        items = {}
        for ref, creatordate in refs:
            self.checkout(ref)
            raw_count = select_keys(self.file_types, self.get_raw_count())
            for key in raw_count:
                stats = raw_count[key].pop("stats", [])
                raw_count[key]["num_files"] = len(stats)
            items[ref] = {"ref": ref, "creatordate": creatordate, "cc": raw_count}
        self.save_counts(items)
        return items

    def get_counts(self, refs: Sequence[Tuple[str, datetime]]):
        file_types = sorted(self.file_types)
        raw_counts = self.get_raw_counts(refs)
        longest = max((len(t) for (t, _) in refs))
        items = []
        for ref, creatordate in refs:
            elem = raw_counts[ref]["cc"]
            counts = {}
            for file_type in file_types:
                counts[file_type] = get_in(elem, [file_type, "code"])
            count_str = " ".join((f"{k}={v}" for k, v in counts.items()))
            print(f"{ref:{longest}} ({creatordate:%x %X}) - {count_str}")
            items.append({"ref": ref, "creatordate": creatordate, "counts": counts})
        return items

    def run(self):
        refs = self.get_commits()
        counts = self.load_counts()
        if counts is None or len(refs) != len(counts):
            counts = self.get_counts(refs)
            self.run_cmd(["git", "checkout", "dev"], stderr=subprocess.DEVNULL)

        self.plot_counts(counts)

    def plot_counts(self, counts: Sequence[dict]):
        code_counts = list(map(op.itemgetter("counts"), counts))
        dates = list(map(op.itemgetter("creatordate"), counts))
        output_file(str(CWD / "ccount.html"), title="Code Counts")
        p = figure(
            title="Code Count",
            x_axis_label="Date",
            y_axis_label="Lines of Code",
            x_axis_type="datetime",
            plot_width=1000,
            plot_height=700,
            tools=TOOLS,
        )
        date_strs = [dt.strftime("%x") for dt in dates]
        for ft in sorted(self.file_types):
            col = next(COLORS)
            ft_count = list(map(op.itemgetter(ft), code_counts))
            count_strs = [f"{c:,}" for c in ft_count]
            source = ColumnDataSource(
                data={"x": dates, "y": ft_count, "date": date_strs, "count": count_strs}
            )
            p.circle(
                "x",
                "y",
                legend_label=f"{ft} Code Count",
                fill_color="white",
                line_color=col,
                size=8,
                source=source,
            )
            p.line(
                "x",
                "y",
                legend_label=f"{ft} Code Count",
                line_color=col,
                line_width=2,
                source=source,
            )
        p.legend.location = "top_left"
        p.hover.tooltips = [("index", "$index"), ("date", "@date"), ("count", "@count")]
        save(p)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_dir", type=dir_arg)
    args = parser.parse_args()
    count = CodeCounter(args.repo_dir)
    print(datetime.utcnow().isoformat(sep=" ", timespec="seconds"), count.repo_dir)
    count.run()


if __name__ == "__main__":
    main()
