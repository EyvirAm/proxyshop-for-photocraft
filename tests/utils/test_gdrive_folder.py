"""
* Tests: Google Drive folder listing and template version resolution
"""
from __future__ import annotations

from typing import Any

import pytest

from src.utils import download


class FakeResponse:
    """Minimal ``requests.Response`` stand-in for the folder listing tests."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """Pretend every response is successful."""
        return

    def json(self) -> dict[str, Any]:
        """Return the canned JSON payload."""
        return self._payload


@pytest.fixture(autouse=True)
def clear_folder_cache() -> None:
    """Reset the module-level folder cache before each test."""
    download._drive_folder_cache.clear()


def test_list_gdrive_folder_maps_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """The listing maps each file name to its Google Drive ID."""
    calls: list[dict[str, Any]] = []

    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        """Fake get."""
        calls.append(kwargs["params"])
        return FakeResponse(
            {"files": [{"id": "file-id", "name": "pw-tf-front.psd"}]}
        )

    monkeypatch.setattr(download.requests, "get", fake_get)

    result = download.list_gdrive_folder("folder-id", "api-key")

    assert result == {"pw-tf-front.psd": "file-id"}
    assert calls[0]["q"] == "'folder-id' in parents and trashed=false"


def test_list_gdrive_folder_caches_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second call reuses the cached listing instead of hitting the API."""
    calls: list[dict[str, Any]] = []

    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        """Fake get."""
        calls.append(kwargs["params"])
        return FakeResponse({"files": [{"id": "file-id", "name": "normal.psd"}]})

    monkeypatch.setattr(download.requests, "get", fake_get)

    assert download.list_gdrive_folder("folder-id", "api-key") == {
        "normal.psd": "file-id"
    }
    assert download.list_gdrive_folder("folder-id", "api-key") == {
        "normal.psd": "file-id"
    }
    assert len(calls) == 1


def test_list_gdrive_folder_follows_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every page of a paginated folder listing is collected."""
    responses = [
        FakeResponse(
            {
                "files": [{"id": "first", "name": "normal.psd"}],
                "nextPageToken": "next-page",
            }
        ),
        FakeResponse({"files": [{"id": "second", "name": "planar.psd"}]}),
    ]

    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        """Fake get."""
        return responses.pop(0)

    monkeypatch.setattr(download.requests, "get", fake_get)

    result = download.list_gdrive_folder("folder-id", "api-key")

    assert result == {"normal.psd": "first", "planar.psd": "second"}


def test_list_gdrive_folder_without_api_key() -> None:
    """Without an API key the listing is skipped and empty."""
    assert download.list_gdrive_folder("folder-id", "") == {}


def test_app_template_prefers_folder_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file in the configured Drive folder wins over the manifest ID."""
    from src import _loader
    from src._state import AppConstants, AppEnvironment

    env = AppEnvironment()
    env.API_GOOGLE = "api-key"
    env.TEMPLATES_DRIVE_FOLDER = "folder-id"
    monkeypatch.setattr(
        _loader,
        "list_gdrive_folder",
        lambda folder_id, api_key: {"pw-tf-front.psd": "folder-file-id"},
    )

    template = _loader.AppTemplate(
        AppConstants(),
        env,
        _loader.TemplateFileInfo(id="manifest-id", templates={}),
        "pw-tf-front.psd",
        {},
        {},
    )

    assert template.google_drive_id == "folder-file-id"


def test_app_template_falls_back_to_manifest_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Templates missing from the folder keep using the manifest ID."""
    from src import _loader
    from src._state import AppConstants, AppEnvironment

    env = AppEnvironment()
    env.API_GOOGLE = "api-key"
    env.TEMPLATES_DRIVE_FOLDER = "folder-id"
    monkeypatch.setattr(
        _loader, "list_gdrive_folder", lambda folder_id, api_key: {}
    )

    template = _loader.AppTemplate(
        AppConstants(),
        env,
        _loader.TemplateFileInfo(id="manifest-id", templates={}),
        "pw-tf-front.psd",
        {},
        {},
    )

    assert template.google_drive_id == "manifest-id"


def _make_template(versions: dict[str, str]) -> Any:
    """Build an ``AppTemplate`` that resolves versions from Google Drive."""
    from src import _loader
    from src._state import AppConstants, AppEnvironment

    env = AppEnvironment()
    env.API_GOOGLE = ""
    env.TEMPLATES_DRIVE_FOLDER = ""
    return _loader.AppTemplate(
        AppConstants(),
        env,
        _loader.TemplateFileInfo(id="manifest-id", templates={}),
        "pw-tf-front.psd",
        {},
        versions,
    )


def test_check_for_update_prefers_description(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A version stored in the Drive description takes precedence."""
    from src import _loader

    monkeypatch.setattr(
        _loader,
        "get_gdrive_metadata",
        lambda *args, **kwargs: {
            "name": "pw-tf-front.psd",
            "size": 1,
            "description": "v1.0.1",
            "modifiedTime": "2026-10-26T00:00:00.000Z",
        },
    )
    template = _make_template({})

    assert template.check_for_update() is True
    assert template.update_version == "v1.0.1"


def test_check_for_update_uses_modified_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a description the file modification time becomes the version."""
    from src import _loader

    monkeypatch.setattr(
        _loader,
        "get_gdrive_metadata",
        lambda *args, **kwargs: {
            "name": "pw-tf-front.psd",
            "size": 1,
            "modifiedTime": "2026-10-26T00:00:00.000Z",
        },
    )
    template = _make_template({})

    assert template.check_for_update() is True
    assert template.update_version == "2026-10-26T00:00:00.000Z"


def test_check_for_update_without_version_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no version metadata the default version is used and no update shown."""
    from src import _loader

    monkeypatch.setattr(
        _loader,
        "get_gdrive_metadata",
        lambda *args, **kwargs: {"name": "pw-tf-front.psd", "size": 1},
    )
    template = _make_template({})

    assert template.check_for_update() is False
    assert template.update_version == "v1.0.0"
