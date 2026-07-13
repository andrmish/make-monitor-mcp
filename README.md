# Make Monitor MCP v2

Read-only MCP server for Make.com monitoring.

## New tools in v2

- `get_recent_executions` — success, warning, error, or all
- `get_recent_warnings`
- `get_scenario_logs`
- `get_execution_log`
- `get_module_operations` — aggregated warnings/errors by module
- `get_module_logs`
- `list_incomplete_executions`
- `get_incomplete_execution_details`

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
