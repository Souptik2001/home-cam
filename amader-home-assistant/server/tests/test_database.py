from sqlalchemy import inspect, text

from amader_home_assistant.database import build_engine, create_schema


def test_sqlite_enables_integrity_and_concurrency_pragmas(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'doorbell.sqlite3'}")

    with engine.connect() as connection:
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
        busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()

    assert foreign_keys == 1
    assert journal_mode.lower() == "wal"
    assert busy_timeout >= 5000


def test_create_schema_restores_event_pagination_index(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'doorbell.sqlite3'}")
    create_schema(engine)

    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ix_doorbell_events_pagination"))

    create_schema(engine)

    indexes = {
        index["name"]: tuple(index["column_names"])
        for index in inspect(engine).get_indexes("doorbell_events")
    }
    assert indexes["ix_doorbell_events_pagination"] == (
        "occurred_at",
        "received_at",
        "id",
    )
