import os
import time

import click
from click import Context, Parameter

from .code_count import CodeCounter


def validate_repo_dir(ctx: Context, param: Parameter, value: str):
    cts = {os.path.split(p)[1] for p in os.listdir(value)}
    if ".git" not in cts:
        raise click.BadParameter("Expected a git repo.", ctx, param)
    return value


@click.command(name="ccount")
@click.argument(
    "repo-dir",
    type=click.Path(file_okay=False, resolve_path=True),
    callback=validate_repo_dir,
)
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
    "--collapse/--no-collapse", default=True, help="Only keep one commit per day."
)
def main(repo_dir: str, limit: int, branch: str, verbose: bool, collapse: bool):
    """Graph lines of code."""
    start = time.perf_counter()
    counter = CodeCounter(repo_dir, verbose=verbose)
    counter.run(limit, branch, collapse)
    elapsed = time.perf_counter() - start
    click.secho(f"Elpased: {elapsed:.2f}")


if __name__ == "__main__":
    main()
