import abc
import gzip
from pathlib import Path
from typing import ClassVar

import attr

ENCODING = "utf-8"
ERRORS = "strict"


class AbstractCompressionFormat(abc.ABC):
    @property
    def name(self) -> str:
        return type(self).__name__.replace("CompressionFormat", "")

    @abc.abstractmethod
    def compress(self, data: bytes) -> bytes:
        ...

    @abc.abstractmethod
    def decompress(self, data: bytes) -> bytes:
        ...


class GzipCompression(AbstractCompressionFormat):
    def __init__(self, compresslevel: int = 9):
        self.compresslevel = compresslevel

    @property
    def name(self) -> str:
        return type(self).__name__.replace("Compression", "")

    def compress(self, data: bytes) -> bytes:
        return gzip.compress(data, compresslevel=self.compresslevel)

    def decompress(self, data: bytes) -> bytes:
        return gzip.decompress(data)


class NoopCompression(AbstractCompressionFormat):
    @property
    def name(self) -> str:
        return type(self).__name__.replace("Compression", "")

    def compress(self, data: bytes) -> bytes:
        return data

    def decompress(self, data: bytes) -> bytes:
        return data


@attr.s(auto_attribs=True, slots=True, repr=False)
class BaseCompressedFile(object):
    fmt: ClassVar[AbstractCompressionFormat] = NoopCompression()
    _path: Path

    def __repr__(self) -> str:
        fmt_name = self.fmt.name
        return f"{fmt_name}({self._path})"

    def __getattr__(self, name: str):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return getattr(self._path, name)

    def read_text(self, encoding: str = ENCODING, errors: str = ERRORS) -> str:
        return self.read_bytes().decode(encoding, errors)

    def write_text(
        self, text: str, encoding: str = ENCODING, errors: str = ERRORS
    ) -> int:
        self.write_bytes(text.encode(encoding, errors))

    def read_bytes(self) -> bytes:
        return self.fmt.decompress(self._path.read_bytes())

    def write_bytes(self, data: bytes) -> int:
        n = len(data)
        self._path.write_bytes(self.fmt.compress(data))
        return n


class NoopCompressedFile(BaseCompressedFile):
    pass


class GzipCompressedFile(BaseCompressedFile):
    fmt = GzipCompression()
