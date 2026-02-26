#!/usr/bin/env python
"""Seed a tiny, synthetic dataset for the UI-only demo.

- Targets SQLite by default (`sqlite:///./demo.db`).
- Idempotent: skips seeding when rows already exist unless --force is set.
- Keeps data small but realistic enough for /programs and /map to render.
"""

from __future__ import annotations

import argparse
import os
import random
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import delete
from sqlmodel import Session, SQLModel, create_engine, select

from carms.models.gold import GoldGeoSummary, GoldProgramProfile
from carms.models.silver import SilverDiscipline

PROVINCES: list[tuple[str, str]] = [
    ("BC", "British Columbia"),
    ("AB", "Alberta"),
    ("SK", "Saskatchewan"),
    ("MB", "Manitoba"),
    ("ON", "Ontario"),
    ("QC", "Quebec"),
    ("NB", "New Brunswick"),
    ("NS", "Nova Scotia"),
    ("PE", "Prince Edward Island"),
    ("NL", "Newfoundland and Labrador"),
    ("YT", "Yukon"),
    ("NT", "Northwest Territories"),
    ("NU", "Nunavut"),
]

DISCIPLINES: list[tuple[int, str]] = [
    (100, "Internal Medicine"),
    (110, "Emergency Medicine"),
    (120, "Family Medicine"),
    (130, "Pediatrics"),
    (140, "Psychiatry"),
    (150, "General Surgery"),
    (160, "Obstetrics & Gynecology"),
]

SCHOOLS: dict[str, list[str]] = {
    "BC": ["UBC Faculty of Medicine", "Victoria Island Health"],
    "AB": ["University of Alberta", "University of Calgary"],
    "SK": ["University of Saskatchewan"],
    "MB": ["University of Manitoba"],
    "ON": [
        "University of Toronto",
        "McMaster University",
        "Western University",
        "Queen's University",
    ],
    "QC": ["McGill University", "Universite de Montreal", "Universite Laval"],
    "NB": ["Dalhousie Medicine New Brunswick"],
    "NS": ["Dalhousie University"],
    "PE": ["University of Prince Edward Island"],
    "NL": ["Memorial University"],
    "YT": ["Yukon University"],
    "NT": ["Aurora College"],
    "NU": ["Nunavut Arctic College"],
}

STREAMS = ["CMG", "IMG"]
SITES = ["Main Campus", "Teaching Hospital", "Community Site"]


def _connect_args_for_sqlite(db_url: str) -> dict:
    if not db_url.startswith("sqlite"):
        return {}
    # sqlite:///./demo.db -> ./demo.db
    path_part = db_url.replace("sqlite:///", "", 1)
    if path_part.startswith("/") and not path_part.startswith("//"):
        path_part = path_part[1:]
    db_path = Path(path_part)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return {"check_same_thread": False}


def _make_description(school: str, discipline: str, province: str, rng: random.Random) -> str:
    themes = [
        "collegial teaching culture",
        "broad community exposure",
        "subspecialty electives",
        "hands-on simulation labs",
        "research mentorship",
        "team-based care",
    ]
    focus = rng.sample(themes, k=2)
    return (
        f"{discipline} residency at {school} in {province}. "
        f"Focus on {focus[0]} and {focus[1]}, with protected teaching time and supportive faculty."
    )


