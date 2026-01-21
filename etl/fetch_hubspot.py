#!/usr/bin/env python3
"""
HubSpot Data Fetcher for Coach Dashboard

Fetches contacts, associations, and deals from HubSpot.
Adapted from conversie-analyse/hubspot_coach_eligibility.py

Outputs:
- etl/cache/na_contacts.json
- etl/cache/contact_deal_links.json
- etl/cache/deal_ids.json
- etl/cache/deals_raw.json
- etl/cache/deals_flat.csv
- data/enums_<RUN_ID>.xlsx

Run with: python etl/fetch_hubspot.py [--refresh all|contacts|associations|deals]
"""

from __future__ import annotations

import os
import sys
import json
import time
import glob
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

import requests
import pandas as pd

# Project root (one level up from etl/)
PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = PROJECT_ROOT / "etl" / "cache"
OUTPUT_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "etl" / "logs"


def utc_now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def ensure_dirs() -> None:
    for d in (CACHE_DIR, OUTPUT_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load_dotenv(path: Path = None) -> None:
    """Very small .env loader (KEY=VALUE, ignores comments/blank lines)."""
    if path is None:
        path = PROJECT_ROOT / ".env"
    if not path.is_file():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)


def write_json(path: Path, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def file_nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 10


def newest_file(pattern: str, directory: Path) -> Optional[Path]:
    files = list(directory.glob(pattern))
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def setup_logging(run_id: str) -> logging.Logger:
    ensure_dirs()
    log_path = LOG_DIR / f"fetch_hubspot_{run_id}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger("fetch_hubspot")
    logger.info("Log file: %s", log_path)
    return logger


@dataclass
class Config:
    pat: str
    base_url: str = "https://api.hubapi.com"
    aangebracht_door_value: str = "Nationale Apotheek"
    pipeline_status_begeleiding: str = "15413220"
    pipeline_nabeller: str = "38341389"

    @property
    def headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.pat}", "Content-Type": "application/json"}


class HubSpotClient:
    def __init__(self, cfg: Config, logger: logging.Logger):
        self.cfg = cfg
        self.log = logger
        self.session = requests.Session()

    def _request_with_retries(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        max_retries: int = 6,
    ) -> requests.Response:
        """Retry for 429 / transient 5xx with exponential backoff."""
        last_exc = None
        for attempt in range(max_retries):
            try:
                r = self.session.request(
                    method,
                    url,
                    headers=self.cfg.headers,
                    params=params,
                    json=json_body,
                    timeout=timeout,
                )
                if r.status_code == 429:
                    wait = min(2 ** attempt, 30)
                    self.log.warning("429 rate limit. Sleeping %ss. url=%s", wait, url)
                    time.sleep(wait)
                    continue
                if 500 <= r.status_code < 600:
                    wait = min(2 ** attempt, 30)
                    self.log.warning("5xx (%s). Sleeping %ss. url=%s", r.status_code, wait, url)
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                last_exc = e
                wait = min(2 ** attempt, 30)
                self.log.warning("Request error (%s). Sleeping %ss. url=%s", e, wait, url)
                time.sleep(wait)
        raise RuntimeError(f"HTTP request failed after retries: {method} {url} ({last_exc})")

    def search_contacts_by_aangebracht_door(
        self,
        aangebracht_door_value: str,
        properties: List[str],
    ) -> List[Dict[str, Any]]:
        url = f"{self.cfg.base_url}/crm/v3/objects/contacts/search"
        after = None
        out: List[Dict[str, Any]] = []

        payload_base = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "aangebracht_door",
                    "operator": "EQ",
                    "value": aangebracht_door_value
                }]
            }],
            "properties": properties,
            "limit": 100,
        }

        while True:
            payload = dict(payload_base)
            if after:
                payload["after"] = after

            r = self._request_with_retries("POST", url, json_body=payload)
            data = r.json()
            results = data.get("results", [])
            out.extend(results)

            nxt = data.get("paging", {}).get("next")
            if not nxt:
                break
            after = nxt.get("after")
            time.sleep(0.2)

        return out

    def get_associated_deals_for_contact(self, contact_id: str) -> List[str]:
        url = f"{self.cfg.base_url}/crm/v4/objects/contacts/{contact_id}/associations/deals"
        deal_ids: List[str] = []
        after = None
        while True:
            params = {"limit": 500}
            if after:
                params["after"] = after
            r = self._request_with_retries("GET", url, params=params)
            data = r.json()
            results = data.get("results", [])
            for rel in results:
                to_id = rel.get("toObjectId")
                if to_id is not None:
                    deal_ids.append(str(to_id))
            paging = data.get("paging", {})
            nxt = paging.get("next")
            if not nxt:
                break
            after = nxt.get("after")
            time.sleep(0.1)
        return deal_ids

    def batch_read_deals(self, deal_ids: List[str], properties: List[str]) -> List[Dict[str, Any]]:
        url = f"{self.cfg.base_url}/crm/v3/objects/deals/batch/read"
        out: List[Dict[str, Any]] = []
        chunk_size = 100

        for i in range(0, len(deal_ids), chunk_size):
            chunk = deal_ids[i:i + chunk_size]
            body = {
                "properties": properties,
                "inputs": [{"id": str(x)} for x in chunk],
            }
            r = self._request_with_retries("POST", url, json_body=body)
            data = r.json()
            out.extend(data.get("results", []))
            time.sleep(0.2)

        return out

    def get_deal_pipelines(self) -> List[Dict[str, Any]]:
        url = f"{self.cfg.base_url}/crm/v3/pipelines/deals"
        r = self._request_with_retries("GET", url)
        data = r.json()
        return data.get("results", [])


