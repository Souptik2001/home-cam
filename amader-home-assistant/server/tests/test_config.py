from amader_home_assistant.config import Settings


def test_database_url_can_be_loaded_from_environment(monkeypatch) -> None:
    database_url = "postgresql://test-user:test-pass@db/test-db"
    monkeypatch.setenv("DATABASE_URL", database_url)

    assert Settings().database_url == database_url
