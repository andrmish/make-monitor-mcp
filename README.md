# Make Monitor MCP

Read-only MCP server for monitoring Make.com scenario errors from ChatGPT.

## Tools

- `list_scenarios`
- `get_recent_errors`
- `get_execution_details`

The server contains no Make write, run, stop, activate, deactivate, or delete methods.

## Required Make token scope

Create a separate Make API token with only:

```text
scenarios:read
```

Do not use an administrator token and do not commit the token to GitHub.

## Environment variables

```text
MAKE_API_TOKEN=...
MAKE_TEAM_ID=...
MAKE_ZONE=eu1
MAX_SCENARIOS=200
PORT=8000
```

Supported zones: `eu1`, `eu2`, `us1`, `us2`.

## Local Docker test

```bash
cp .env.example .env
# Fill in .env
docker build -t make-monitor .
docker run --rm --env-file .env -p 8000:8000 make-monitor
```

MCP endpoint:

```text
http://localhost:8000/mcp
```

## Railway deployment

1. Create a private GitHub repository and upload these files.
2. In Railway, choose **New Project → Deploy from GitHub repo**.
3. Add the environment variables under **Variables**.
4. Generate a public HTTPS domain.
5. The MCP URL will be:

```text
https://YOUR-SERVICE.up.railway.app/mcp
```

## Connect to ChatGPT

1. Open ChatGPT settings.
2. Enable Developer mode under Security and login.
3. Open Plugins/Apps and create a developer-mode app.
4. Enter the public MCP URL.
5. Verify that ChatGPT displays only the three read-only tools above.

## Test prompts

```text
Покажи список сценариев Make.
```

```text
Проверь ошибки Make за последние 24 часа. Для каждой ошибки укажи сценарий, время и execution ID.
```

```text
Изучи детали последней ошибки и объясни наиболее вероятную причину. Не выполняй никаких изменений.
```

## Security note

This starter version does not implement user authentication at the MCP layer.
Use it only for an initial private test, keep the deployment URL private, and do
not expose any write tools. For durable production use, add OAuth or place the
service behind an authentication layer compatible with ChatGPT MCP apps.
