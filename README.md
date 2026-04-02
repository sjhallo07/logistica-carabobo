# Logistica Carabobo — Local MCP Usage

This project includes a local MCP (Meta/Model Control Plane) HTTP server and client configuration to allow searching Instagram profiles/hashtags and performing web searches as a fallback.

## Local MCP server (FastAPI)

A lightweight MCP server is available at `mcp_server.py` in the project root. It exposes the following endpoints (all under `/mcp`):

- `GET /mcp/health` — health check
- `POST /mcp/search_instagram_profile` — body: { "profile_url": "<https://www.instagram.com/yourprofile>", "limit": 25 }
- `POST /mcp/search_instagram_hashtag` — body: { "hashtag": "promociones", "limit": 25, "since": "2026-03-01T00:00:00Z" }
- `POST /mcp/web_search_google` — body: { "query": "cupones comida valencia venezuela", "limit": 5 }
- `POST /mcp/get_traffic_arc` — body: { "segment": "San Diego" }
- `POST /mcp/verify_logistics_coupon` — body: { "code": "FIRST2026" }

Run the server locally (in the project root):

```powershell
# install dependencies first
python -m pip install -r requirements.txt
# run uvicorn from the project directory
python -m uvicorn mcp_server:app --app-dir . --host 0.0.0.0 --port 9000 --reload
```

The server will be available at `http://localhost:9000` and the MCP endpoints at `http://localhost:9000/mcp/*`.

## Client configuration (`.vscode/mcp.json`)

A local MCP client configuration is included at `.vscode/mcp.json`. Important entries:

- `servers.my-mcp-server-df3ec9ee.url` — base URL template for the MCP server (uses `{port}` placeholder)
- `servers.my-mcp-server-df3ec9ee.allowedModels` — list of allowed model identifiers for this MCP server. Example (partial):

```
"allowedModels": [
  "copilot/auto",
  "copilotcli/gpt-5.4",
  "copilot/gpt-5.1",
  "copilot/gpt-5.2",
  "copilot/gpt-5.4-mini",
  "copilot/gemini-3.1-pro-preview",
  "copilot/oswe-vscode-prime"
]
```

The full `allowedModels` list is stored in `.vscode/mcp.json` in the repository.

## Scraping behavior and robots.txt

The MCP bridge includes public scraping fallbacks when Instagram API credentials are not configured. The config file contains a `scraping.ignoreRobotsTxt` flag (set to `true`) to permit those fallbacks locally.

IMPORTANT: Scraping public websites may violate Terms of Service. Prefer using the Instagram Graph API (official) and commercial search APIs (SerpAPI / Google Custom Search) for production.

## Environment variables

To enable the Instagram Graph API integration, add the following to your `.env` file in the project root:

```
IG_ACCESS_TOKEN=your_facebook_ig_graph_access_token
IG_BUSINESS_ID=your_ig_business_user_id
IG_API_VERSION=v17.0
SUPABASE_URL=https://<your-supabase>.supabase.co
SUPABASE_KEY=<your-supabase-key>
```

If `IG_ACCESS_TOKEN` and `IG_BUSINESS_ID` are not set, the MCP server will return stubbed/scraped results depending on availability.

## Docker registry / CI notes

If you need to push Docker images from CI or perform a docker login in a script, set these environment variables (for example in your CI secrets or Hugging Face Spaces environment variables):

```
DOCKER_USERNAME=your_docker_username
DOCKER_PAT=your_docker_personal_access_token_or_password
```

To login non-interactively in a shell script:

```bash
echo "$DOCKER_PAT" | docker login -u "$DOCKER_USERNAME" --password-stdin
```

Hugging Face Spaces does not require Docker Hub credentials to build a Docker-based Space (it builds the image on HF infra), but CI flows that push images to external registries will need the above credentials.

## Example usage (curl)

Search Instagram profile (public fallback):

```bash
curl -X POST http://localhost:9000/mcp/search_instagram_profile \
  -H "Content-Type: application/json" \
  -d '{"profile_url":"https://www.instagram.com/cuponmania.ve","limit":10}'
```

Search hashtag:

```bash
curl -X POST http://localhost:9000/mcp/search_instagram_hashtag \
  -H "Content-Type: application/json" \
  -d '{"hashtag":"promociones","limit":20}'
```

Web search (best-effort):

```bash
curl -X POST http://localhost:9000/mcp/web_search_google \
  -H "Content-Type: application/json" \
  -d '{"query":"cupones comida valencia venezuela","limit":5}'
```

## Persisting results

The project currently extracts candidate coupon codes but does not automatically persist them. Recommended next steps:

- Add a `instagram_coupons` table in Supabase and implement `save_instagram_coupons()` in `core/database.py`.
- Create a scheduled job (GitHub Action or server cron) that queries MCP endpoints periodically and saves new coupons.

## Security & Compliance

- Store API keys and tokens in `.env` and never commit them.
- Review Instagram and Google ToS — scraping may be disallowed.

---

If you want, I can now:

- Add `save_instagram_coupons()` and SQL migration for Supabase (automate persistence).
- Add a GitHub Action that runs periodic searches and saves results.
- Add a validation in the MCP server to reject requests specifying models not in `allowedModels`.

Tell me which of the above to implement next and I will proceed.
