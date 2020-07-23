import abc
import gzip
from pathlib import Path
from typing import ClassVar

import attr


class AbstractCompressionFormat(abc.ABC):
    @abc.abstractmethod
    def compress(self, data: bytes) -> bytes:
        ...

    @abc.abstractmethod
    def decompress(self, data: bytes) -> bytes:
        ...


class GzipCompression(AbstractCompressionFormat):
    def __init__(self, compresslevel: int = 9):
        self.compresslevel = compresslevel

    def compress(self, data: bytes) -> bytes:
        return gzip.compress(data, compresslevel=self.compresslevel)

    def decompress(self, data: bytes) -> bytes:
        return gzip.decompress(data)


class NoopCompression(AbstractCompressionFormat):
    def compress(self, data: bytes) -> bytes:
        return data

    def decompress(self, data: bytes) -> bytes:
        return data


@attr.s(auto_attribs=True, slots=True)
class BaseCompressedFile(object):
    fmt: ClassVar[AbstractCompressionFormat] = NoopCompression()
    _path: Path

    def read_text(self, encoding: str = None, errors: str = None) -> str:
        return self.read_bytes().decode(encoding, errors)

    def write_text(self, text: str, encoding: str = None, errors: str = None) -> int:
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
