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
