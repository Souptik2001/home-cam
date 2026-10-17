from collections.abc import Iterator
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Self

import psycopg

from amader_home_assistant.readiness import DatabaseReadinessChecker


class FakeConnection(AbstractContextManager["FakeConnection"]):
    def __init__(self, queries: list[str]) -> None:
        self.queries = queries

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def execute(self, query: str) -> None:
        self.queries.append(query)


def test_database_readiness_checks_the_configured_database() -> None:
    queries: list[str] = []
    connection_arguments: list[tuple[str, int]] = []

    def connect(database_url: str, *, connect_timeout: int) -> FakeConnection:
        connection_arguments.append((database_url, connect_timeout))
        return FakeConnection(queries)

    checker = DatabaseReadinessChecker(
        "postgresql://user:password@db/app", connector=connect
    )

    assert checker() is True
    assert connection_arguments == [("postgresql://user:password@db/app", 2)]
    assert queries == ["SELECT 1"]


def test_database_readiness_returns_false_when_database_is_unavailable() -> None:
    def connect(database_url: str, *, connect_timeout: int) -> FakeConnection:
        raise psycopg.OperationalError("database unavailable")

    checker = DatabaseReadinessChecker(
        "postgresql://user:password@db/app", connector=connect
    )

    assert checker() is False
