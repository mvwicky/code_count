import os
from functools import partial
from pathlib import Path

import click
from click import Context, Parameter

from .code_count import Counter
from .plot import Plotter
from .utils import Log

CWD = Path.cwd()


ResolvedDir = partial(click.Path, file_okay=False, resolve_path=True)


def validate_repo_dir(ctx: Context, param: Parameter, value: str):
    if not os.path.isdir(os.path.join(value, ".git")):
        raise click.BadParameter("Expected a git repo.", ctx, param)
    return value


@click.command(name="ccount")
@click.argument("repo-dir", type=ResolvedDir(), callback=validate_repo_dir)
@click.option(
    "--limit",
    "-n",
    type=click.IntRange(0),
    default=50,
    metavar="N",
    help="Limit graphed commits to `N`",
    show_default=True,
)
@click.option(
    "--branch",
    "-b",
    default="master",
    metavar="BRANCH",
    help="Find commits from `BRANCH`",
    show_default=True,
)
@click.option(
    "--verbose/--not-verbose", "-v/ ", default=False, help="Give more verbose output."
)
@click.option(
    "--collapse/--no-collapse",
    default=True,
    help="Only keep one commit per day.",
    show_default=True,
)
@click.option("--show/--no-show", default=False, help="Open the generated plot.")
@click.option(
    "--output-dir",
    "-o",
    default=str(CWD / "out"),
    type=ResolvedDir(),
    help="Where to write the output files.",
)
def main(
    repo_dir: str,
    limit: int,
    branch: str,
    verbose: bool,
    collapse: bool,
    show: bool,
    output_dir: str,
):
    """Graph lines of code."""
    name = ".".join([os.path.split(repo_dir)[1], "html"])
    output_file = os.path.join(output_dir, name)
    log = Log.create(verbose)
    log(f"Examining repository {repo_dir}", fg="green")
    counter = Counter.create(repo_dir, log)
    counts = counter.count(limit, branch, collapse)
    plt = Plotter.create(output_file)
    plt.plot_counts(counts)
    log(f"Wrote {output_file}", fg="green")
    if show:
        plt.open_fig()


if __name__ == "__main__":
    main()
