"""Local, durable control plane for scoped campaigns and customer research.

This module never starts the legacy pipeline, publishes, sends messages or calls
paid providers. Claude can inspect and prepare work without importing them.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path
from urllib.parse import urlsplit


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encoded(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def money_units(value) -> int:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid USD amount") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("USD amounts must be finite and nonnegative")
    return int((amount * 1_000_000).to_integral_value(rounding=ROUND_CEILING))


def public_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("A public HTTP(S) source URL without credentials is required")
    return value


def validate_presenter(manifest: dict, approved: dict) -> list[str]:
    errors = []
    for key in ("series_id", "presenter_id", "identity_hash", "voice_id", "voice_reference_hash"):
        if not approved.get(key) or manifest.get(key) != approved.get(key):
            errors.append(f"Presenter manifest mismatch: {key}")
    if manifest.get("synthetic") is not approved.get("synthetic"):
        errors.append("Presenter manifest mismatch: synthetic")
    if approved.get("synthetic") and not manifest.get("disclosure"):
        errors.append("Synthetic presenter disclosure is missing")
    return errors


class GrowthStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.folder = self.root / "data" / "growthops"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.database = self.folder / "state.sqlite3"
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs(
                    id TEXT PRIMARY KEY, lane TEXT NOT NULL, kind TEXT NOT NULL,
                    idem TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL,
                    status TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL,
                    result TEXT, UNIQUE(lane, idem));
                CREATE TABLE IF NOT EXISTS prospects(
                    id TEXT PRIMARY KEY, dedup TEXT UNIQUE NOT NULL, data TEXT NOT NULL,
                    suppressed INTEGER NOT NULL DEFAULT 0, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS research_costs(
                    job_id TEXT PRIMARY KEY, reserved INTEGER NOT NULL,
                    actual INTEGER, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL,
                    object_id TEXT NOT NULL, detail TEXT NOT NULL);
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def event(db, action: str, object_id: str, detail: dict):
        db.execute("INSERT INTO events(at,action,object_id,detail) VALUES(?,?,?,?)",
                   (now(), action, object_id, encoded(detail)))

    def status(self) -> dict:
        controls = {}
        for filename in ("CONTENTOPS_STATE.json", "CONTENTOPS_KILL_SWITCH.json"):
            path = self.root / "data" / filename
            if path.exists():
                try:
                    controls[filename] = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    controls[filename] = {"state": "unreadable"}
            else:
                controls[filename] = {"state": "not_present_in_this_checkout"}
        with self.connection() as db:
            jobs = [dict(row) for row in db.execute(
                "SELECT lane,status,COUNT(*) AS count FROM jobs GROUP BY lane,status")]
            reserved, spent = db.execute(
                "SELECT COALESCE(SUM(CASE WHEN state='reserved' THEN reserved ELSE 0 END),0),"
                "COALESCE(SUM(actual),0) FROM research_costs").fetchone()
        return {"jobs": jobs, "legacy_controls_observed": controls,
                "legacy_controls_modified": False, "publishing": "external_adapter_required",
                "research_reserved_usd": reserved / 1_000_000,
                "research_spent_usd": spent / 1_000_000}

    def skills(self) -> list[dict]:
        result = []
        for path in sorted((self.root / ".agents" / "skills").glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8")
            result.append({"name": path.parent.name, "path": str(path),
                           "sha256": hashlib.sha256(text.encode()).hexdigest()})
        return result

    def enqueue(self, lane: str, kind: str, idempotency_key: str, payload: dict) -> dict:
        if lane not in {"campaign", "prospecting"}:
            raise ValueError("Use campaign or prospecting lane")
        if kind not in {"research", "draft", "render_review", "distribution_plan"}:
            raise ValueError("Unsupported bounded task kind")
        if not isinstance(payload, dict) or not 1 <= len(idempotency_key) <= 200:
            raise ValueError("A payload object and bounded idempotency key are required")
        body = encoded(payload)
        if len(body.encode()) > 262144:
            raise ValueError("Use artifact references, not large/private source files")
        digest = hashlib.sha256(body.encode()).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE lane=? AND idem=?", (lane, idempotency_key)).fetchone()
            if row:
                if row["hash"] != digest or row["kind"] != kind:
                    raise ValueError("Idempotency key already belongs to different work")
                return self._job(row)
            identifier = str(uuid.uuid4())
            timestamp = now()
            db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (identifier, lane, kind, idempotency_key, body, digest,
                        "queued", timestamp, timestamp, None))
            self.event(db, "job.queued", identifier, {"lane": lane, "kind": kind})
            return self._job(db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone())

    @staticmethod
    def _job(row):
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        item["result"] = json.loads(item["result"]) if item["result"] else None
        return item

    def jobs(self, lane: str | None = None) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT * FROM jobs WHERE (? IS NULL OR lane=?) ORDER BY created",
                              (lane, lane)).fetchall()
            return [self._job(row) for row in rows]

    def finish(self, job_id: str, result: dict, status: str = "completed") -> dict:
        if status not in {"completed", "failed", "blocked"}:
            raise ValueError("Invalid final task state")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise ValueError("Unknown job")
            if row["status"] == "completed":
                if row["result"] != encoded(result) or status != "completed":
                    raise ValueError("Completed result is immutable; enqueue a new revision")
                return self._job(row)
            if status == "completed":
                reservation = db.execute("SELECT state FROM research_costs WHERE job_id=?",
                                         (job_id,)).fetchone()
                if reservation and reservation["state"] == "reserved":
                    raise ValueError("Settle the research reservation before completing the job")
            db.execute("UPDATE jobs SET status=?,result=?,updated=? WHERE id=?",
                       (status, encoded(result), now(), job_id))
            self.event(db, "job." + status, job_id, {"result": result})
            return self._job(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def save_prospect(self, lead: dict) -> dict:
        lead = json.loads(encoded(lead))
        website = public_url(lead["website"])
        if not lead.get("name") or not lead.get("location") or not lead.get("observations"):
            raise ValueError("Name, location and sourced observations are required")
        for observation in lead["observations"]:
            public_url(observation["source_url"])
            if not observation.get("text") or not observation.get("captured_at"):
                raise ValueError("Every observation needs text and capture time")
        host = urlsplit(website).hostname.lower().removeprefix("www.")
        key = host + "|" + re.sub(r"\s+", " ", lead["location"].strip().casefold())
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM prospects WHERE dedup=?", (key,)).fetchone()
            suppressed = bool(lead.get("do_not_contact")) or bool(old and old["suppressed"])
            identifier = old["id"] if old else str(uuid.uuid4())
            lead.update({"id": identifier, "do_not_contact": suppressed})
            # Eligibility is never certified from a model-supplied boolean.
            lead["outreach_status"] = "suppressed" if suppressed else "evidence_review_required"
            db.execute("INSERT INTO prospects VALUES(?,?,?,?,?) ON CONFLICT(dedup) DO UPDATE SET "
                       "data=excluded.data,suppressed=excluded.suppressed,updated=excluded.updated",
                       (identifier, key, encoded(lead), int(suppressed), now()))
            self.event(db, "prospect.saved", identifier, {"website": website})
            return lead

    def prospects(self) -> list[dict]:
        with self.connection() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT data FROM prospects ORDER BY updated")]

    def reserve_research(self, job_id: str, quote_usd: float) -> dict:
        policy_path = self.folder / "research-budget.json"
        if not policy_path.exists():
            raise ValueError("Configure the existing authorized research budget and verify its balance first")
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        if policy.get("currency") != "USD" or policy.get("balance_verified") is not True:
            raise ValueError("Research balance/currency has not been verified")
        amount = money_units(quote_usd)
        cap = money_units(policy["total_cap_usd"])
        per_job = money_units(policy["max_job_usd"])
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            job = db.execute("SELECT lane FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not job or job["lane"] != "prospecting":
                raise ValueError("Research charges require a prospecting job; media has a separate ledger")
            old = db.execute("SELECT * FROM research_costs WHERE job_id=?", (job_id,)).fetchone()
            if old:
                if old["reserved"] != amount:
                    raise ValueError("Reservation already exists at a different quote")
                return dict(old)
            used = db.execute("SELECT COALESCE(SUM(CASE WHEN state='reserved' THEN reserved "
                              "ELSE COALESCE(actual,0) END),0) FROM research_costs").fetchone()[0]
            if amount > per_job or used + amount > cap:
                raise ValueError("Authorized research budget would be exceeded")
            db.execute("INSERT INTO research_costs VALUES(?,?,NULL,'reserved')", (job_id, amount))
            self.event(db, "research.reserved", job_id, {"quote_usd": amount / 1_000_000})
            return {"job_id": job_id, "reserved": amount, "actual": None, "state": "reserved"}

    def settle_research(self, job_id: str, actual_usd: float, receipt: str) -> dict:
        if not receipt.strip():
            raise ValueError("An actual provider receipt/reference is required")
        actual = money_units(actual_usd)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM research_costs WHERE job_id=?", (job_id,)).fetchone()
            if not row:
                raise ValueError("Unknown research reservation")
            result = {"job_id": job_id, "actual_usd": actual / 1_000_000,
                      "over_quote": actual > row["reserved"]}
            if row["state"] == "settled":
                if row["actual"] != actual:
                    raise ValueError("Reservation already settled at another amount")
                return result
            db.execute("UPDATE research_costs SET actual=?,state='settled' WHERE job_id=?", (actual, job_id))
            self.event(db, "research.settled", job_id,
                       {"actual_usd": result["actual_usd"], "receipt": receipt,
                        "over_quote": result["over_quote"]})
            return result

    def distribution_plan(self, campaign_id: str, source_hash: str, destinations: list[dict]) -> dict:
        if not re.fullmatch(r"[a-f0-9]{64}", source_hash):
            raise ValueError("A source asset SHA256 is required")
        actors = [item.get("actor_id") for item in destinations]
        if not destinations or any(not actor for actor in actors) or len(set(actors)) != len(actors):
            raise ValueError("Each destination needs a distinct verified actor ID")
        if any(item.get("verified") is not True for item in destinations):
            raise ValueError("Verify destination identity/access before preparing distribution")
        payload = {"campaign_id": campaign_id, "source_hash": source_hash,
                   "destinations": destinations, "state": "draft",
                   "published_receipts": [], "automatic_publication": False}
        return self.enqueue("campaign", "distribution_plan", "distribution:" + campaign_id, payload)
