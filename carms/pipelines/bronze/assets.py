from pathlib import Path

import pandas as pd
from dagster import asset, get_dagster_logger
from sqlmodel import Session, delete

from carms.core.database import engine
from carms.core.utils import canonical_id
from carms.models.bronze import BronzeDescription, BronzeDiscipline, BronzeProgram

logger = get_dagster_logger()

SOURCE_FILES = {
    "programs": "1503_program_master.xlsx",
    "disciplines": "1503_discipline.xlsx",
    "descriptions": "1503_program_descriptions_x_section.csv",
}


def find_source_file(filename: str) -> Path:
    """
    Search upward from this file until the source file is found.
    Looks both at the parent and a sibling `data/` directory (and a nested
    folder that matches the filename stem) to avoid hardcoding absolute paths.
    """
    name_stem = Path(filename).stem
    for parent in Path(__file__).resolve().parents:
        direct = parent / filename
        data_root = parent / "data" / filename
        data_stem = parent / "data" / name_stem / filename
        for candidate in (direct, data_root, data_stem):
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"Source file not found: {filename}")


def _clean_record(record: dict) -> dict:
    return {k: (None if pd.isna(v) else v) for k, v in record.items()}


@asset(group_name="bronze")
def bronze_programs() -> int:
    path = find_source_file(SOURCE_FILES["programs"])
    df = pd.read_excel(path)
    df = df.rename(columns=lambda c: c.strip())
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    programs: list[BronzeProgram] = [
        BronzeProgram(**_clean_record(r)) for r in df.to_dict(orient="records")
    ]

    with Session(engine) as session:
        session.exec(delete(BronzeProgram))
        session.add_all(programs)
        session.commit()

    logger.info("Loaded %s bronze programs", len(programs))
    return len(programs)


@asset(group_name="bronze")
def bronze_disciplines() -> int:
    path = find_source_file(SOURCE_FILES["disciplines"])
    df = pd.read_excel(path)
    df = df.rename(columns=lambda c: c.strip())

    disciplines: list[BronzeDiscipline] = [
        BronzeDiscipline(**_clean_record(r)) for r in df.to_dict(orient="records")
    ]

    with Session(engine) as session:
        session.exec(delete(BronzeDiscipline))
        session.add_all(disciplines)
        session.commit()

    logger.info("Loaded %s bronze disciplines", len(disciplines))
    return len(disciplines)


@asset(group_name="bronze")
def bronze_descriptions() -> int:
    path = find_source_file(SOURCE_FILES["descriptions"])
    df = pd.read_csv(path)
    df = df.rename(columns=lambda c: c.strip())
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    descriptions: list[BronzeDescription] = []
    for record in df.to_dict(orient="records"):
        cleaned = _clean_record(record)
        match_iteration_id = cleaned.get("match_iteration_id")
        program_description_id = cleaned.get("program_description_id")

        if match_iteration_id is not None and program_description_id is not None:
            cleaned["document_id"] = canonical_id(
                int(match_iteration_id), int(program_description_id)
            )

        descriptions.append(BronzeDescription(**cleaned))

    with Session(engine) as session:
        session.exec(delete(BronzeDescription))
        session.add_all(descriptions)
        session.commit()

    logger.info("Loaded %s bronze descriptions", len(descriptions))
    return len(descriptions)
