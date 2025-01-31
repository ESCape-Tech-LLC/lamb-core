from __future__ import annotations

import dataclasses
from typing import Optional, Self

# Lamb Framework
from lamb.exc import InvalidParamTypeError, InvalidParamValueError, RequestRangeError


@dataclasses.dataclass(frozen=True)
class BytesRange:
    bytes_start: Optional[int] = None
    bytes_end: Optional[int] = None

    @property
    def slice(self) -> slice:  # noqa: A003
        if self.bytes_start is None:
            return slice(self.bytes_end, None)
        else:
            return slice(self.bytes_start, self.bytes_end + 1 if self.bytes_end is not None else None)

    def __str__(self):
        match self.bytes_start, self.bytes_end:
            case None, None:
                return "none"
            case bs, None:
                return f"bytes={bs}-"
            case None, be:
                return f"bytes={be}"
            case bs, be:
                return f"bytes={bs}-{be}"

    def __format__(self, format_spec):
        return str(self).__format__(format_spec)

    @classmethod
    def parse_bytes_range(cls, value: str, safe: bool = True) -> Optional[Self]:
        try:
            if not isinstance(value, str):
                raise InvalidParamTypeError("Invalid object for bytes range parsing")

            value = value.lower()
            value = "".join(value.split())

            if "none" in value:
                return BytesRange(bytes_start=None, bytes_end=None)

            if not value.startswith("bytes="):
                return InvalidParamValueError(f"Could not parse bytes range: {value}")
            value = (value[6:]).strip()

            components = value.split("-")
            if len(components) != 2:
                raise InvalidParamValueError(f"Invalid bytes range structure: {value}")

            if len(components[0]) > 0:
                bytes_start = int(components[0])
                bytes_end = int(components[1]) if len(components[1]) > 0 else None
            else:
                bytes_start = None
                bytes_end = -1 * int(components[1]) if len(components[1]) > 0 else None
            if bytes_start is not None and bytes_end is not None and bytes_end < bytes_start:
                raise InvalidParamValueError(f"Invalid bytes range: {value}")
            return BytesRange(bytes_start=bytes_start, bytes_end=bytes_end)
        except Exception as e:
            if safe:
                return BytesRange(bytes_start=None, bytes_end=None)
            else:
                raise e

    def content_range(self, length: int) -> Optional[str]:
        if self.bytes_start is None and self.bytes_end is None:
            return None
        match self.bytes_start, self.bytes_end:
            case None, None:
                return None
            case bs, None:
                if bs >= length:
                    raise RequestRangeError
                return f"bytes {bs}-{length - 1}/{length}"
            case None, be:
                return f"bytes {max(length + be, 0)}-{length - 1}/{length}"
            case bs, be:
                if be >= length:
                    be = length - 1
                return f"bytes {bs}-{be}/{length}"

    def content_length(self, full_length: int) -> int:
        if self.bytes_start is None and self.bytes_end is None:
            return full_length
        match self.bytes_start, self.bytes_end:
            case None, None:
                return full_length
            case bs, None:
                if bs >= full_length:
                    raise RequestRangeError
                return full_length - bs
            case None, be:
                return min(-be, full_length)
            case bs, be:
                if be >= full_length:
                    be = full_length - 1
                return be - bs + 1

        return -100


# def tf_bytes_range(value: Optional[str]) -> Optional[BytesRange]:
#     if value is None:
#         return None
#     return BytesRange.parse_bytes_range(value, safe=True)
#
#
# l = [1, 2, 3]
#
# assert l[tf_bytes_range('bytes=0-').slice] == [1, 2, 3]
# assert l[tf_bytes_range('bytes=1-').slice] == [2, 3]
# assert l[tf_bytes_range('bytes=1-2').slice] == [2, 3]
# assert l[tf_bytes_range('bytes=-1').slice] == [3]
# assert l[tf_bytes_range('bytes=2-').slice] == [3]
# assert l[tf_bytes_range('bytes=none').slice] == [1, 2, 3]
# assert l[tf_bytes_range('bytes=-1-2').slice] == [1, 2, 3]
#
# # check over content-range
# pairs = [
#     ('bytes=0-', 'bytes 0-1023/1024'),
#     ('bytes=1-', 'bytes 1-1023/1024'),
#     ('bytes=1-20', 'bytes 1-20/1024'),
#     ('bytes=-', None),
#     ('bytes=-1-2', None),
#     ('bytes=-1', 'bytes 1023-1023/1024'),
#     ('bytes=-10', 'bytes 1014-1023/1024'),
#     ('bytes=0-1024', 'bytes 0-1023/1024'),
#     ('bytes=-1000', 'bytes 24-1023/1024'),
#     ('bytes=-10000', 'bytes 0-1023/1024'),
#     ('bytes=10000-', RequestRangeError),
#     ('bytes=1000-', 'bytes 1000-1023/1024'),
#     ('bytes=1024-', RequestRangeError),
# ]
#
# for src, target in pairs:
#     br = BytesRange.parse_bytes_range(src, safe=True)
#     try:
#         sample = br.content_range(1024)
#     except Exception as e:
#         sample = e.__class__
#     print(f'"{src}":"{br}":{target == sample} {target} : {sample}')
#     assert sample == target
#
# # check over length
# print('checking for content-length')
# pairs = [
#     ('bytes=0-', 1024),
#     ('bytes=1-', 1023),
#     ('bytes=1-20', 20),
#     ('bytes=-', 1024),
#     ('bytes=-1-2', 1024),
#     ('bytes=-1', 1),
#     ('bytes=-10', 10),
#     ('bytes=0-1024', 1024),
#     ('bytes=-1000', 1000),
#     ('bytes=-10000', 1024),
#     ('bytes=10000-', RequestRangeError),
#     ('bytes=1000-', 24),
#     ('bytes=1024-', RequestRangeError),
# ]
# for src, target in pairs:
#     br = BytesRange.parse_bytes_range(src, safe=True)
#     try:
#         sample = br.content_length(1024)
#     except Exception as e:
#         print(e)
#         sample = e.__class__
#     print(f'"{src}":"{br}":{target == sample} {target} : {sample}')
#     assert sample == target

# import requests
# from lamb.utils import compact
#
# url = 'http://localhost:8000/files/72dc5d7a-c718-40bf-8a50-59b82efdf98a'
# variants = [
#     None,
#     'bytes=0-',
#     'bytes=1-',
#     'bytes=1-20',
#     'bytes=-',
#     'bytes=-1-2',
#     'bytes=-1',
#     'bytes=-10',
#     'bytes=0-1024',
#     'bytes=-1000',
#     'bytes=-10000',
#     'bytes=10000-',
#     'bytes=1000-',
#     'bytes=1024-',
# ]
#
# for r_header in variants:
#     res1 = requests.get(url, headers=compact({'Range': r_header}))
#     res2 = requests.get(url, headers=compact({'Range': r_header, 'X-Lamb-Device-Platform': 'ios'}))
#
#     print(f'res1: {res1}, {res1.headers}')
#     print(f'res2: {res2}, {res2.headers}')
#     assert res1.status_code == res2.status_code
#     if res1.status_code != 416:
#         for h in ['Content-Type', 'Content-Length', 'Accept-Ranges', 'Content-Range']:
#             assert res1.headers.get(h, None) == res2.headers.get(h, None)
