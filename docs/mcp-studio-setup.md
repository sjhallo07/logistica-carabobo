# MCP Studio setup for `logistica-carabobo`

## What is local vs remote here?

- `logisticaStudioLocal` in `.vscode/mcp.json` is a **local HTTP MCP server** because it points to `localhost`.
- `supabaseRemote` in `.vscode/mcp.json` is a **remote MCP server** because it points to `https://mcp.supabase.com/...`.
- `mcp_server.py` in this repo is currently a **REST bridge**, not a native VS Code MCP protocol server. It is useful for app/runtime integrations, but VS Code MCP Studio talks to the servers declared in `.vscode/mcp.json`.

## Suggested MCP tool scope for this project

Recommended Supabase features for the remote MCP server:

- `database` — query coupon/promotions tables
- `docs` — schema/docs lookup while building prompts and migrations
- `storage` — media/assets if you later store flyers or images
- `functions` — edge functions for ingestion or enrichment
- `development` — debugging while iterating in Studio

## Suggested inputs in `.vscode/mcp.json`

- `localMcpUrl` — example: `http://localhost:6274/mcp`
- `supabaseProjectRef` — your project ref
- `supabaseAccessToken` — Supabase personal access token
- `supabaseFeatures` — example: `database,docs,storage,functions,development`

## Agentic routing practice used in code

The app now uses a query router that:

1. restricts country scope to Venezuela by default (`VE`)
2. caps search radius at 100 miles
3. only marks a query as MCP-worthy when it contains both:
   - promotion/location keywords like `comida`, `farmatodo`, `Valencia`, `Naguanagua`, `Sambil`
   - a number/code pattern like `2x1`, `25%`, `PROMO10`

This keeps the agent from firing expensive tools for every vague message.

## Safe scraping practice

The helper in `core/query_router.py` checks `robots.txt` before fetching any page.
Use `BeautifulSoup` by default. Only enable Selenium when the site requires rendering and you have the proper driver/browser installed.
