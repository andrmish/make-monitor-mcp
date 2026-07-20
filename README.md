# Make Monitor MCP v4

Read-only MCP server for Make.com monitoring and Airtable configuration analysis.

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

Do not add any write or run scopes.

## Railway update

Replace the files in the existing GitHub repository with this version and commit.
Railway should redeploy automatically.

If you prefer to keep the current repository unchanged, create a new private repo
and deploy it as a new Railway service using the same environment variables.

## ChatGPT refresh

After Railway redeploys:

1. Open ChatGPT Settings → Apps.
2. Open Make Monitor.
3. Refresh/reconnect the app so ChatGPT re-reads the MCP tool list.
4. Verify the new tools appear.

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
