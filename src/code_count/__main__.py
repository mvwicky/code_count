import os
import time
from typing import Union

import click

from .code_count import CodeCounter


def validate_repo_dir(ctx: click.Context, param: click.Parameter, value: str):
    cts = {os.path.split(p)[1] for p in os.listdir(value)}
    if ".git" not in cts:
        raise click.BadParameter("Expected a git repo.", ctx, param)
    return value


def validate_limit(
    ctx: click.Context, param: click.Parameter, value: Union[int, float]
) -> Union[int, float]:
    if value <= 0:
        raise click.BadParameter("`limit` must be greater than 0.")
    if value <= 1.0:
        return value
    else:
        return int(value)


@click.command(name="ccount")
@click.argument(
    "repo-dir",
    type=click.Path(file_okay=False, resolve_path=True),
    callback=validate_repo_dir,
)
@click.option("--limit", "-n", type=int, default=50)
@click.option("--branch", "-b", default="master")
@click.option("--safe/--unsafe", " /-u", default=True)
def main(repo_dir: str, limit: Union[int, float], branch: str, safe: bool):
    start = time.perf_counter()
    counter = CodeCounter(repo_dir)
    click.secho(f"Examining repository {counter.repo_dir}", fg="green")
    counter.run(limit, branch, safe)
    click.secho(f"Wrote {counter.output_file}", fg="green")
    elapsed = time.perf_counter() - start
    click.secho(f"Elpased: {elapsed:.2f}")


if __name__ == "__main__":
    main()
