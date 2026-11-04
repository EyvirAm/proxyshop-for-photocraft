"""
* Utils: Downloads and Updates
"""
from __future__ import annotations

import shutil
from collections.abc import Callable
from logging import getLogger
from pathlib import Path
from threading import Lock

import requests
import yarl
from omnitils.fetch import download_file
from omnitils.files import get_temporary_file
from omnitils.files.archive import unpack_archive

from src import DEFAULT_HEADERS

_logger = getLogger(__name__)

_drive_folder_cache: dict[tuple[str, str], dict[str, str]] = {}
_drive_folder_lock: Lock = Lock()


def list_gdrive_folder(folder_id: str, api_key: str) -> dict[str, str]:
    """List the files of a shared Google Drive folder, mapped by name.

    Templates are matched by file name, so re-uploading a template to the
    folder changes the download source without editing ``manifest.yml``.

    Args:
        folder_id: ID of the Google Drive folder.
        api_key: Google Drive API key.

    Returns:
        A dictionary mapping each file name to its Google Drive file ID.
    """
    if not folder_id or not api_key:
        return {}

    cache_key = (folder_id, api_key)
    if (cached := _drive_folder_cache.get(cache_key)) is not None:
        return cached

    with _drive_folder_lock:
        # Another thread may have listed the folder while we waited.
        if (cached := _drive_folder_cache.get(cache_key)) is not None:
            return cached
        files = _fetch_gdrive_folder(folder_id, api_key)
        if files:
            _drive_folder_cache[cache_key] = files
        return files


def get_gdrive_metadata(file_id: str, api_key: str) -> dict[str, Any] | None:
    """Get the metadata of a Google Drive file.

    Requests ``modifiedTime`` in addition to the fields used by the updater, so
    a replaced file can still be detected when its description has no version.

    Args:
        file_id: ID of the Google Drive file.
        api_key: Google Drive API key.

    Returns:
        The file metadata, or None if it could not be fetched.
    """
    if not file_id or not api_key:
        return None
    try:
        res = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={
                "alt": "json",
                "fields": "description,name,size,modifiedTime",
                "key": api_key,
            },
            headers=DEFAULT_HEADERS,
            timeout=30,
        )
        if res.status_code != 200:
            return None
        data = res.json()
    except (requests.RequestException, ValueError):
        _logger.exception(f"Failed to fetch Google Drive metadata for '{file_id}'")
        return None
    return data if isinstance(data, dict) else None


def _fetch_gdrive_folder(folder_id: str, api_key: str) -> dict[str, str]:
    """Fetch every page of a Google Drive folder listing."""
    files: dict[str, str] = {}
    page_token: str | None = None
    try:
        while True:
            params: dict[str, str | int] = {
                "q": f"'{folder_id}' in parents and trashed=false",
                "fields": "nextPageToken,files(id,name)",
                "pageSize": 1000,
                "key": api_key,
            }
            if page_token:
                params["pageToken"] = page_token

            res = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=30,
            )
            res.raise_for_status()
            data = res.json()
            for item in data.get("files", []):
                name = item.get("name")
                file_id = item.get("id")
                if name and file_id:
                    files[name] = file_id
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    except (requests.RequestException, ValueError):
        _logger.exception(f"Failed to list Google Drive folder '{folder_id}'")
        return files

    return files


def download_cloudfront(
    url: yarl.URL, path: Path, callback: Callable[[int, int], None] | None = None
) -> bool:
    """Download a template from cloudfront cached Amazon S3 bucket.

    Args:
        url: URL to S3/cloudfront hosted file.
        path: Path to save the archive.
        callback: Callback function to update progress.

    Returns:
        True if download is successful, otherwise False.
    """
    # Get a temp file
    temp_path = get_temporary_file(path=path, ext=".amzn")

    # Start the download
    try:
        download_file(
            url=url, path=temp_path, callback=callback, header=DEFAULT_HEADERS
        )
        shutil.move(temp_path, path)
        unpack_archive(path)
    except (requests.RequestException, FileExistsError, FileNotFoundError):
        return False
    return True
