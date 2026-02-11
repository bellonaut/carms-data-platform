from pathlib import Path
from typing import Dict, Tuple, List

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlmodel import Session, select

from carms.core.database import get_session
from carms.models.gold import GoldGeoSummary

router = APIRouter(tags=["map"])

# Rough centroids (demo-appropriate)
# lat, lon in degrees
PROVINCE_CENTROIDS: Dict[str, Tuple[float, float, str]] = {
    "BC": (53.7267, -127.6476, "British Columbia"),
    "AB": (53.9333, -116.5765, "Alberta"),
    "SK": (52.9399, -106.4509, "Saskatchewan"),
    "MB": (53.7609, -98.8139, "Manitoba"),
    "ON": (51.2538, -85.3232, "Ontario"),
    "QC": (52.9399, -73.5491, "Quebec"),
    "NB": (46.5653, -66.4619, "New Brunswick"),
    "NS": (44.6820, -63.7443, "Nova Scotia"),
    "PE": (46.5107, -63.4168, "Prince Edward Island"),
    "NL": (53.1355, -57.6604, "Newfoundland and Labrador"),
    "YT": (64.2823, -135.0000, "Yukon"),
    "NT": (64.8255, -124.8457, "Northwest Territories"),
    "NU": (70.2998, -83.1076, "Nunavut"),
}


@router.get("/map", response_class=FileResponse)
def map_page() -> FileResponse:
    # /app/carms/api/routes/geo_map.py -> /app/carms/api/templates/map.html
    html_path = Path(__file__).resolve().parent.parent / "templates" / "map.html"
    return FileResponse(str(html_path), media_type="text/html")


@router.get("/map/canada.geojson", response_class=FileResponse)
def map_geojson() -> FileResponse:
    # Serve the static GeoJSON used by the choropleth map
    geojson_path = (
        Path(__file__).resolve().parents[2] / "static" / "map" / "canada.geojson"
    )
    return FileResponse(str(geojson_path), media_type="application/geo+json")


@router.get("/map/data.json")
def map_data(session: Session = Depends(get_session)) -> List[dict]:
    # Aggregate: total program_count per province
    stmt = (
        select(
            GoldGeoSummary.province,
            func.sum(GoldGeoSummary.program_count).label("programs"),
        )
        .group_by(GoldGeoSummary.province)
    )
    rows = session.exec(stmt).all()

    points: List[dict] = []
    for province, programs in rows:
        if not province or province == "UNKNOWN":
            continue

        meta = PROVINCE_CENTROIDS.get(province)
        if not meta:
            continue

        lat, lon, name = meta
        points.append(
            {
                "province": province,
                "name": name,
                "lat": lat,
                "lon": lon,
                "programs": int(programs or 0),
            }
        )

    # Largest first; stable ordering for ties
    points.sort(key=lambda x: (-x["programs"], x["province"]))
    return points
