"""REST client for ArcGIS Feature Service operations."""
from __future__ import annotations

import json
from typing import Any

import httpx

from .auth import token_manager
from .config import config


def _esri_to_geojson_geometry(esri_geom: dict) -> dict | None:
    """Convert ESRI geometry to GeoJSON geometry."""
    if not esri_geom:
        return None
    if "x" in esri_geom:  # point
        return {"type": "Point", "coordinates": [esri_geom["x"], esri_geom["y"]]}
    if "rings" in esri_geom:  # polygon
        return {"type": "Polygon", "coordinates": esri_geom["rings"]}
    if "paths" in esri_geom:  # polyline
        return {"type": "MultiLineString", "coordinates": esri_geom["paths"]}
    return esri_geom


def _feature_to_geojson(esri_feature: dict) -> dict:
    return {
        "type": "Feature",
        "geometry": _esri_to_geojson_geometry(esri_feature.get("geometry")),
        "properties": esri_feature.get("attributes", {}),
    }


def _geojson_to_esri_feature(geojson_feature: dict) -> dict:
    """Convert a GeoJSON Feature to ESRI feature format."""
    geom = geojson_feature.get("geometry")
    esri_geom: dict | None = None
    if geom:
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        if gtype == "Point":
            esri_geom = {"x": coords[0], "y": coords[1], "spatialReference": {"wkid": 4326}}
        elif gtype == "Polygon":
            esri_geom = {"rings": coords, "spatialReference": {"wkid": 4326}}
        elif gtype in ("LineString", "MultiLineString"):
            paths = [coords] if gtype == "LineString" else coords
            esri_geom = {"paths": paths, "spatialReference": {"wkid": 4326}}
    return {"geometry": esri_geom, "attributes": geojson_feature.get("properties", {})}


def _check_esri_error(body: dict) -> None:
    if "error" in body:
        err = body["error"]
        raise RuntimeError(f"ESRI error {err.get('code')}: {err.get('message')}")


async def _get(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    token = await token_manager.get_token(client)
    if token:
        params["token"] = token
    params.setdefault("f", "json")
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    body = resp.json()
    _check_esri_error(body)
    return body


async def _post(client: httpx.AsyncClient, url: str, data: dict) -> dict:
    token = await token_manager.get_token(client)
    if token:
        data["token"] = token
    data.setdefault("f", "json")
    resp = await client.post(url, data=data)
    resp.raise_for_status()
    body = resp.json()
    _check_esri_error(body)
    return body


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search_services(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search the portal for feature services."""
    async with httpx.AsyncClient() as client:
        body = await _get(client, config.portal_search_url, {
            "q": f"{query} type:\"Feature Service\"",
            "num": max_results,
        })
    return [
        {"title": r.get("title"), "url": r.get("url"), "id": r.get("id"), "owner": r.get("owner")}
        for r in body.get("results", [])
    ]


async def get_service_info(service_url: str) -> dict[str, Any]:
    """Return top-level metadata for a Feature Service."""
    async with httpx.AsyncClient() as client:
        return await _get(client, service_url, {})


async def get_layer_info(service_url: str, layer_id: int) -> dict[str, Any]:
    """Return metadata and field schema for a single layer."""
    async with httpx.AsyncClient() as client:
        return await _get(client, f"{service_url}/{layer_id}", {})


async def query_features(
    service_url: str,
    layer_id: int,
    where: str = "1=1",
    out_fields: str = "*",
    geometry_filter: dict | None = None,
    max_records: int = 100,
) -> list[dict]:
    """Query features, handling pagination automatically."""
    features: list[dict] = []
    offset = 0
    async with httpx.AsyncClient() as client:
        while True:
            params: dict[str, Any] = {
                "where": where,
                "outFields": out_fields,
                "returnGeometry": "true",
                "outSR": "4326",
                "resultOffset": offset,
                "resultRecordCount": min(max_records - len(features), 1000),
            }
            if geometry_filter:
                params["geometry"] = json.dumps(geometry_filter.get("geometry"))
                params["geometryType"] = geometry_filter.get("geometryType", "esriGeometryEnvelope")
                params["spatialRel"] = geometry_filter.get("spatialRel", "esriSpatialRelIntersects")

            body = await _get(client, f"{service_url}/{layer_id}/query", params)
            batch = [_feature_to_geojson(f) for f in body.get("features", [])]
            features.extend(batch)

            if not body.get("exceededTransferLimit") or len(features) >= max_records:
                break
            offset += len(batch)

    return features[:max_records]


async def add_features(service_url: str, layer_id: int, features: list[dict]) -> dict:
    """Add GeoJSON features to a layer. Returns ESRI add result."""
    esri_features = [_geojson_to_esri_feature(f) for f in features]
    async with httpx.AsyncClient() as client:
        return await _post(client, f"{service_url}/{layer_id}/addFeatures", {
            "features": json.dumps(esri_features),
        })


async def update_features(service_url: str, layer_id: int, features: list[dict]) -> dict:
    """Update existing features. Each GeoJSON feature must include OBJECTID in properties."""
    esri_features = [_geojson_to_esri_feature(f) for f in features]
    async with httpx.AsyncClient() as client:
        return await _post(client, f"{service_url}/{layer_id}/updateFeatures", {
            "features": json.dumps(esri_features),
        })


async def delete_features(
    service_url: str,
    layer_id: int,
    object_ids: list[int] | None = None,
    where: str | None = None,
) -> dict:
    """Delete features by OBJECTID list or where clause."""
    if not object_ids and not where:
        raise ValueError("Provide object_ids or where clause")
    data: dict[str, Any] = {}
    if object_ids:
        data["objectIds"] = ",".join(str(i) for i in object_ids)
    if where:
        data["where"] = where
    async with httpx.AsyncClient() as client:
        return await _post(client, f"{service_url}/{layer_id}/deleteFeatures", data)
