import asyncio
import copy
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastmcp import FastMCP
from starlette.testclient import TestClient

from editor import ScenarioEditor, blueprint_payload, build_app, revision, validate_blueprint

BP = {"name": "Test", "flow": [{"id": 1, "module": "util:SetVariable2", "version": 1,
                                 "mapper": {"name": "x", "value": "old"}}], "metadata": {"version": 1}}
TOKEN = "a" * 43


class EditorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bp = copy.deepcopy(BP)
        self.version = 7
        self.team = 123
        self.get = AsyncMock(side_effect=self.fake_get)
        self.editor = ScenarioEditor(self.get, 123, "https://eu1.make.com/api/v2", {"Authorization": "Token test"})

    async def fake_get(self, path, params=None):
        if path.endswith("/blueprint"):
            self.assertEqual(params, {"draft": "true"})
            return {"response": {"blueprint": copy.deepcopy(self.bp), "version": self.version}}
        return {"scenario": {"id": 42, "teamId": self.team, "name": "Test", "isActive": True}}

    def proposed(self):
        bp = copy.deepcopy(BP)
        bp["flow"][0]["mapper"]["value"] = "corrected"
        return bp

    async def test_read_and_preview_never_write(self):
        self.editor.patch = AsyncMock()
        current = await self.editor.load(42)
        self.assertEqual(current["version"], 7)
        result = await self.editor.preview(42, self.proposed())
        self.assertTrue(result["has_changes"])
        self.assertFalse(result["saved"])
        self.assertEqual(result["changes"]["changed_module_ids"], [1])
        self.editor.patch.assert_not_awaited()

    async def test_success_readback_and_version(self):
        async def save(scenario_id, blueprint, version):
            self.assertEqual((scenario_id, version), (42, 7))
            self.bp = blueprint
            self.version = 8
        self.editor.patch = AsyncMock(side_effect=save)
        result = await self.editor.update(42, self.proposed(), 7, revision(BP))
        self.assertEqual(result["status"], "saved_verified")
        self.assertTrue(result["verified"])
        self.assertEqual(result["version"], 8)
        self.editor.patch.assert_awaited_once()

    async def test_stale_version_and_revision_refused(self):
        self.editor.patch = AsyncMock()
        for version, digest in [(6, revision(BP)), (7, "b" * 64)]:
            with self.assertRaisesRegex(ValueError, "changed"):
                await self.editor.update(42, self.proposed(), version, digest)
        self.editor.patch.assert_not_awaited()

    async def test_other_team_refused_before_blueprint_read(self):
        self.team = 999
        with self.assertRaisesRegex(ValueError, "team"):
            await self.editor.update(42, self.proposed(), 7, revision(BP))
        self.assertEqual(self.get.await_count, 1)

    async def test_identical_blueprint_is_not_sent(self):
        self.editor.patch = AsyncMock()
        result = await self.editor.update(42, BP, 7, revision(BP))
        self.assertEqual(result["status"], "no_changes")
        self.editor.patch.assert_not_awaited()

    async def test_readback_failure_does_not_repeat_save(self):
        self.editor.patch = AsyncMock()
        old_load = self.editor.load
        current = await old_load(42)
        self.editor.load = AsyncMock(side_effect=[current, RuntimeError("network")])
        result = await self.editor.update(42, self.proposed(), 7, revision(BP))
        self.assertEqual(result["status"], "saved_verification_pending")
        self.assertTrue(result["saved"])
        self.assertFalse(result["verified"])
        self.editor.patch.assert_awaited_once()

    async def test_normalized_readback_not_claimed_verified(self):
        self.editor.patch = AsyncMock()  # Simulate API accepting, but returning a different blueprint.
        result = await self.editor.update(42, self.proposed(), 7, revision(BP))
        self.assertEqual(result["status"], "saved_readback_differs")
        self.assertFalse(result["verified"])

    async def test_patch_sends_only_blueprint_and_concurrency_version(self):
        seen = []
        def respond(request):
            seen.append(request)
            return httpx.Response(200, json={"scenario": {"id": 42}})
        real_client = httpx.AsyncClient
        with patch("editor.httpx.AsyncClient", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw)):
            await self.editor.patch(42, self.proposed(), 7)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].method, "PATCH")
        body = json.loads(seen[0].content)
        self.assertEqual(set(body), {"blueprint", "baseVersion"})
        self.assertEqual(body["baseVersion"], 7)
        self.assertEqual(json.loads(body["blueprint"]), self.proposed())

    async def test_conflict_permissions_and_timeout_never_retry(self):
        real_client = httpx.AsyncClient
        for status, error in [(409, ValueError), (401, PermissionError), (403, PermissionError), (500, RuntimeError)]:
            seen = []
            def respond(request):
                seen.append(request)
                return httpx.Response(status, json={"error": "private-response-content"})
            with patch("editor.httpx.AsyncClient", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw)):
                with self.assertRaises(error) as exc:
                    await self.editor.patch(42, self.proposed(), 7)
            self.assertNotIn("private-response-content", str(exc.exception))
            self.assertEqual(len(seen), 1)
        def timeout(request):
            raise httpx.ReadTimeout("private details", request=request)
        with patch("editor.httpx.AsyncClient", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(timeout), **kw)):
            with self.assertRaisesRegex(RuntimeError, "unknown"):
                await self.editor.patch(42, self.proposed(), 7)

    def test_bad_blueprints_and_missing_version_refused(self):
        for bp in [{"flow": []}, {"flow": [BP["flow"][0], BP["flow"][0]]}, {"flow": [{"id": 1}]}]:
            with self.assertRaises(ValueError):
                validate_blueprint(bp)
        with self.assertRaises(ValueError):
            blueprint_payload({"response": {"blueprint": BP}})
        with self.assertRaises(ValueError):
            blueprint_payload({"response": {"blueprint": BP, "version": True}})


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.reader = FastMCP("reader")
        @self.reader.tool(annotations={"readOnlyHint": True})
        async def example_read() -> dict:
            return {"ok": True}
        self.service = ScenarioEditor(AsyncMock(), 123, "https://eu1.make.com/api/v2", {})
        self.app = asyncio.run(build_app(self.reader, self.service, TOKEN))

    @staticmethod
    def rpc(client, path, method, params=None, extra_headers=None):
        response = client.post(path, headers={"Accept": "application/json, text/event-stream", **(extra_headers or {})},
                               json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            data = json.loads(next(line[6:] for line in response.text.splitlines() if line.startswith("data: ")))
        else:
            data = response.json()
        return response, data

    def test_private_url_and_bearer_work_public_remains_read_only(self):
        with TestClient(self.app) as client:
            response, data = self.rpc(client, "/mcp", "initialize", {
                "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "tests", "version": "1"}})
            self.assertEqual(response.status_code, 200)
            session = {"mcp-session-id": response.headers["mcp-session-id"]}
            _, public = self.rpc(client, "/mcp", "tools/list", extra_headers=session)
            self.assertEqual([t["name"] for t in public["result"]["tools"]], ["example_read"])
            _, denied = self.rpc(client, "/mcp", "tools/call", {"name": "update_scenario", "arguments": {}}, session)
            self.assertTrue(denied.get("error") or denied.get("result", {}).get("isError"))
            for path, headers in [(f"/editor/{TOKEN}/mcp", {}), ("/editor/mcp", {"Authorization": f"Bearer {TOKEN}"})]:
                response, listing = self.rpc(client, path, "tools/list", extra_headers=headers)
                self.assertEqual(response.status_code, 200)
                tools = {t["name"]: t for t in listing["result"]["tools"]}
                self.assertIn("example_read", tools)
                self.assertIn("update_scenario", tools)
                self.assertFalse(tools["update_scenario"]["annotations"]["readOnlyHint"])
                self.assertTrue(tools["update_scenario"]["annotations"]["destructiveHint"])
                self.assertEqual(set(tools["update_scenario"]["inputSchema"]["required"]),
                                 {"scenario_id", "blueprint", "expected_version", "expected_revision"})
                _, status = self.rpc(client, path, "tools/call", {"name": "get_editor_status", "arguments": {}}, headers)
                self.assertNotIn(TOKEN, json.dumps(status))

    def test_missing_wrong_and_disabled_credentials_rejected(self):
        with TestClient(self.app) as client:
            for path in ["/editor/mcp", "/editor/wrong/mcp", f"/editor/{TOKEN}x/mcp"]:
                response = client.post(path, json={})
                self.assertEqual(response.status_code, 401)
        disabled = asyncio.run(build_app(FastMCP("disabled"), self.service, ""))
        with TestClient(disabled) as client:
            self.assertEqual(client.post(f"/editor/{TOKEN}/mcp", json={}).status_code, 401)

    def test_health_and_reader_instructions(self):
        with TestClient(self.app) as client:
            self.assertEqual(client.get("/health").json(), {"status": "ok", "version": "5.0.0", "editor_configured": True})
        with self.assertRaises(ValueError):
            asyncio.run(build_app(self.reader, self.service, "too-short"))


if __name__ == "__main__":
    unittest.main()
