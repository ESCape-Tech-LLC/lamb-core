"""Benchmark the field-parsing blocks of Chattti views on decoded request bodies.

Run from the Lamb checkout with the Chattti Python environment and dpath-fast installed:
    python -m tests.dpath.bench_chattti

For the unmodified release, run this same script against a clean export:
    baseline=$(mktemp -d)
    git archive v3.7.4 | tar -x -C "$baseline"
    PYTHONPATH="$baseline" python tests/dpath/bench_chattti.py

Each process measures the active Lamb backend and Pydantic on the same fixtures.
Inputs follow the API contract. In particular, a normal Pydantic field default
only handles a missing key, while Lamb's legacy default also handles bad input.
The timings exclude HTTP, decryption, JSON decoding and business logic.
"""

import base64
import os
import platform
import random
import statistics
import sys
import timeit
from datetime import datetime
from typing import Annotated

import pydantic
from django.conf import settings
from pydantic import BaseModel, BeforeValidator

from lamb.utils import dpath_value
from lamb.utils.transformers import transform_boolean, transform_datetime


# modules/main/views.py, MessageBadgeView.put
class Badge(BaseModel):
    value: int


def badge_fields(body, lookup=dpath_value):
    return lookup(body, "value", int)


def badge_result(model):
    return model.value


# modules/main/views.py, MessageListView.get
class MessagePage(BaseModel):
    lastid: int = 0
    limit: int = 10
    erase: bool = True
    is_signal: bool = False


def page_fields(body, lookup=dpath_value):
    return (
        lookup(body, "lastid", int, default=0),
        lookup(body, "limit", int, default=10),
        lookup(body, "erase", str, transform=transform_boolean, default=True),
        lookup(body, "is_signal", str, transform=transform_boolean, default=False),
    )


def page_result(model):
    return model.lastid, model.limit, model.erase, model.is_signal


# modules/main/views.py, MessageListView.post
DecodedMessage = Annotated[bytes, BeforeValidator(base64.urlsafe_b64decode)]


class SendMessage(BaseModel):
    message: DecodedMessage
    groupudid: str | None = None
    hash: str | None = None
    deduplication_id: str | None = None
    sender_content: DecodedMessage | None = None
    silent: bool = False
    is_signal: bool = False


def send_fields(body, lookup=dpath_value):
    return (
        lookup(body, "message", str, transform=base64.urlsafe_b64decode),
        lookup(body, "groupudid", str, default=None),
        lookup(body, "hash", str, default=None),
        lookup(body, "deduplication_id", str, default=None),
        lookup(body, "sender_content", str, transform=base64.urlsafe_b64decode, default=None),
        lookup(body, "silent", str, transform=transform_boolean, default=False),
        lookup(body, "is_signal", str, transform=transform_boolean, default=False),
    )


def send_result(model):
    return (
        model.message,
        model.groupudid,
        model.hash,
        model.deduplication_id,
        model.sender_content,
        model.silent,
        model.is_signal,
    )


# modules/info_channel/views.py, InfoPostListView.post
def parse_publish_at(value):
    return transform_datetime(value, __format="iso")


class Cursor(BaseModel):
    publish_at: Annotated[datetime, BeforeValidator(parse_publish_at)]
    post_id: int


class Feed(BaseModel):
    limit: int = 30
    cursor: Cursor | None = None


def feed_fields(body, lookup=dpath_value):
    limit = lookup(body, "limit", int, default=30)
    cursor = lookup(body, "cursor", dict, allow_none=True, default=None)
    if cursor is not None:
        cursor = {
            "publish_at": lookup(cursor, "publish_at", str, transform=parse_publish_at),
            "post_id": lookup(cursor, "post_id", int),
        }
    return max(1, min(limit, 100)), cursor


def feed_result(model):
    cursor = model.cursor
    if cursor is not None:
        cursor = {"publish_at": cursor.publish_at, "post_id": cursor.post_id}
    return max(1, min(model.limit, 100)), cursor


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.test_settings")
    settings.LAMB_DPATH_DICT_ENGINE = "reduce"
    active_backend = sys.modules[dpath_value.__module__]
    active_backend.adapt_dict_impl()
    assert active_backend._impl_dict is active_backend._impl_dict_reduce

    content = base64.urlsafe_b64encode(bytes(range(256))).decode("ascii")
    direct_message = {"message": content, "hash": "test-peer"}
    cases = [
        ("badge", Badge, badge_fields, badge_result, {"value": 7}),
        (
            "messages GET, all fields",
            MessagePage,
            page_fields,
            page_result,
            {"lastid": 100, "limit": 20, "erase": False, "is_signal": True},
        ),
        ("messages GET, empty", MessagePage, page_fields, page_result, {}),
        ("messages POST, 2/7 fields", SendMessage, send_fields, send_result, direct_message),
        (
            "messages POST, 6/7 fields",
            SendMessage,
            send_fields,
            send_result,
            {
                **direct_message,
                "deduplication_id": "test-id",
                "sender_content": content,
                "silent": True,
                "is_signal": False,
            },
        ),
        (
            "feed, nested cursor",
            Feed,
            feed_fields,
            feed_result,
            {"limit": 20, "cursor": {"post_id": 123, "publish_at": "2026-11-25T11:00:00Z"}},
        ),
    ]
    statements = {
        "dpath_value": "fields(body, lookup)",
        "validate+read": "read(model.model_validate(body))",
        "validate": "model.model_validate(body)",
        "read": "read(parsed)",
    }
    repeats, iterations = 9, 20_000
    print(f"CPython {platform.python_version()}, {platform.machine()}, Pydantic {pydantic.__version__}")
    print(f"{active_backend.__file__}, engine=reduce")
    print(f"Median microseconds/body ({repeats} runs x {iterations} iterations per case)")
    print(f"{'case':<28}" + "".join(f"{label:>15}" for label in statements))
    rng = random.Random(100)
    for name, model, fields, read, body in cases:
        parsed = model.model_validate(body)
        scope = {"model": model, "body": body, "read": read, "fields": fields, "parsed": parsed}
        if fields(body, dpath_value) != read(parsed):
            raise AssertionError(f"Results differ for {name}")
        scope["lookup"] = dpath_value
        timers = {label: timeit.Timer(stmt, globals=scope) for label, stmt in statements.items()}
        samples = {label: [] for label in timers}
        for timer in timers.values():
            timer.timeit(number=1_000)
        order = list(timers)
        for _ in range(repeats):
            rng.shuffle(order)
            for label in order:
                elapsed = timers[label].timeit(number=iterations)
                samples[label].append(elapsed * 1_000_000 / iterations)
        print(f"{name:<28}" + "".join(f"{statistics.median(times):15.3f}" for times in samples.values()))


if __name__ == "__main__":
    main()