class Workflow:
    def __init__(self, cfg: Config, run_id: str, logger: logging.Logger):
        self.cfg = cfg
        self.run_id = run_id
        self.log = logger
        self.client = HubSpotClient(cfg, logger)
        ensure_dirs()

    def _load_or_fetch_contacts(self, refresh: bool) -> List[Dict[str, Any]]:
        cache_json = CACHE_DIR / "na_contacts.json"
        if not refresh and file_nonempty(cache_json):
            self.log.info("Using cached NA contacts: %s", cache_json)
            return read_json(cache_json)

        self.log.info("Fetching NA contacts (aangebracht_door=%s)...", self.cfg.aangebracht_door_value)
        props = ["hs_object_id", "firstname", "lastname", "hubspot_owner_id", "aangebracht_door"]
        contacts = self.client.search_contacts_by_aangebracht_door(self.cfg.aangebracht_door_value, props)

        write_json(cache_json, contacts)

        rows = []
        for c in contacts:
            p = c.get("properties", {})
            rows.append({
                "contact_id": c.get("id"),
                "firstname": p.get("firstname"),
                "lastname": p.get("lastname"),
                "hubspot_owner_id": p.get("hubspot_owner_id"),
                "aangebracht_door": p.get("aangebracht_door"),
            })
        pd.DataFrame(rows).to_csv(CACHE_DIR / "na_contacts.csv", index=False)

        self.log.info("NA contacts fetched: %d", len(contacts))
        return contacts

    def _load_or_fetch_associations(self, contact_ids: List[str], refresh: bool) -> Dict[str, List[str]]:
        cache_json = CACHE_DIR / "contact_deal_links.json"
        if not refresh and file_nonempty(cache_json):
            self.log.info("Using cached contact->deal links: %s", cache_json)
            return read_json(cache_json)

        self.log.info("Fetching associations (contact -> deals) for %d contacts...", len(contact_ids))
        links: Dict[str, List[str]] = {}
        for idx, cid in enumerate(contact_ids, start=1):
            if idx % 50 == 0:
                self.log.info("Progress associations: %d/%d", idx, len(contact_ids))
            deal_ids = self.client.get_associated_deals_for_contact(str(cid))
            links[str(cid)] = list(sorted(set(deal_ids)))
            time.sleep(0.05)

        write_json(cache_json, links)

        all_deal_ids: Set[str] = set()
        for ids in links.values():
            all_deal_ids.update(ids)
        deal_ids_list = sorted(all_deal_ids)
        write_json(CACHE_DIR / "deal_ids.json", deal_ids_list)

        self.log.info("Associations fetched. Unique deals: %d", len(deal_ids_list))
        return links

    def _load_or_fetch_deals(self, refresh: bool) -> List[Dict[str, Any]]:
        cache_json = CACHE_DIR / "deals_raw.json"
        deal_ids_path = CACHE_DIR / "deal_ids.json"

        if not refresh and file_nonempty(cache_json):
            self.log.info("Using cached deals_raw: %s", cache_json)
            return read_json(cache_json)

        if not file_nonempty(deal_ids_path):
            raise RuntimeError("deal_ids.json missing/empty. Run associations step first.")

        deal_ids = read_json(deal_ids_path)
        if not isinstance(deal_ids, list) or not deal_ids:
            raise RuntimeError("deal_ids.json is empty.")

        self.log.info("Fetching deal details for %d deals (batch read)...", len(deal_ids))
        props = [
            "hs_object_id",
            "dealname",
            "hubspot_owner_id",
            "pipeline",
            "dealstage",
            "createdate",
            "closedate",
            "hs_is_closed_won",
            "hs_is_closed_lost",
        ]
        deals = self.client.batch_read_deals([str(x) for x in deal_ids], props)
        write_json(cache_json, deals)

        flat_rows = []
        for d in deals:
            p = d.get("properties", {})
            flat_rows.append({
                "deal_id": d.get("id"),
                "dealname": p.get("dealname"),
                "hubspot_owner_id": p.get("hubspot_owner_id"),
                "pipeline": p.get("pipeline"),
                "dealstage": p.get("dealstage"),
                "createdate": p.get("createdate"),
                "closedate": p.get("closedate"),
                "hs_is_closed_won": p.get("hs_is_closed_won"),
                "hs_is_closed_lost": p.get("hs_is_closed_lost"),
            })
        pd.DataFrame(flat_rows).to_csv(CACHE_DIR / "deals_flat.csv", index=False)

        self.log.info("Deals fetched: %d", len(deals))
        return deals

    def _dump_enums(self, deals: List[Dict[str, Any]], refresh: bool) -> Path:
        out_xlsx = OUTPUT_DIR / f"enums_{self.run_id}.xlsx"
        if not refresh and out_xlsx.is_file() and out_xlsx.stat().st_size > 1000:
            self.log.info("Enums already exist: %s", out_xlsx)
            return out_xlsx

        self.log.info("Fetching deal pipelines & stages...")
        pipelines = self.client.get_deal_pipelines()

        pipeline_rows = []
        stage_rows = []
        for p in pipelines:
            pipeline_rows.append({
                "pipeline_id": p.get("id"),
                "pipeline_label": p.get("label"),
                "display_order": p.get("displayOrder"),
                "archived": p.get("archived"),
                "created_at": p.get("createdAt"),
                "updated_at": p.get("updatedAt"),
            })
            for st in p.get("stages", []) or []:
                stage_rows.append({
                    "pipeline_id": p.get("id"),
                    "dealstage_id": st.get("id"),
                    "stage_label": st.get("label"),
                    "display_order": st.get("displayOrder"),
                    "metadata": json.dumps(st.get("metadata", {}), ensure_ascii=False),
                    "archived": st.get("archived"),
                    "created_at": st.get("createdAt"),
                    "updated_at": st.get("updatedAt"),
                })

        obs = {
            "pipeline": {},
            "dealstage": {},
            "hubspot_owner_id": {},
            "hs_is_closed_won": {},
            "hs_is_closed_lost": {},
        }

        for d in deals:
            p = d.get("properties", {})
            for k in list(obs.keys()):
                v = p.get(k)
                key = "" if v is None else str(v)
                obs[k][key] = obs[k].get(key, 0) + 1

        observed_rows = []
        for prop, counts in obs.items():
            for val, cnt in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
                observed_rows.append({
                    "property": prop,
                    "value": val,
                    "count": cnt,
                })

        with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
            pd.DataFrame(pipeline_rows).to_excel(w, "Pipelines", index=False)
            pd.DataFrame(stage_rows).to_excel(w, "Stages", index=False)
            pd.DataFrame(observed_rows).to_excel(w, "ObservedValues", index=False)

        self.log.info("Wrote enums: %s", out_xlsx)
        return out_xlsx

    def run(self, refresh: str = "none") -> None:
        refresh = (refresh or "none").lower()
        refresh_contacts = refresh in ("contacts", "all")
        refresh_assoc = refresh in ("associations", "all")
        refresh_deals = refresh in ("deals", "all")
        refresh_enums = refresh in ("all",)

        self.log.info("Refresh flags: contacts=%s associations=%s deals=%s", refresh_contacts, refresh_assoc, refresh_deals)

        contacts = self._load_or_fetch_contacts(refresh_contacts)
        if not contacts:
            raise RuntimeError("0 NA contacts found. Check contact property 'aangebracht_door' and its exact value.")

        contact_ids = [str(c.get("id")) for c in contacts if c.get("id") is not None]
        links = self._load_or_fetch_associations(contact_ids, refresh_assoc)

        unique_deals = set()
        for ids in links.values():
            unique_deals.update([str(x) for x in ids])
        if not unique_deals:
            raise RuntimeError("0 associated deals found for NA contacts.")

        deals = self._load_or_fetch_deals(refresh_deals)
        if not deals:
            raise RuntimeError("0 deals fetched (batch read).")

        enums_path = self._dump_enums(deals, refresh_enums)

        print("\n" + "=" * 80)
        print("Fetch complete")
        print("=" * 80)
        print(f"NA contacts: {len(contacts)}  ({CACHE_DIR / 'na_contacts.json'})")
        print(f"Unique deals: {len(unique_deals)} ({CACHE_DIR / 'deal_ids.json'})")
        print(f"Deals raw: {len(deals)}    ({CACHE_DIR / 'deals_raw.json'})")
        print(f"Enums Excel: {enums_path}")
        print("=" * 80 + "\n")


