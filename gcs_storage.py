"""
Google Cloud Storage helper for Coach Dashboard.

Provides upload/download of ETL run output, cache files, and runs.json
to a GCS bucket so that Streamlit Cloud (read-only filesystem) can
run the full ETL pipeline and persist results.

Credential lookup (same 3-tier order as gsheets_writer):
  1. GOOGLE_SA_JSON_PATH environment variable  (local file path)
  2. secrets/service_account.json              (local default)
  3. st.secrets["gcp_service_account"]         (Streamlit Cloud)
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import List, Optional

BUCKET_NAME = "coach-dashboard-data"

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = PROJECT_ROOT / "etl" / "cache"
DEFAULT_SA_PATH = PROJECT_ROOT / "secrets" / "service_account.json"

# Files that live inside a run folder
RUN_FILES = ["coach_eligibility.xlsx", "enums.xlsx", "deals_flat.csv"]

# Files that live in etl/cache/
CACHE_FILES = [
    "na_contacts.json",
    "contact_deal_links.json",
    "deal_ids.json",
    "deals_raw.json",
    "owners.json",
]


def _get_sa_info() -> Optional[dict]:
    """Return service-account info dict, or None if unavailable."""
    sa_path = os.environ.get("GOOGLE_SA_JSON_PATH")
    if not sa_path and DEFAULT_SA_PATH.is_file():
        sa_path = str(DEFAULT_SA_PATH)

    if sa_path and os.path.isfile(sa_path):
        with open(sa_path, "r", encoding="utf-8") as f:
            return json.load(f)

    try:
        import streamlit as st
        sa_info = st.secrets["gcp_service_account"]
        return dict(sa_info)
    except Exception:
        pass

    return None


def get_gcs_client():
    """
    Return an authenticated google.cloud.storage.Client.

    Raises EnvironmentError when no credentials are found.
    """
    from google.cloud import storage
    from google.oauth2.service_account import Credentials

    sa_info = _get_sa_info()
    if sa_info is None:
        raise EnvironmentError(
            "Google Service Account niet gevonden voor GCS.\n\n"
            "Lokaal: plaats service_account.json in secrets/ of stel GOOGLE_SA_JSON_PATH in.\n"
            "Streamlit Cloud: voeg gcp_service_account toe aan Settings → Secrets."
        )

    credentials = Credentials.from_service_account_info(sa_info)
    return storage.Client(credentials=credentials, project=sa_info.get("project_id"))


def _bucket():
    """Return the GCS bucket object."""
    return get_gcs_client().bucket(BUCKET_NAME)


def gcs_available() -> bool:
    """Check whether GCS credentials are configured (does not call the API)."""
    return _get_sa_info() is not None


# -------------------------------------------------------------------------
# Run files  (data/<run_id>/ ↔ gs://bucket/runs/<run_id>/)
# -------------------------------------------------------------------------

def upload_run(run_id: str, run_dir: Optional[Path] = None) -> List[str]:
    """Upload all run output files to GCS. Returns list of uploaded blob names."""
    if run_dir is None:
        run_dir = DATA_DIR / run_id

    bucket = _bucket()
    uploaded = []

    for fname in RUN_FILES:
        local = run_dir / fname
        if not local.is_file():
            continue
        blob_name = f"runs/{run_id}/{fname}"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(local))
        uploaded.append(blob_name)

    return uploaded


def download_run(run_id: str, target_dir: Optional[Path] = None) -> bool:
    """
    Download run files from GCS into a local directory.

    Returns True if at least coach_eligibility.xlsx was downloaded.
    """
    if target_dir is None:
        target_dir = DATA_DIR / run_id

    target_dir.mkdir(parents=True, exist_ok=True)
    bucket = _bucket()
    got_eligibility = False

    for fname in RUN_FILES:
        blob_name = f"runs/{run_id}/{fname}"
        blob = bucket.blob(blob_name)
        if not blob.exists():
            continue
        local = target_dir / fname
        blob.download_to_filename(str(local))
        if fname == "coach_eligibility.xlsx":
            got_eligibility = True

    return got_eligibility


# -------------------------------------------------------------------------
# runs.json  (data/runs.json ↔ gs://bucket/runs.json)
# -------------------------------------------------------------------------

def upload_runs_json(local_path: Optional[Path] = None) -> None:
    """Upload runs.json to GCS."""
    if local_path is None:
        local_path = DATA_DIR / "runs.json"
    if not local_path.is_file():
        return
    bucket = _bucket()
    blob = bucket.blob("runs.json")
    blob.upload_from_filename(str(local_path))


def download_runs_json(target_path: Optional[Path] = None) -> bool:
    """Download runs.json from GCS. Returns True if downloaded."""
    if target_path is None:
        target_path = DATA_DIR / "runs.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    bucket = _bucket()
    blob = bucket.blob("runs.json")
    if not blob.exists():
        return False
    blob.download_to_filename(str(target_path))
    return True


def upload_runs_json_bytes(data: dict) -> None:
    """Upload runs.json content directly from a dict (avoids local write)."""
    bucket = _bucket()
    blob = bucket.blob("runs.json")
    blob.upload_from_string(
        json.dumps(data, indent=2, default=str),
        content_type="application/json",
    )


def download_runs_json_data() -> Optional[dict]:
    """Download and return runs.json content as dict, or None."""
    bucket = _bucket()
    blob = bucket.blob("runs.json")
    if not blob.exists():
        return None
    raw = blob.download_as_text()
    return json.loads(raw)


# -------------------------------------------------------------------------
# List runs in bucket
# -------------------------------------------------------------------------

def list_runs() -> List[str]:
    """List all run_id prefixes stored in GCS."""
    bucket = _bucket()
    blobs = bucket.list_blobs(prefix="runs/", delimiter="/")
    # Consume the iterator to populate prefixes
    _ = list(blobs)
    run_ids = []
    for prefix in blobs.prefixes:
        # prefix looks like "runs/20260128_075845/"
        parts = prefix.strip("/").split("/")
        if len(parts) == 2:
            run_ids.append(parts[1])
    return sorted(run_ids, reverse=True)


# -------------------------------------------------------------------------
# Cache files  (etl/cache/ ↔ gs://bucket/cache/)
# -------------------------------------------------------------------------

def upload_cache_files(cache_dir: Optional[Path] = None) -> List[str]:
    """Upload ETL cache files to GCS. Returns list of uploaded blob names."""
    if cache_dir is None:
        cache_dir = CACHE_DIR

    bucket = _bucket()
    uploaded = []

    for fname in CACHE_FILES:
        local = cache_dir / fname
        if not local.is_file():
            continue
        blob_name = f"cache/{fname}"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(local))
        uploaded.append(blob_name)

    return uploaded


def download_cache_files(target_dir: Optional[Path] = None) -> List[str]:
    """Download ETL cache files from GCS. Returns list of downloaded file names."""
    if target_dir is None:
        target_dir = CACHE_DIR

    target_dir.mkdir(parents=True, exist_ok=True)
    bucket = _bucket()
    downloaded = []

    for fname in CACHE_FILES:
        blob_name = f"cache/{fname}"
        blob = bucket.blob(blob_name)
        if not blob.exists():
            continue
        local = target_dir / fname
        blob.download_to_filename(str(local))
        downloaded.append(fname)

    return downloaded
