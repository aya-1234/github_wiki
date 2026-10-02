from pathlib import Path

from photo_organizer.config.settings import Settings


def test_settings_load_and_save(tmp_path: Path) -> None:
    config = tmp_path / ".env"
    config.write_text(
        "SOURCE_PATH=/photos/in\nDESTINATION_PATH=/photos/out\nDEFAULT_MODE=move\n"
        "MOVE_WARNING=false\nSUPPORTED_EXTENSIONS=.JPG, png\nDATE_FALLBACK=skip\n",
        encoding="utf-8",
    )

    settings = Settings.load(config)

    assert settings.source_path == Path("/photos/in")
    assert settings.default_mode == "move"
    assert not settings.move_warning
    assert settings.supported_extensions == (".jpg", ".png")
    assert settings.date_fallback == "skip"
    settings.save()
    assert "DEFAULT_MODE=move" in config.read_text(encoding="utf-8")


def test_invalid_mode_is_rejected() -> None:
    try:
        Settings(default_mode="delete")
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported mode must be rejected")