def _generate_programs(rng: random.Random, rows: int) -> list[GoldProgramProfile]:
    programs: list[GoldProgramProfile] = []
    next_id = 12000

    # Ensure every province gets at least one discipline represented
    for prov_code, _ in PROVINCES:
        _, disc_name = rng.choice(DISCIPLINES)
        school = rng.choice(SCHOOLS.get(prov_code, [f"{prov_code} Medical Centre"]))
        stream = rng.choice(STREAMS)
        discipline_slug = disc_name.lower().replace(" ", "-")
        next_id += 1
        programs.append(
            GoldProgramProfile(
                program_stream_id=next_id,
                program_name=f"{disc_name} Residency",
                program_stream_name=f"{disc_name} ({stream})",
                program_stream=stream,
                discipline_name=disc_name,
                province=prov_code,
                school_name=school,
                program_site=rng.choice(SITES),
                program_url=f"https://example.edu/{prov_code.lower()}/{discipline_slug}",
                description_text=_make_description(school, disc_name, prov_code, rng),
                is_valid=True,
            )
        )

    # Fill the remainder with random variety
    while len(programs) < rows:
        _, disc_name = rng.choice(DISCIPLINES)
        prov_code, _ = rng.choice(PROVINCES)
        school = rng.choice(SCHOOLS.get(prov_code, [f"{prov_code} Medical Centre"]))
        stream = rng.choice(STREAMS)
        discipline_slug = disc_name.lower().replace(" ", "-")
        next_id += 1
        programs.append(
            GoldProgramProfile(
                program_stream_id=next_id,
                program_name=f"{disc_name} Residency",
                program_stream_name=f"{disc_name} ({stream})",
                program_stream=stream,
                discipline_name=disc_name,
                province=prov_code,
                school_name=school,
                program_site=rng.choice(SITES),
                program_url=(
                    f"https://example.edu/{prov_code.lower()}/{discipline_slug}-{stream.lower()}"
                ),
                description_text=_make_description(school, disc_name, prov_code, rng),
                is_valid=True,
            )
        )

    return programs


def _build_geo_summary(
    programs: Iterable[GoldProgramProfile], rng: random.Random
) -> list[GoldGeoSummary]:
    buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for p in programs:
        quota = rng.randint(1, 12)
        buckets[(p.province, p.discipline_name)].append(quota)

    summaries: list[GoldGeoSummary] = []
    for (prov, disc), quotas in buckets.items():
        avg_quota = sum(quotas) / len(quotas)
        summaries.append(
            GoldGeoSummary(
                province=prov,
                discipline_name=disc,
                program_count=len(quotas),
                avg_quota=avg_quota,
            )
        )
    return summaries


def _seed_disciplines(session: Session) -> None:
    # Minimal set of valid disciplines for /disciplines endpoint
    existing = session.exec(select(SilverDiscipline)).all()
    if existing:
        session.exec(delete(SilverDiscipline))
    session.add_all(
        [
            SilverDiscipline(discipline_id=disc_id, discipline=name, province=None, is_valid=True)
            for disc_id, name in DISCIPLINES
        ]
    )


def seed(db_url: str, rows: int, seed: int, force: bool) -> tuple[int, int]:
    connect_args = _connect_args_for_sqlite(db_url)
    engine = create_engine(db_url, echo=False, connect_args=connect_args)

    SQLModel.metadata.create_all(engine)

    rng = random.Random(seed)
    programs = _generate_programs(rng, rows)
    geo = _build_geo_summary(programs, rng)

    with Session(engine) as session:
        existing = session.exec(select(GoldProgramProfile.program_stream_id).limit(1)).first()
        if existing and not force:
            return 0, 0

        session.exec(delete(GoldGeoSummary))
        session.exec(delete(GoldProgramProfile))
        session.exec(delete(SilverDiscipline))
        session.commit()

        _seed_disciplines(session)
        session.add_all(programs)
        session.add_all(geo)
        session.commit()

    return len(programs), len(geo)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic demo data for the UI-only run")
    parser.add_argument(
        "--db-url",
        dest="db_url",
        default=os.getenv("DB_URL", "sqlite:///./demo.db"),
        help="Database URL (default: env DB_URL or sqlite demo.db)",
    )
    parser.add_argument(
        "--rows", dest="rows", type=int, default=70, help="Approx number of program rows to create"
    )
    parser.add_argument(
        "--seed", dest="seed", type=int, default=42, help="Random seed for deterministic output"
    )
    parser.add_argument("--force", action="store_true", help="Re-seed even if data already exists")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created_programs, created_geo = seed(args.db_url, args.rows, args.seed, args.force)
    if created_programs == 0:
        print("Seed data already present; skipping (use --force to reseed).")
    else:
        print(
            f"Seeded {created_programs} programs and {created_geo} geo aggregates -> {args.db_url}"
        )


if __name__ == "__main__":
    main()
