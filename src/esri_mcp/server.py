"""MCP server entry point — tools and resources for ArcGIS Feature Services."""
from __future__ import annotations

import asyncio
import json
from urllib.parse import quote, unquote

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    TextContent,
    Tool,
)

import esri_mcp.feature_service as fs
from .config import config

app = Server("esri-mcp")


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@app.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="esri://services",
            name="Feature Services",
            description="Search the ArcGIS portal for feature services",
            mimeType="application/json",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    parts = uri.removeprefix("esri://").split("/")

    if uri == "esri://services":
        results = await fs.search_services("", max_results=20)
        return json.dumps(results, indent=2)

    # esri://service/<encoded_url>/layers
    if len(parts) >= 3 and parts[0] == "service" and parts[-1] == "layers":
        service_url = unquote(parts[1])
        info = await fs.get_service_info(service_url)
        layers = [
            {"id": l.get("id"), "name": l.get("name"), "type": l.get("type")}
            for l in info.get("layers", []) + info.get("tables", [])
        ]
        return json.dumps(layers, indent=2)

    # esri://service/<encoded_url>/layer/<id>/schema
    if len(parts) >= 5 and parts[0] == "service" and parts[2] == "layer" and parts[-1] == "schema":
        service_url = unquote(parts[1])
        layer_id = int(parts[3])
        info = await fs.get_layer_info(service_url, layer_id)
        schema = {
            "name": info.get("name"),
            "type": info.get("type"),
            "geometryType": info.get("geometryType"),
            "fields": info.get("fields", []),
        }
        return json.dumps(schema, indent=2)

    raise ValueError(f"Unknown resource URI: {uri}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_feature_services",
            description="Search the ArcGIS portal for feature services. Returns service titles and URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keywords (e.g. 'zoning', 'parcels')"},
                    "max_results": {"type": "integer", "default": 10, "description": "Max number of results (1-50)"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_layer_info",
            description="Get metadata and field schema for a specific layer in a Feature Service.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_url": {"type": "string", "description": "Full URL of the Feature Service"},
                    "layer_id": {"type": "integer", "description": "Layer index (0-based)"},
                },
                "required": ["service_url", "layer_id"],
            },
        ),
        Tool(
            name="query_features",
            description=(
                "Query features from a layer using SQL where clause and optional spatial filter. "
                "Returns GeoJSON features."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "service_url": {"type": "string"},
                    "layer_id": {"type": "integer"},
                    "where": {"type": "string", "default": "1=1", "description": "SQL where clause"},
                    "out_fields": {"type": "string", "default": "*", "description": "Comma-separated field names, or * for all"},
                    "geometry_filter": {
                        "type": "object",
                        "description": "Optional spatial filter with keys: geometry (ESRI JSON), geometryType, spatialRel",
                    },
                    "max_records": {"type": "integer", "default": 100, "description": "Maximum features to return"},
                },
                "required": ["service_url", "layer_id"],
            },
        ),
        Tool(
            name="add_features",
            description="Add new features to a layer. Requires authentication. Features must be GeoJSON.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_url": {"type": "string"},
                    "layer_id": {"type": "integer"},
                    "features": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of GeoJSON Feature objects",
                    },
                },
                "required": ["service_url", "layer_id", "features"],
            },
        ),
        Tool(
            name="update_features",
            description=(
                "Update existing features. Requires authentication. "
                "Each GeoJSON feature must include OBJECTID in its properties."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "service_url": {"type": "string"},
                    "layer_id": {"type": "integer"},
                    "features": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of GeoJSON Feature objects with OBJECTID in properties",
                    },
                },
                "required": ["service_url", "layer_id", "features"],
            },
        ),
        Tool(
            name="delete_features",
            description="Delete features by OBJECTID list or SQL where clause. Requires authentication.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_url": {"type": "string"},
                    "layer_id": {"type": "integer"},
                    "object_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of OBJECTIDs to delete",
                    },
                    "where": {"type": "string", "description": "SQL where clause (alternative to object_ids)"},
                },
                "required": ["service_url", "layer_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]


async def _dispatch(name: str, args: dict):
    if name == "list_feature_services":
        return await fs.search_services(args["query"], max_results=min(args.get("max_results", 10), 50))

    if name == "get_layer_info":
        return await fs.get_layer_info(args["service_url"], args["layer_id"])

    if name == "query_features":
        return await fs.query_features(
            service_url=args["service_url"],
            layer_id=args["layer_id"],
            where=args.get("where", "1=1"),
            out_fields=args.get("out_fields", "*"),
            geometry_filter=args.get("geometry_filter"),
            max_records=min(args.get("max_records", 100), 1000),
        )

    if name == "add_features":
        return await fs.add_features(args["service_url"], args["layer_id"], args["features"])

    if name == "update_features":
        return await fs.update_features(args["service_url"], args["layer_id"], args["features"])

    if name == "delete_features":
        return await fs.delete_features(
            service_url=args["service_url"],
            layer_id=args["layer_id"],
            object_ids=args.get("object_ids"),
            where=args.get("where"),
        )

    raise ValueError(f"Unknown tool: {name}")


def main() -> None:
    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
