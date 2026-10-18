from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Protocol

import psycopg


class Connection(Protocol):
    def execute(self, query: str) -> object: ...


Connector = Callable[..., AbstractContextManager[Connection]]


class DatabaseReadinessChecker:
    def __init__(
        self,
        database_url: str,
        *,
        connector: Connector = psycopg.connect,
        connect_timeout: int = 2,
    ) -> None:
        self._database_url = database_url
        self._connector = connector
        self._connect_timeout = connect_timeout

    def __call__(self) -> bool:
        try:
            with self._connector(
                self._database_url, connect_timeout=self._connect_timeout
            ) as connection:
                connection.execute("SELECT 1")
        except psycopg.Error:
            return False
        return True
