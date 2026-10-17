from amader_home_assistant.config import Settings


def test_sqlite_is_the_durable_default() -> None:
    assert (
        Settings(_env_file=None).database_url
        == "sqlite:///./data/amader-home-assistant.db"
    )


def test_database_url_can_be_loaded_from_environment(monkeypatch) -> None:
    database_url = "postgresql://test-user:password@db/test-db"
    monkeypatch.setenv("DATABASE_URL", database_url)

    assert Settings(_env_file=None).database_url == database_url


def test_structured_security_and_cors_settings_load_from_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "DOORBELL_HMAC_SECRETS", '{"front-door":"secret","back-door":"other"}'
    )
    monkeypatch.setenv("PAIRING_CODE", "pair-code")
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://app.example.test"]')

    settings = Settings(_env_file=None)

    assert settings.doorbell_hmac_secrets == {
        "front-door": "secret",
        "back-door": "other",
    }
    assert settings.pairing_code.get_secret_value() == "pair-code"
    assert settings.allowed_origins == ["https://app.example.test"]
