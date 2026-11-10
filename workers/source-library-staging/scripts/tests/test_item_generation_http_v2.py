import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_http_v2 import create_app

UID = "00000000-0000-4000-8000-000000000001"
PAYLOAD = {"topic": "airway", "mode": "NCE", "domain": "III",
           "section": "H", "objective": "III.H.4", "item_id": "draft-1"}

class Connection:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class DraftRevalidationHttpTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app(conn_factory=Connection,
                            resolve_admin=lambda token: UID if token=="valid" else None,
                            environment={"STAGING_ONLY":"true"})

    def call(self, path, method="GET", token="valid", origin="https://staging.srnastudytool.com"):
        env={"PATH_INFO":path,"REQUEST_METHOD":method,"HTTP_ORIGIN":origin,
             "HTTP_AUTHORIZATION":"Bearer "+token}
        seen=[]
        body=b"".join(self.app(env,lambda status,headers:seen.append(status)))
        return seen[0],json.loads(body)

    @patch("item_generation_http_v2.revalidate",return_value={
        "draft_id":"abc90a93-41f8-4d7c-8e27-94a609135572",
        "can_publish":False,"generation_performed":False,"database_writes":False})
    def test_authenticated_get_is_read_only(self, validator):
        path="/generation/drafts/abc90a93-41f8-4d7c-8e27-94a609135572/revalidate"
        status,data=self.call(path)
        self.assertEqual(status,"200 OK")
        self.assertFalse(data["can_publish"])
        validator.assert_called_once()
        self.assertEqual(validator.call_args.kwargs["owner_uid"],UID)

    @patch("item_generation_http_v2.revalidate")
    def test_non_admin_and_wrong_origin_denied(self,validator):
        path="/generation/drafts/abc90a93-41f8-4d7c-8e27-94a609135572/revalidate"
        self.assertEqual(self.call(path,token="invalid")[0],"403 Forbidden")
        self.assertEqual(self.call(path,origin="https://srnastudytool.com")[0],"403 Forbidden")
        self.assertEqual(self.call(path,method="POST")[0],"405 Method Not Allowed")
        validator.assert_not_called()

    def test_invalid_draft_id_rejected(self):
        status,_=self.call("/generation/drafts/not-a-uuid/revalidate")
        self.assertEqual(status,"404 Not Found")

