# TDD RED state — forge_db.py does not exist yet. Run after Phase 4 implementation.
"""
Smoke tests for forge_db.py (scripts/forge_db.py).

Schema under test
-----------------
Tables:
  sub_projects  (id, name UNIQUE, path, description, status, created_at, updated_at)
  decisions     (id, created_at, agent, decision, rationale, sub_project_id FK, issue_ref)
  indexed_files (id, path UNIQUE, content_hash, sub_project_id FK, doc_type, last_indexed_at)
  knowledge_index  FTS5 virtual table (file_id, path, sub_project, doc_type, content)

Functions under test (locked signatures from devops-lead review):
  get_connection() -> sqlite3.Connection
  register_project(name, path, description=None, status="active") -> int
  update_project(name, status=None, description=None, path=None) -> bool
  list_projects(status=None) -> list[dict]
  log_decision(agent, decision, rationale=None, sub_project=None, issue_ref=None) -> int
  get_decisions(agent=None, sub_project=None, limit=50) -> list[dict]
  index_file(path, content, sub_project=None, doc_type="other") -> int
  search(query, limit=10, sub_project=None, doc_type=None) -> list[dict]
  purge_knowledge(sub_project=None, older_than_days=None) -> int
"""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Module import — expected to raise ModuleNotFoundError in RED state
# ---------------------------------------------------------------------------
import forge_db  # noqa: E402  — intentional; will fail until Phase 4


def _reload_with_db(tmp_dir: str):
    """Re-import forge_db with DB_PATH pointing at a temp directory."""
    db_path = Path(tmp_dir) / "data" / "forge.db"
    # Patch the module-level constant, then force schema initialisation.
    forge_db.DB_PATH = db_path
    # Re-run init so tables are created in the temp DB.
    forge_db.init_db()
    return db_path


