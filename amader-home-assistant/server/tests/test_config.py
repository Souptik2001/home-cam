import pytest
from pydantic import ValidationError

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


def test_camera_url_is_restricted_to_the_approved_https_origin() -> None:
    assert (
        Settings(
            _env_file=None,
            camera_base_url="https://camera.souptik.dev/#pi_cam_2",
        ).camera_base_url
        == "https://camera.souptik.dev/#pi_cam_2"
    )

    for url in (
        "http://camera.souptik.dev/#pi_cam_2",
        "https://attacker.example/#pi_cam_2",
        "https://camera.souptik.dev/",
    ):
        with pytest.raises(ValidationError, match="approved HTTPS origin"):
            Settings(_env_file=None, camera_base_url=url)


def test_web_push_vapid_public_key_accepts_url_safe_uncompressed_p256_key() -> None:
    key = "B" + "a" * 86

    assert (
        Settings(
            _env_file=None, web_push_vapid_public_key=key
        ).web_push_vapid_public_key
        == key
    )


def test_web_push_vapid_public_key_rejects_cli_labelled_output() -> None:
    with pytest.raises(ValidationError, match="87-character URL-safe"):
        Settings(
            _env_file=None,
            web_push_vapid_public_key="Application Server Key = B" + "a" * 86,
        )


def test_web_push_allowed_hosts_rejects_wildcards_and_ip_literals() -> None:
    for host in ("*.push.example.com", "127.0.0.1", "[::1]"):
        with pytest.raises(ValidationError, match="exact DNS hostnames"):
            Settings(_env_file=None, web_push_allowed_hosts=[host])