class DraftRevisionHttpTests(unittest.TestCase):
    PATH="/generation/drafts/abc90a93-41f8-4d7c-8e27-94a609135572/revisions"
    def setUp(self):
        self.app=create_app(conn_factory=Connection,
            resolve_admin=lambda token: UID if token=="valid" else None,
            environment={"STAGING_ONLY":"true"})

    def call(self,method="GET",payload=None,token="valid",
             origin="https://staging.srnastudytool.com"):
        raw=json.dumps(payload).encode() if payload is not None else b""
        env={"PATH_INFO":self.PATH,"REQUEST_METHOD":method,
             "HTTP_ORIGIN":origin,"HTTP_AUTHORIZATION":"Bearer "+token,
             "CONTENT_LENGTH":str(len(raw)),"wsgi.input":io.BytesIO(raw)}
        seen=[]
        body=b"".join(self.app(env,lambda status,headers:seen.append(status)))
        return seen[0],json.loads(body)

    @patch("item_generation_http_v2.list_revisions",return_value=[])
    def test_history_read_scoped_to_authenticated_owner(self,history):
        status,data=self.call()
        self.assertEqual(status,"200 OK")
        self.assertEqual(data,[])
        self.assertEqual(history.call_args.kwargs["owner_uid"],UID)

    @patch("item_generation_http_v2.save_revision",return_value={
        "revision_number":1,"published":False,"can_publish":False})
    def test_save_uses_authenticated_owner_not_client_identity(self,saver):
        payload={"expected_parent_sha256":"a"*64,"citation_excerpts":{"0":"Verified quote"},
                 "option_evidence":{},"reviewer_notes":"Checked source"}
        status,data=self.call("POST",payload)
        self.assertEqual(status,"201 Created")
        self.assertFalse(data["published"])
        self.assertEqual(saver.call_args.kwargs["owner_uid"],UID)
        self.assertEqual(saver.call_args.kwargs["citation_excerpts"],{0:"Verified quote"})
        self.assertNotIn("trusted_passages",saver.call_args.kwargs)

    @patch("item_generation_http_v2.save_revision")
    def test_validation_failure_returns_rule_ids_without_saving(self,saver):
        from item_draft_revision_storage_v2 import RevisionValidationError
        saver.side_effect=RevisionValidationError([{"rule_id":"R-12.4","message":"Missing option evidence"}])
        payload={"expected_parent_sha256":"a"*64,"citation_excerpts":{},
                 "option_evidence":{},"reviewer_notes":"Verified source"}
        status,data=self.call("POST",payload)
        self.assertEqual(status,"422 Unprocessable Entity")
        self.assertEqual(data["error"],"revision_validation_failed")
        self.assertEqual(data["issues"][0]["rule_id"],"R-12.4")

    @patch("item_generation_http_v2.save_revision")
    def test_rejects_client_identity_and_invalid_citation_index(self,saver):
        payload={"expected_parent_sha256":"a"*64,"citation_excerpts":{"bad":"Quote"},
                 "option_evidence":{},"reviewer_notes":"Checked"}
        self.assertEqual(self.call("POST",payload)[0],"422 Unprocessable Entity")
        payload["citation_excerpts"]={"0":"Quote"}
        payload["owner_uid"]=UID
        self.assertEqual(self.call("POST",payload)[0],"422 Unprocessable Entity")
        saver.assert_not_called()

    @patch("item_generation_http_v2.save_revision")
    def test_rejects_unauthorized_requests_and_methods(self,saver):
        payload={"expected_parent_sha256":"a"*64,"citation_excerpts":{},
                 "option_evidence":{},"reviewer_notes":"Checked"}
        self.assertEqual(self.call("POST",payload,token="invalid")[0],"403 Forbidden")
        self.assertEqual(self.call("POST",payload,origin="https://srnastudytool.com")[0],"403 Forbidden")
        self.assertEqual(self.call("PUT",payload)[0],"405 Method Not Allowed")
        saver.assert_not_called()

