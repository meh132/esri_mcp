# esri-mcp

An MCP (Model Context Protocol) server that connects Claude to ArcGIS Feature Services, enabling AI-powered interaction with geographic data.

## Features

- Search ArcGIS portals for feature services
- Inspect layer schemas and metadata
- Query features with SQL where clauses and spatial filters (returns GeoJSON)
- Add, update, and delete features (requires authentication)

## Requirements

- Python 3.11+
- An ArcGIS server URL (defaults to `https://boston.maps.arcgis.com`)
- Optional: ArcGIS credentials for write operations

## Installation

```bash
pip install .
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install .
```

## Configuration

Create a `.env` file in the project root:

```env
ESRI_SERVER_URL=https://your-org.maps.arcgis.com
ESRI_USERNAME=your_username
ESRI_PASSWORD=your_password
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `ESRI_SERVER_URL` | No | `https://boston.maps.arcgis.com` | ArcGIS portal URL |
| `ESRI_USERNAME` | No | — | Username for write operations |
| `ESRI_PASSWORD` | No | — | Password for write operations |

## Usage

Run the MCP server:

```bash
esri-mcp
```

### Connecting to Claude Desktop

Add the server to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "esri": {
      "command": "esri-mcp"
    }
  }
}
```

## Testing from the Command Line

The server uses SSE transport. Requests are sent via POST and responses arrive on the open SSE stream, so you need two terminals.

> **Windows note:** In PowerShell, `curl` is an alias for `Invoke-WebRequest`. Use `curl.exe` or `Invoke-RestMethod` as shown below.

### Step 1 — Open the SSE stream (Terminal 1, keep it running)

```powershell
curl.exe -k -N https://localhost:8000/sse
```

This returns an `endpoint` event containing your session ID, e.g.:
```
event: endpoint
data: /messages/?session_id=abc123...
```

### Step 2 — Send requests (Terminal 2)

Replace `<SESSION_ID>` with the value from Step 1.

**Initialize the session:**
```powershell
Invoke-RestMethod -Uri "https://localhost:8000/messages/?session_id=<SESSION_ID>" -Method POST -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}'
```

**List available tools:**
```powershell
Invoke-RestMethod -Uri "https://localhost:8000/messages/?session_id=<SESSION_ID>" -Method POST -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

**Search for feature services:**
```powershell
Invoke-RestMethod -Uri "https://localhost:8000/messages/?session_id=<SESSION_ID>" -Method POST -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_feature_services","arguments":{"query":"parcels","max_results":3}}}'
```

**Query features from a layer:**
```powershell
Invoke-RestMethod -Uri "https://localhost:8000/messages/?session_id=<SESSION_ID>" -Method POST -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"query_features","arguments":{"service_url":"https://your-org.maps.arcgis.com/arcgis/rest/services/YourService/FeatureServer","layer_id":0,"where":"1=1","max_records":5}}}'
```

Each POST returns `202 Accepted` — check Terminal 1 for the actual response.

### Alternative: MCP Inspector (browser UI)

```powershell
pip install "mcp[cli]"
mcp dev https://localhost:8000/sse
```

Opens a browser-based tool explorer with no manual JSON required.

## Available Tools

| Tool | Description |
|---|---|
| `list_feature_services` | Search the portal for feature services by keyword |
| `get_layer_info` | Get metadata and field schema for a layer |
| `query_features` | Query features with SQL/spatial filters, returns GeoJSON |
| `add_features` | Add new features to a layer |
| `update_features` | Update existing features by OBJECTID |
| `delete_features` | Delete features by OBJECTID or SQL where clause |

## Project Structure

```
src/esri_mcp/
├── server.py          # MCP server, resources, and tool definitions
├── feature_service.py # ArcGIS REST client and geometry conversion
├── auth.py            # Token management and refresh logic
├── config.py          # Configuration via environment variables
└── __init__.py
```
