# Make Monitor MCP v5

MCP server for Make.com monitoring, authenticated scenario editing, and read-only
Airtable configuration analysis.

## Scenario editing in v5

The existing `/mcp` connection remains read-only. The editor is a separate,
authenticated MCP transport on the same Railway service, with all existing read
tools plus:

- `get_editor_status` — capabilities; does not claim the Make token has write access
- `get_scenario_for_edit` — complete latest saved draft, concurrency version, and SHA-256 revision
- `preview_scenario_update` — validate the proposed complete blueprint and summarize changes without saving
- `update_scenario` — save a revised blueprint and read back the result

Editing is limited to the configured `MAKE_TEAM_ID`. The caller must supply the
version and revision of the blueprint it edited. Both are checked before saving;
`baseVersion` is also passed to Make to reject a concurrent edit during the request.
The editor reads the latest saved draft explicitly rather than overwriting it from
an older published blueprint. Empty blueprints and duplicate module IDs are refused.
Schedules, activation state, execution queues and Airtable are not changed by these
tools. The editor has no run, stop, activate, retry, or delete commands.

Successful saves return `saved: true`; only matching read-back returns `verified: true`.
If a write times out or read-back fails, inspect the current blueprint before
retrying. Never automatically replay an uncertain save. Make retains blueprint
history under its own retention rules; this service does not promise permanent backups.

### Private editor connection

Set `MCP_EDITOR_TOKEN` in Railway to a random URL-safe secret with at least 256 bits
of entropy (for example, `secrets.token_urlsafe(32)`). Without this variable, the
editor is disabled and the public reader continues working.

Clients that support custom headers can use `/editor/mcp` with
`Authorization: Bearer <MCP_EDITOR_TOKEN>`.

For private ChatGPT connections without custom headers, use:

```text
https://<service-domain>/editor/<MCP_EDITOR_TOKEN>/mcp
```

This URL is a credential: anyone holding it can use the editor within the configured
Make team. Keep it private, never put it in this repository or a public plugin,
and rotate the token if it is disclosed. Server access logging is disabled;
infrastructure HTTP logs may still contain request paths. `MCP_EDITOR_URL` can be
stored as a convenience in Railway variables for the owner to copy into ChatGPT.
Do not put the Make API token in the URL.

Update the private custom app's MCP server URL to the editor URL and refresh its
tools; if the client does not allow changing an existing server URL, add a private
connection with that URL and Authentication set to None (the URL already carries
the credential). Do not publish this connection. The original `/mcp` connection
keeps its existing read-only tool set.

`GET /health` returns the release version and whether an editor credential is
configured, without returning secrets.

### Validation

```sh
python -m unittest -v test_server_helpers test_editor
```

Tests cover real MCP transport discovery and access isolation, cross-team rejection,
concurrent/stale saves, JSON serialization, permission failures, and uncertain
write outcomes. They use synthetic blueprints and never change a live Make scenario.

## New Airtable tools in v4

- `list_airtable_tables` — table names and IDs in the configured base
- `get_airtable_table_schema` — fields, types, options, and views for one table
- `get_airtable_records` — paginated record reads with optional view, formula, and field filters

All Airtable tools are read-only and return at most 500 records per call.

## Required Airtable variables

Configure these in Railway service variables, never in the repository:

```text
AIRTABLE_API_TOKEN=pat...
AIRTABLE_BASE_ID=app...
```

The Airtable personal access token needs only these scopes and should be restricted
to the single settings base:

```text
data.records:read
schema.bases:read
```

Do not add any Airtable write scopes.

## New tools in v2

- `get_recent_executions` — success, warning, error, or all
- `get_recent_warnings`
- `get_scenario_logs`
- `get_execution_log`
- `get_module_operations` — aggregated warnings/errors by module
- `get_module_logs`
- `list_incomplete_executions`
- `get_incomplete_execution_details`

## New tools in v3

- `get_scenario_details` — scenario metadata and scheduling
- `get_scenario_blueprint` — current or historical blueprint
- `get_scenario_module` — configuration and mappings for one module

v3 also fixes `get_recent_errors` and `get_recent_warnings` failing with
`'FunctionTool' object is not callable` under FastMCP 2.x.

Existing tools remain:

- `list_scenarios`
- `get_recent_errors`
- `get_execution_details`

## Required Make API scopes

For scenarios, warnings, execution logs, and module logs:

```text
scenarios:read
```

For incomplete executions:

```text
dlqs:read
```

For authenticated scenario editing, also add `scenarios:write` to the Make token.
Keep `dlqs:read` if incomplete-execution diagnostics are needed. No run scope is
needed by this release. The token owner's Make team role must also permit editing.

## Railway update

Replace the files in the existing GitHub repository with this version and commit.
Railway should redeploy automatically.

If you prefer to keep the current repository unchanged, create a new private repo
and deploy it as a new Railway service using the same environment variables.

## ChatGPT refresh

After Railway redeploys:

1. Open ChatGPT Settings → Apps.
2. Open Make Monitor.
3. To use the editor, switch to the private editor connection described above.
4. Refresh/reconnect the app so ChatGPT re-reads the MCP tool list.
5. Verify `get_scenario_for_edit`, `preview_scenario_update`, and `update_scenario` appear.

## Example prompts

```text
Проверь ошибки и warnings Make за последние 4 часа.
```

```text
Покажи warnings сценария 005.1 за последние сутки.
```

```text
Покажи статистику warnings и errors по модулям сценария за 7 дней.
```

```text
Проверь incomplete executions сценария 6545632.
```

