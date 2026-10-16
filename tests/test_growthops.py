import json
import os
import shutil
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.growthops import GrowthStore, money_units, validate_presenter
from src.agents.linkedin_publisher import LinkedInPublisher
from scripts.install_growth_skills import install


class GrowthTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = GrowthStore(self.root)

    def job(self, key="one", lane="prospecting"):
        return self.store.enqueue(lane, "research", key, {"scope": "one business"})

    def budget(self, cap=10, maximum=7, verified=True):
        (self.store.folder / "research-budget.json").write_text(json.dumps({
            "currency": "USD", "balance_verified": verified,
            "total_cap_usd": cap, "max_job_usd": maximum,
        }), encoding="utf-8")

    def lead(self):
        return {"name": "Example operating business", "website": "https://example.com/contact",
                "location": "Richmond Hill", "observations": [{
                    "text": "The contact page lists two different business email domains.",
                    "source_url": "https://example.com/contact", "captured_at": "2026-10-15"}]}

    def test_duplicate_work_returns_one_job_and_payload_conflict_fails(self):
        job = self.job()
        self.assertEqual(self.job()["id"], job["id"])
        with self.assertRaises(ValueError):
            self.store.enqueue("prospecting", "research", "one", {"different": True})
        self.assertNotEqual(self.job(lane="campaign")["id"], job["id"])

    def test_completed_result_is_idempotent_and_immutable(self):
        job = self.job()
        result = {"artifact": "review.json", "observed": True}
        self.store.finish(job["id"], result)
        self.assertEqual(self.store.finish(job["id"], result)["status"], "completed")
        with self.assertRaises(ValueError):
            self.store.finish(job["id"], {"invented": True})

    def test_stop_files_are_observed_without_change(self):
        path = self.root / "data" / "CONTENTOPS_STATE.json"
        path.write_text('{"status":"STOP","careerops":"unchanged"}', encoding="utf-8")
        original = path.read_bytes()
        self.job()
        result = self.store.status()
        self.assertEqual(result["legacy_controls_observed"][path.name]["status"], "STOP")
        self.assertFalse(result["legacy_controls_modified"])
        self.assertEqual(path.read_bytes(), original)

    def test_suppression_survives_update_and_normalized_domain(self):
        lead = self.lead()
        lead["do_not_contact"] = True
        first = self.store.save_prospect(lead)
        lead["website"] = "https://www.example.com/"
        lead["location"] = " RICHMOND   HILL "
        lead["do_not_contact"] = False
        lead["consent_verified"] = True
        second = self.store.save_prospect(lead)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["outreach_status"], "suppressed")
        self.assertEqual(len(self.store.prospects()), 1)

    def test_model_boolean_does_not_certify_contact_eligibility(self):
        lead = self.lead()
        lead["consent_verified"] = True
        result = self.store.save_prospect(lead)
        self.assertEqual(result["outreach_status"], "evidence_review_required")
        lead["observations"][0]["source_url"] = "file:///private/data"
        with self.assertRaises(ValueError):
            self.store.save_prospect(lead)

    def test_budget_requires_verified_balance_and_separate_lane(self):
        job = self.job()
        with self.assertRaises(ValueError):
            self.store.reserve_research(job["id"], 1)
        self.budget(verified=False)
        with self.assertRaises(ValueError):
            self.store.reserve_research(job["id"], 1)
        self.budget()
        with self.assertRaises(ValueError):
            self.store.reserve_research(self.job("media", lane="campaign")["id"], 1)

    def test_concurrent_reservations_cannot_overspend(self):
        self.budget()
        jobs = [self.job(str(i))["id"] for i in range(2)]

        def reserve(identifier):
            try:
                self.store.reserve_research(identifier, 7)
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(reserve, jobs))
        self.assertEqual(sum(outcomes), 1)
        self.assertEqual(self.store.status()["research_reserved_usd"], 7)

    def test_actual_overage_is_recorded_and_blocks_future_spend(self):
        self.budget(cap=10, maximum=9)
        job = self.job()
        self.store.reserve_research(job["id"], 7)
        self.store.reserve_research(job["id"], 7)
        with self.assertRaises(ValueError):
            self.store.reserve_research(job["id"], 8)
        result = self.store.settle_research(job["id"], 11, "provider-receipt-1")
        self.assertTrue(result["over_quote"])
        self.assertEqual(self.store.status()["research_spent_usd"], 11)
        with self.assertRaises(ValueError):
            self.store.reserve_research(self.job("next")["id"], 1)

    def test_settlement_retry_returns_the_same_public_shape(self):
        self.budget(cap=10, maximum=9)
        job = self.job()
        self.store.reserve_research(job["id"], 7)
        first = self.store.settle_research(job["id"], 9, "provider-receipt-1")
        retry = self.store.settle_research(job["id"], 9, "provider-receipt-1")
        self.assertEqual(retry, first)
        self.assertEqual(set(retry), {"job_id", "actual_usd", "over_quote"})
        self.assertEqual(retry["actual_usd"], 9)
        self.assertTrue(retry["over_quote"])

    def test_completion_waits_for_research_settlement(self):
        self.budget(cap=10, maximum=9)
        job = self.job()
        self.store.reserve_research(job["id"], 7)
        with self.assertRaises(ValueError):
            self.store.finish(job["id"], {"done": True})
        self.assertEqual(self.store.finish(job["id"], {"why": "provider down"}, "failed")["status"], "failed")
        paid = self.job("paid")
        self.store.reserve_research(paid["id"], 2)
        self.store.settle_research(paid["id"], 2, "provider-receipt-2")
        self.assertEqual(self.store.finish(paid["id"], {"done": True})["status"], "completed")
        free = self.job("free")
        self.assertEqual(self.store.finish(free["id"], {"done": True})["status"], "completed")

    def test_money_is_finite_nonnegative_and_rounds_up(self):
        self.assertEqual(money_units("0.0000001"), 1)
        for value in ("NaN", "Infinity", -1):
            with self.assertRaises(ValueError):
                money_units(value)

    def test_presenter_identity_voice_and_disclosure_must_match(self):
        approved = {"series_id": "launch", "presenter_id": "ai-masoud", "identity_hash": "a",
                    "voice_id": "approved-voice", "voice_reference_hash": "b", "synthetic": True}
        manifest = {**approved, "disclosure": "AI representation of Masoud. Synthetic voice."}
        self.assertEqual(validate_presenter(manifest, approved), [])
        changed = {**manifest, "voice_id": "another-voice", "disclosure": ""}
        self.assertEqual(len(validate_presenter(changed, approved)), 2)

    def test_distribution_requires_distinct_verified_actors_and_stays_draft(self):
        personal = {"actor_id": "person:verified-example", "verified": True}
        company = {"actor_id": "company:verified-example", "verified": True}
        with self.assertRaises(ValueError):
            self.store.distribution_plan("launch", "a" * 64, [personal, personal])
        with self.assertRaises(ValueError):
            self.store.distribution_plan("launch", "a" * 64, [{**personal, "verified": False}])
        result = self.store.distribution_plan("launch", "a" * 64, [personal, company])
        self.assertFalse(result["payload"]["automatic_publication"])
        self.assertEqual(result["payload"]["published_receipts"], [])

    def test_retired_linkedin_methods_do_not_import_or_use_password_client(self):
        publisher = LinkedInPublisher()
        self.assertFalse(publisher.is_configured())
        for result in (publisher.publish_text_post("text"),
                       publisher.publish_image_post("text", "missing.png"),
                       publisher.publish_video_post("text", "missing.mp4"), publisher.get_profile()):
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["error"], "supported_connection_required")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ("mas-ai-growth-ops", "mas-ai-linkedin", "mas-ai-prospecting"):
            source = self.root / ".agents" / "skills" / name
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(f"skill {name}", encoding="utf-8")

    def test_repeat_install_keeps_other_mcp_entries_and_is_idempotent(self):
        path = self.root / ".mcp.json"
        original = {"mcpServers": {"existing": {"command": "keep-me"}}, "other": {"keep": True}}
        path.write_text(json.dumps(original), encoding="utf-8")
        self.assertEqual(install(self.root, "python", True)["changed"], 3)
        self.assertEqual(install(self.root, "python", True)["changed"], 0)
        current = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(current["mcpServers"]["existing"], original["mcpServers"]["existing"])
        self.assertEqual(current["other"], original["other"])

    def test_modified_skill_blocks_install_before_any_write(self):
        install(self.root, "python")
        source = self.root / ".agents" / "skills" / "mas-ai-growth-ops" / "SKILL.md"
        source.write_text("new canonical content", encoding="utf-8")
        target = self.root / ".claude" / "skills" / "mas-ai-linkedin" / "SKILL.md"
        target.write_text("local owner changes", encoding="utf-8")
        old = (self.root / ".claude" / "skills" / "mas-ai-growth-ops" / "SKILL.md").read_bytes()
        with self.assertRaises(ValueError):
            install(self.root, "python", True)
        self.assertEqual((self.root / ".claude" / "skills" / "mas-ai-growth-ops" / "SKILL.md").read_bytes(), old)
        self.assertFalse((self.root / ".mcp.json").exists())

    def test_unowned_mcp_entry_is_preserved(self):
        path = self.root / ".mcp.json"
        path.write_text('{"mcpServers":{"contentops-growth":{"command":"owner-service"}}}', encoding="utf-8")
        original = path.read_bytes()
        with self.assertRaises(ValueError):
            install(self.root, "python", True)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.root / ".claude" / "skills").exists())

    def link_outside(self, link: Path, create_target: bool) -> Path:
        outside = Path(tempfile.mkdtemp()) / "victim.json"
        self.addCleanup(shutil.rmtree, outside.parent, True)
        if create_target:
            outside.write_text("keep", encoding="utf-8")
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(outside, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not available here")
        return outside

    def test_symlinked_receipt_is_refused_before_any_write(self):
        receipt = self.root / ".claude" / "mas-ai-skill-install.json"
        for create_target in (True, False):
            with self.subTest(dangling=not create_target):
                if receipt.is_symlink():
                    receipt.unlink()
                outside = self.link_outside(receipt, create_target)
                with self.assertRaises(ValueError):
                    install(self.root, "python")
                if create_target:
                    self.assertEqual(outside.read_text(encoding="utf-8"), "keep")
                else:
                    self.assertFalse(outside.exists())
                self.assertFalse((self.root / ".claude" / "skills").exists())

    def test_symlinked_mcp_temporary_file_is_refused_before_any_write(self):
        outside = self.link_outside(self.root / ".mcp.json.growth-tmp", True)
        with self.assertRaises(ValueError):
            install(self.root, "python", True)
        self.assertEqual(outside.read_text(encoding="utf-8"), "keep")
        self.assertFalse((self.root / ".claude" / "skills").exists())


if __name__ == "__main__":
    unittest.main()
