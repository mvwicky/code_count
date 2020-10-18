import hashlib
import os
import random
from pathlib import Path
from typing import Optional, Type, Union

import attr
import click

_PathTypes = Union[os.PathLike, str]


def ntext(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def get_cache_dir(name: str) -> Path:
    _default_xdg = os.path.expanduser(os.path.join("~", ".cache"))
    xdg = Path(os.environ.get("XDG_CACHE_HOME", _default_xdg))
    cache_d = xdg / name
    if not cache_d.is_dir():
        cache_d.mkdir(parents=True)
    return cache_d


@attr.s(auto_attribs=True, slots=True)
class LazyCache(object):
    name: str
    ensure: bool = True
    _value: Optional[Path] = attr.ib(init=False, default=None)

    @property
    def location(self) -> Path:
        if self._value is None:
            self._value = get_cache_dir(self.name)
            if self.ensure and not self._value.is_dir():
                self._value.mkdir(parents=True)
        return self._value

    def __truediv__(self, other: _PathTypes) -> Path:
        if not isinstance(other, str):
            return NotImplemented
        return self.location / other

    def joinpath(self, *parts: _PathTypes) -> Path:
        return self.location.joinpath(*parts)


def hash_path(p: Path, hasher: Type["hashlib._Hash"] = hashlib.md5) -> str:
    name = p.name
    digest = hasher(bytes(p)).hexdigest()
    return "-".join([name, digest])


def true_with_prob(p: float) -> bool:
    x = random.uniform(0, 1)
    return x < p


@attr.s(auto_attribs=True, slots=True)
class Log(object):
    _verbose: bool
    prefix: str = attr.ib(default=">>>")

    @classmethod
    def create(cls, verbose: bool) -> "Log":
        return cls(verbose)

    def verbose(self, msg: str, **kwargs):
        if self._verbose:
            self.log(msg, **kwargs)

    def log(self, msg: str, **kwargs):
        click.secho(" ".join([self.prefix, msg]), **kwargs)

    def __call__(self, msg: str, **kwargs):
        self.log(msg, **kwargs)