def parse_args(argv: List[str]) -> Tuple[str]:
    refresh = "none"
    for i, a in enumerate(argv):
        if a == "--refresh" and i + 1 < len(argv):
            refresh = argv[i + 1]
    return (refresh,)


def main() -> None:
    ensure_dirs()
    load_dotenv()

    run_id = utc_now_run_id()
    logger = setup_logging(run_id)

    pat = os.environ.get("HUBSPOT_PAT", "").strip()
    if not pat or pat.lower().startswith("pat-replace_me"):
        raise RuntimeError("Missing HUBSPOT_PAT. Create .env file in project root with HUBSPOT_PAT=your_token")

    cfg = Config(
        pat=pat,
        aangebracht_door_value=os.environ.get("AANGEBRACHT_DOOR_VALUE", "Nationale Apotheek").strip() or "Nationale Apotheek",
        pipeline_status_begeleiding=os.environ.get("PIPELINE_STATUS_BEGELEIDING", "15413220").strip() or "15413220",
        pipeline_nabeller=os.environ.get("PIPELINE_NABELLER", "38341389").strip() or "38341389",
    )

    wf = Workflow(cfg, run_id, logger)
    refresh, = parse_args(sys.argv[1:])
    wf.run(refresh=refresh)


if __name__ == "__main__":
    main()