class LiveDraftPersistenceTests(unittest.TestCase):
    def request(self, *, token="valid"):
        app = create_app(conn_factory=Connection,
            resolve_admin=lambda bearer: UID if bearer == "valid" else None,
            environment={"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true"})
        raw = json.dumps({**PAYLOAD, "textbook_id": "00000000-0000-4000-8000-000000000002"}).encode()
        env = {"PATH_INFO": "/generation/one", "REQUEST_METHOD": "POST",
               "HTTP_ORIGIN": "https://staging.srnastudytool.com",
               "HTTP_AUTHORIZATION": "Bearer " + token,
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        statuses = []
        body = b"".join(app(env, lambda status, headers: statuses.append(status)))
        return statuses[0], json.loads(body)

    @patch("item_generation_http_v2.save", return_value={
        "draft_id": "00000000-0000-4000-8000-000000000003", "status": "pending_review"})
    @patch("item_generation_http_v2.execute", return_value={
        "item": {"stem": "Synthetic"}, "save_payload": {"textbook_id": "00000000-0000-4000-8000-000000000002"},
        "can_publish": False, "database_writes": False})
    def test_live_result_saved_for_authenticated_owner_without_publication(self, execute, saver):
        status, data = self.request()
        self.assertEqual(status, "200 OK")
        self.assertEqual(data["draft_status"], "pending_review")
        self.assertFalse(data["published"])
        self.assertTrue(data["requires_human_review"])
        self.assertEqual(data["draft_id"], "00000000-0000-4000-8000-000000000003")
        self.assertEqual(saver.call_args.args[1]["owner_uid"], UID)

    @patch("item_generation_http_v2.save_once", return_value={
        "draft_id": "00000000-0000-4000-8000-000000000003", "status": "pending_review"})
    @patch("item_generation_http_v2.save")
    @patch("item_generation_http_v2.execute", return_value={
        "item": {"stem": "Synthetic"},
        "save_payload": {"textbook_id": "00000000-0000-4000-8000-000000000002"},
        "_checkpoint_key": {"textbook_id": "00000000-0000-4000-8000-000000000002",
                            "request_hash": "a" * 64, "evidence_hash": "b" * 64}})
    def test_checkpointed_retries_use_idempotent_save(self, execute, saver, save_once):
        first_status, first = self.request()
        second_status, second = self.request()
        self.assertEqual((first_status, second_status), ("200 OK", "200 OK"))
        self.assertEqual(first["draft_id"], second["draft_id"])
        self.assertNotIn("_checkpoint_key", first)
        self.assertFalse(first["published"])
        self.assertEqual(save_once.call_count, 2)
        saver.assert_not_called()

    @patch("item_generation_http_v2.save_once", side_effect=ValueError("Checkpoint draft association failed"))
    @patch("item_generation_http_v2.execute", return_value={
        "item": {"stem": "Synthetic"},
        "save_payload": {"textbook_id": "00000000-0000-4000-8000-000000000002"},
        "_checkpoint_key": {"textbook_id": "00000000-0000-4000-8000-000000000002",
                            "request_hash": "a" * 64, "evidence_hash": "b" * 64}})
    def test_checkpoint_link_failure_never_reports_saved_draft(self, execute, saver):
        status, data = self.request()
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertNotIn("draft_id", data)
        saver.assert_called_once()

    @patch("item_generation_http_v2.save_once")
    @patch("item_generation_http_v2.execute")
    def test_unauthorized_checkpoint_recovery_never_saves(self, execute, saver):
        status, data = self.request(token="invalid")
        self.assertEqual(status, "403 Forbidden")
        execute.assert_not_called()
        saver.assert_not_called()

    @patch("item_generation_http_v2.save", side_effect=ValueError("not ready"))
    @patch("item_generation_http_v2.execute", return_value={
        "item": {"stem": "Synthetic"}, "save_payload": {"textbook_id": "00000000-0000-4000-8000-000000000002"}})
    def test_save_failure_never_reports_success(self, execute, saver):
        status, data = self.request()
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertNotIn("draft_id", data)

    @patch("item_generation_http_v2.save")
    @patch("item_generation_http_v2.execute")
    def test_unauthorized_cannot_generate_or_save(self, execute, saver):
        self.assertEqual(self.request(token="invalid")[0], "403 Forbidden")
        execute.assert_not_called()
        saver.assert_not_called()

class HttpPreflightTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(conn_factory=Connection, resolve_admin=lambda token: UID if token == "valid" else None,
                              environment={"STAGING_ONLY": "true"})

    def call(self, payload=PAYLOAD, token="valid", origin="https://staging.srnastudytool.com"):
        raw = json.dumps(payload).encode()
        env = {"PATH_INFO": "/generation/preflight", "REQUEST_METHOD": "POST",
               "HTTP_ORIGIN": origin, "HTTP_AUTHORIZATION": "Bearer " + token,
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        seen = []
        body = b"".join(self.app(env, lambda status, headers: seen.append(status)))
        return seen[0], json.loads(body)

    @patch("item_generation_http_v2.execute", return_value={
        "dry_run": True, "passage_count": 2, "can_publish": False,
        "database_writes": False,
        "resume": {"resumable": True, "next_stage": "rationale",
                   "expires_in_seconds": 600}})
    def test_admin_preflight_returns_resume_metadata_without_paid_execution(self, execute):
        status, data = self.call({**PAYLOAD,
            "textbook_id": "00000000-0000-4000-8000-000000000002"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(data["resume"]["next_stage"], "rationale")
        self.assertTrue(data["resume"]["resumable"])
        self.assertTrue(data["dry_run"])
        self.assertFalse(execute.call_args.args[1].execute)

    @patch("item_generation_http_v2.execute", return_value={"dry_run": True, "passage_count": 2, "can_publish": False, "database_writes": False})
    def test_admin_preflight_only(self, execute):
        status, data = self.call()
        self.assertEqual(status, "200 OK")
        self.assertTrue(data["dry_run"])
        self.assertFalse(execute.call_args.args[1].execute)
        self.assertEqual(execute.call_args.args[1].owner_uid, UID)

    @patch("item_generation_http_v2.execute", return_value={"dry_run": False, "item": {"stem": "Sample"}, "can_publish": False, "database_writes": False, "save_payload": {}})
    @patch("item_generation_http_v2.save", return_value={"draft_id": "00000000-0000-4000-8000-000000000003", "status": "pending_review"})
    def test_single_question_requires_server_opt_in(self, saver, execute):
        raw = json.dumps({**PAYLOAD, "textbook_id": "00000000-0000-4000-8000-000000000002"}).encode()
        env = {"PATH_INFO": "/generation/one", "REQUEST_METHOD": "POST",
               "HTTP_ORIGIN": "https://staging.srnastudytool.com",
               "HTTP_AUTHORIZATION": "Bearer valid",
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        seen = []
        body = b"".join(self.app(env, lambda status, headers: seen.append(status)))
        self.assertEqual(seen[0], "403 Forbidden")
        execute.assert_not_called()
        enabled = create_app(conn_factory=Connection, resolve_admin=lambda token: UID if token == "valid" else None,
                             environment={"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true"})
        seen.clear()
        body = b"".join(enabled({**env, "wsgi.input": io.BytesIO(raw)}, lambda status, headers: seen.append(status)))
        self.assertEqual(seen[0], "200 OK")
        self.assertEqual(json.loads(body)["item"]["stem"], "Sample")
        self.assertTrue(execute.call_args.args[1].execute)
        self.assertTrue(execute.call_args.args[1].confirm_paid_calls)

    @patch("item_generation_http_v2.execute", return_value={
        "dry_run": False, "item": {"stem": "Synthetic"}, "can_publish": False,
        "database_writes": False, "save_payload": {}})
    @patch("item_generation_http_v2.save", return_value={"draft_id": "00000000-0000-4000-8000-000000000003", "status": "pending_review"})
    def test_live_generation_passes_trusted_semantic_lookup(self, saver, execute):
        calls = []
        callback = lambda item: {"embedding": [1.0, 0.0], "neighbors": [],
                                 "search_complete": True, "index_id": "staging"}
        def factory(conn, owner, textbook_id):
            calls.append((owner, textbook_id))
            return callback
        app = create_app(conn_factory=Connection,
            resolve_admin=lambda token: UID if token == "valid" else None,
            environment={"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true"},
            semantic_lookup_factory=factory)
        textbook = "00000000-0000-4000-8000-000000000002"
        raw = json.dumps({**PAYLOAD, "textbook_id": textbook}).encode()
        env = {"PATH_INFO": "/generation/one", "REQUEST_METHOD": "POST",
               "HTTP_ORIGIN": "https://staging.srnastudytool.com",
               "HTTP_AUTHORIZATION": "Bearer valid",
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        seen = []
        app(env, lambda status, headers: seen.append(status))
        self.assertEqual(seen[0], "200 OK")
        self.assertEqual(calls, [(UID, textbook)])
        self.assertIs(execute.call_args.kwargs["semantic_lookup"], callback)

    @patch("item_generation_http_v2.execute", return_value={
        "dry_run": True, "passage_count": 1, "can_publish": False,
        "database_writes": False})
    def test_preflight_does_not_create_semantic_lookup(self, execute):
        def forbidden_factory(*args):
            raise AssertionError("No semantic index needed for free preflight")
        app = create_app(conn_factory=Connection,
            resolve_admin=lambda token: UID if token == "valid" else None,
            environment={"STAGING_ONLY": "true"},
            semantic_lookup_factory=forbidden_factory)
        raw = json.dumps(PAYLOAD).encode()
        env = {"PATH_INFO": "/generation/preflight", "REQUEST_METHOD": "POST",
               "HTTP_ORIGIN": "https://staging.srnastudytool.com",
               "HTTP_AUTHORIZATION": "Bearer valid",
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        seen = []
        app(env, lambda status, headers: seen.append(status))
        self.assertEqual(seen[0], "200 OK")

    @patch("item_generation_http_v2.execute")
    def test_planning_diagnostics_are_allowlisted_and_never_echo_model_text(self, execute):
        for message, detail in [
            ("Concept card choice plan response invalid", "PLAN_RESPONSE_FIELDS"),
            ("Concept card choice plan repeats a response pattern", "PLAN_REPEATED_PATTERN"),
            ("Concept card references unknown passages", "CONCEPT_UNKNOWN_SOURCE"),
            ("Concept card private source text and secret", None),
        ]:
            execute.side_effect = ValueError(message)
            status, data = self.call()
            self.assertEqual(status, "422 Unprocessable Entity")
            self.assertEqual(data.get("validation_detail"), detail)
            self.assertNotIn(message, json.dumps(data))

    @patch("item_generation_http_v2.execute")
    def test_no_model_execution_from_http(self, execute):
        status, _ = self.call({**PAYLOAD, "execute": True})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_unauthorized_rejected_before_database(self, execute):
        status, _ = self.call(token="invalid")
        self.assertEqual(status, "403 Forbidden")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_other_origin_rejected(self, execute):
        status, _ = self.call(origin="https://srnastudytool.com")
        self.assertEqual(status, "403 Forbidden")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_paid_confirmation_rejected(self, execute):
        status, _ = self.call({**PAYLOAD, "confirm_paid_calls": True})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_invalid_blueprint_rejected_before_database(self, execute):
        for change in ({"section": "III.H"}, {"objective": "II.H.4"},
                       {"domain": "V"}, {"format": "TF"}):
            with self.subTest(change=change):
                status, _ = self.call({**PAYLOAD, **change})
                self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_boolean_limit_rejected(self, execute):
        status, _ = self.call({**PAYLOAD, "limit": True})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_duplicate_unknown_field_rejected(self, execute):
        status, _ = self.call({**PAYLOAD, "admin_override": True})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_invalid_range_rejected(self, execute):
        status, _ = self.call({**PAYLOAD, "page_start": 9, "page_end": 2})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

class DraftBasketHttpTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(conn_factory=Connection,
            resolve_admin=lambda token: UID if token == "valid" else None,
            environment={"STAGING_ONLY": "true"})

    def call(self, path, method="GET", payload=None, token="valid"):
        raw = json.dumps(payload).encode() if payload is not None else b""
        env = {"PATH_INFO": path, "REQUEST_METHOD": method,
               "HTTP_ORIGIN": "https://staging.srnastudytool.com",
               "HTTP_AUTHORIZATION": "Bearer " + token,
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        seen = []
        body = b"".join(self.app(env, lambda status, headers: seen.append(status)))
        return seen[0], json.loads(body) if body else {}

    @patch("item_generation_http_v2.list_drafts", return_value=[])
    def test_list_requires_admin(self, mock_list):
        status, data = self.call("/generation/drafts")
        self.assertEqual(status, "200 OK")
        self.assertEqual(data["drafts"], [])
        self.assertEqual(mock_list.call_args.kwargs["owner_uid"], UID)
        status, _ = self.call("/generation/drafts", token="invalid")
        self.assertEqual(status, "403 Forbidden")
        self.assertEqual(mock_list.call_count, 1)

    @patch("item_generation_http_v2.save", return_value={"status": "pending_review"})
    def test_save_uses_verified_owner(self, mock_save):
        status, data = self.call("/generation/drafts", "POST", {"topic": "airway"})
        self.assertEqual(status, "201 Created")
        self.assertEqual(mock_save.call_args.args[1]["owner_uid"], UID)
        self.assertEqual(data["status"], "pending_review")
        status, _ = self.call("/generation/drafts", "POST", {"owner_uid": UID})
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertEqual(mock_save.call_count, 1)

    @patch("item_generation_http_v2.get_draft", return_value={"published": False})
    def test_detail_scoped_to_owner(self, mock_get):
        draft_id = "00000000-0000-4000-8000-000000000002"
        status, data = self.call("/generation/drafts/" + draft_id)
        self.assertEqual(status, "200 OK")
        self.assertEqual(mock_get.call_args.kwargs["owner_uid"], UID)
        self.assertFalse(data["published"])

    @patch("item_generation_http_v2.review", return_value={"published": False})
    def test_review_uses_verified_reviewer(self, mock_review):
        draft_id = "00000000-0000-4000-8000-000000000002"
        status, _ = self.call("/generation/drafts/" + draft_id + "/review",
                              "POST", {"status": "rejected", "notes": "Unsupported"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(mock_review.call_args.kwargs["reviewer_uid"], UID)
        self.assertEqual(mock_review.call_args.kwargs["owner_uid"], UID)

if __name__ == "__main__":
    unittest.main()