# ---------------------------------------------------------------------------
# 1. TestRegisterProject
# ---------------------------------------------------------------------------
class TestRegisterProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _reload_with_db(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_register_returns_int_id(self):
        pid = forge_db.register_project(
            name="test-proj",
            path="/tmp/test-proj",
            description="A test project",
            status="active",
        )
        self.assertIsInstance(pid, int)
        self.assertGreater(pid, 0)

    def test_upsert_same_name_updates_not_duplicates(self):
        forge_db.register_project(name="upsert-proj", path="/tmp/upsert", status="active")
        forge_db.register_project(name="upsert-proj", path="/tmp/upsert", status="archived")

        projects = forge_db.list_projects()
        names = [p["name"] for p in projects]
        self.assertEqual(names.count("upsert-proj"), 1, "UPSERT must not duplicate rows")

        matching = [p for p in projects if p["name"] == "upsert-proj"]
        self.assertEqual(matching[0]["status"], "archived")

    def test_list_projects_returns_registered_project(self):
        forge_db.register_project(name="list-me", path="/tmp/list-me")
        projects = forge_db.list_projects()
        names = [p["name"] for p in projects]
        self.assertIn("list-me", names)

    def test_list_projects_filters_by_status(self):
        forge_db.register_project(name="active-proj", path="/tmp/active", status="active")
        forge_db.register_project(name="archived-proj", path="/tmp/archived", status="archived")

        archived = forge_db.list_projects(status="archived")
        names = [p["name"] for p in archived]
        self.assertIn("archived-proj", names)
        self.assertNotIn("active-proj", names)


# ---------------------------------------------------------------------------
# 2. TestUpdateProject
# ---------------------------------------------------------------------------
class TestUpdateProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _reload_with_db(self.tmp)
        forge_db.register_project(name="update-me", path="/tmp/update-me", status="active")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_update_existing_project_returns_true(self):
        result = forge_db.update_project(
            name="update-me", status="archived", description="Now archived"
        )
        self.assertTrue(result)

        projects = forge_db.list_projects(status="archived")
        names = [p["name"] for p in projects]
        self.assertIn("update-me", names)

        matching = [p for p in projects if p["name"] == "update-me"]
        self.assertEqual(matching[0]["description"], "Now archived")

    def test_update_nonexistent_project_returns_false(self):
        result = forge_db.update_project(name="ghost-project", status="archived")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# 3. TestLogDecision
# ---------------------------------------------------------------------------
class TestLogDecision(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _reload_with_db(self.tmp)
        forge_db.register_project(name="test-proj", path="/tmp/test-proj")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_log_global_decision_returns_int_id(self):
        did = forge_db.log_decision(
            agent="test-agent",
            decision="Use SQLite for storage",
            rationale="Simplicity and zero-dependency",
        )
        self.assertIsInstance(did, int)
        self.assertGreater(did, 0)

    def test_log_project_scoped_decision_sets_sub_project_id(self):
        did = forge_db.log_decision(
            agent="test-agent",
            decision="Scope decision to test-proj",
            sub_project="test-proj",
        )
        decisions = forge_db.get_decisions(sub_project="test-proj")
        ids = [d["id"] for d in decisions]
        self.assertIn(did, ids)

        scoped = [d for d in decisions if d["id"] == did]
        self.assertIsNotNone(scoped[0].get("sub_project_id"))

    def test_get_decisions_returns_all(self):
        forge_db.log_decision(agent="test-agent", decision="Global decision")
        forge_db.log_decision(agent="test-agent", decision="Project decision", sub_project="test-proj")
        decisions = forge_db.get_decisions()
        self.assertGreaterEqual(len(decisions), 2)

    def test_get_decisions_filters_by_agent(self):
        forge_db.log_decision(agent="test-agent", decision="By test-agent")
        forge_db.log_decision(agent="other-agent", decision="By other-agent")

        results = forge_db.get_decisions(agent="test-agent")
        for d in results:
            self.assertEqual(d["agent"], "test-agent")

    def test_get_decisions_filters_by_sub_project(self):
        forge_db.register_project(name="proj-b", path="/tmp/proj-b")
        forge_db.log_decision(agent="a", decision="For test-proj", sub_project="test-proj")
        forge_db.log_decision(agent="a", decision="For proj-b", sub_project="proj-b")

        results = forge_db.get_decisions(sub_project="test-proj")
        for d in results:
            self.assertIsNotNone(d.get("sub_project_id"))
        # Ensure proj-b decisions are NOT in the result
        proj_b_id = next(
            p["id"] for p in forge_db.list_projects() if p["name"] == "proj-b"
        )
        for d in results:
            self.assertNotEqual(d.get("sub_project_id"), proj_b_id)


# ---------------------------------------------------------------------------
# 4. TestIndexFile
# ---------------------------------------------------------------------------
class TestIndexFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _reload_with_db(self.tmp)
        forge_db.register_project(name="test-proj", path="/tmp/test-proj")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_index_new_file_returns_int_id(self):
        fid = forge_db.index_file(
            path="/tmp/test-proj/README.md",
            content="This is a keyword-rich document",
            sub_project="test-proj",
            doc_type="doc",
        )
        self.assertIsInstance(fid, int)
        self.assertGreater(fid, 0)

    def test_reindex_same_content_is_noop(self):
        content = "Stable content with keyword"
        path = "/tmp/test-proj/stable.md"
        id1 = forge_db.index_file(path=path, content=content)
        id2 = forge_db.index_file(path=path, content=content)
        self.assertEqual(id1, id2, "Same-content re-index must return the same id (no-op)")

        # FTS should not have duplicate rows for the same file
        results = forge_db.search("Stable content")
        paths = [r["path"] for r in results]
        self.assertEqual(paths.count(path), 1, "FTS must not have duplicate rows for same path")

    def test_reindex_different_content_updates_entry(self):
        path = "/tmp/test-proj/changing.md"
        forge_db.index_file(path=path, content="original content alpha")
        forge_db.index_file(path=path, content="updated content beta")

        results = forge_db.search("beta")
        paths = [r["path"] for r in results]
        self.assertIn(path, paths)

        # Old content should not surface
        old_results = forge_db.search("alpha")
        old_paths = [r["path"] for r in old_results]
        self.assertNotIn(path, old_paths)

    def test_search_returns_result_with_correct_path(self):
        target_path = "/tmp/test-proj/findme.md"
        forge_db.index_file(
            path=target_path,
            content="uniqueterm987 document content",
            sub_project="test-proj",
            doc_type="doc",
        )
        results = forge_db.search("uniqueterm987")
        paths = [r["path"] for r in results]
        self.assertIn(target_path, paths)

    def test_search_filters_by_sub_project(self):
        forge_db.register_project(name="other-proj", path="/tmp/other-proj")
        forge_db.index_file(
            path="/tmp/test-proj/scoped.md",
            content="scoped987 document",
            sub_project="test-proj",
        )
        forge_db.index_file(
            path="/tmp/other-proj/noise.md",
            content="scoped987 document in other proj",
            sub_project="other-proj",
        )

        results = forge_db.search("scoped987", sub_project="test-proj")
        for r in results:
            self.assertEqual(r.get("sub_project"), "test-proj")

    def test_search_filters_by_doc_type(self):
        forge_db.index_file(
            path="/tmp/test-proj/typed_doc.md",
            content="doctype456 in a doc file",
            doc_type="doc",
        )
        forge_db.index_file(
            path="/tmp/test-proj/typed_code.py",
            content="doctype456 in a code file",
            doc_type="code",
        )

        results = forge_db.search("doctype456", doc_type="doc")
        for r in results:
            self.assertEqual(r.get("doc_type"), "doc")


# ---------------------------------------------------------------------------
# 5. TestPurgeKnowledge
# ---------------------------------------------------------------------------
class TestPurgeKnowledge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _reload_with_db(self.tmp)
        forge_db.register_project(name="proj-a", path="/tmp/proj-a")
        forge_db.register_project(name="proj-b", path="/tmp/proj-b")
        forge_db.index_file(
            path="/tmp/proj-a/file.md",
            content="purgeword proj-a content",
            sub_project="proj-a",
        )
        forge_db.index_file(
            path="/tmp/proj-b/file.md",
            content="purgeword proj-b content",
            sub_project="proj-b",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_purge_sub_project_deletes_only_that_project(self):
        deleted = forge_db.purge_knowledge(sub_project="proj-a")
        self.assertEqual(deleted, 1, "purge_knowledge must return count of deleted entries")

    def test_purge_leaves_other_project_searchable(self):
        forge_db.purge_knowledge(sub_project="proj-a")
        results = forge_db.search("purgeword", sub_project="proj-b")
        paths = [r["path"] for r in results]
        self.assertIn("/tmp/proj-b/file.md", paths)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
