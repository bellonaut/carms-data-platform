import re
import unicodedata

from dagster import AssetIn, asset
from sqlmodel import Session, delete, select

from carms.core.database import engine
from carms.models.bronze import BronzeDescription, BronzeDiscipline, BronzeProgram
from carms.models.silver import SilverDescriptionSection, SilverDiscipline, SilverProgram

PROVINCE_CODES = {
    "NL",
    "PE",
    "NS",
    "NB",
    "QC",
    "ON",
    "MB",
    "SK",
    "AB",
    "BC",
    "YT",
    "NT",
    "NU",
}

SCHOOL_PROVINCE_MAP: dict[str, str] = {
    "dalhousie university": "NS",
    "mcgill university": "QC",
    "mcmaster university": "ON",
    "memorial university of newfoundland": "NL",
    "nosm university": "ON",
    "queen's university": "ON",
    "queens university": "ON",
    "toronto metropolitan university": "ON",
    "university of alberta": "AB",
    "university of british columbia": "BC",
    "university of calgary": "AB",
    "university of manitoba": "MB",
    "university of ottawa": "ON",
    "university of saskatchewan": "SK",
    "university of toronto": "ON",
    "universite laval": "QC",
    "universite de montreal": "QC",
    "universite de sherbrooke": "QC",
    "western university": "ON",
}


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    normalized_quotes = ascii_only.replace("’", "'").replace("`", "'")
    return " ".join(normalized_quotes.lower().split())


def parse_province(program_site: str | None) -> str | None:
    if not program_site:
        return None
    tokens = [t.strip() for t in program_site.replace(";", ",").split(",") if t.strip()]
    for token in reversed(tokens):
        candidate = token.upper()
        if len(candidate) in (2, 3) and candidate in PROVINCE_CODES:
            return candidate
    return None


def derive_province(program_site: str | None, school_name: str | None) -> str:
    province_from_site = parse_province(program_site)
    if province_from_site:
        return province_from_site

    school_key = _normalize_text(school_name)
    if school_key in SCHOOL_PROVINCE_MAP:
        return SCHOOL_PROVINCE_MAP[school_key]

    return "UNKNOWN"


def is_valid_text(value: str | None) -> bool:
    return bool(value and str(value).strip())


def parse_quota(match_iteration_name: str | None) -> int | None:
    if not match_iteration_name:
        return None
    match = re.search(
        r"(?i)Approximate Quota:\s*(\d+(?:\s*-\s*\d+)?|Variable)",
        str(match_iteration_name),
    )
    if not match:
        return None

    value = match.group(1).strip()
    if value.lower() == "variable":
        return None
    if "-" in value:
        value = value.split("-", 1)[0].strip()
    return int(value)


@asset(group_name="silver", ins={"bronze_programs": AssetIn("bronze_programs")})
def silver_programs(bronze_programs) -> int:  # type: ignore[unused-argument]
    with Session(engine) as session:
        programs = session.exec(select(BronzeProgram)).all()
        session.exec(delete(SilverProgram))

        silver_rows: list[SilverProgram] = []
        for row in programs:
            province = derive_province(
                row.program_site, row.school_name
            )  # prefer site, then fall back to school map
            # province is guaranteed non-null ("UNKNOWN" fallback) by derive_province()
            is_valid = all([row.program_stream_id, row.program_name, row.discipline_id])
            silver_rows.append(
                SilverProgram(
                    program_stream_id=row.program_stream_id,
                    discipline_id=row.discipline_id,
                    discipline_name=row.discipline_name,
                    school_id=row.school_id,
                    school_name=row.school_name,
                    program_stream_name=row.program_stream_name,
                    program_site=row.program_site,
                    program_stream=row.program_stream,
                    program_name=row.program_name,
                    program_url=row.program_url,
                    quota=parse_quota(getattr(row, "match_iteration_name", None)),
                    province=province,
                    is_valid=is_valid,
                )
            )

        session.add_all(silver_rows)
        session.commit()
        return len(silver_rows)


@asset(group_name="silver", ins={"bronze_disciplines": AssetIn("bronze_disciplines")})
def silver_disciplines(bronze_disciplines) -> int:  # type: ignore[unused-argument]
    with Session(engine) as session:
        disciplines = session.exec(select(BronzeDiscipline)).all()
        session.exec(delete(SilverDiscipline))

        silver_rows: list[SilverDiscipline] = [
            SilverDiscipline(
                discipline_id=row.discipline_id,
                discipline=row.discipline,
                province=None,
                is_valid=is_valid_text(row.discipline),
            )
            for row in disciplines
        ]

        session.add_all(silver_rows)
        session.commit()
        return len(silver_rows)


@asset(group_name="silver", ins={"bronze_descriptions": AssetIn("bronze_descriptions")})
def silver_description_sections(bronze_descriptions) -> int:  # type: ignore[unused-argument]
    section_columns = [
        "program_contracts",
        "general_instructions",
        "supporting_documentation_information",
        "review_process",
        "interviews",
        "selection_criteria",
        "program_highlights",
        "program_curriculum",
        "training_sites",
        "additional_information",
        "return_of_service",
        "faq",
        "summary_of_changes",
    ]

    with Session(engine) as session:
        descriptions = session.exec(select(BronzeDescription)).all()
        session.exec(delete(SilverDescriptionSection))

        silver_rows: list[SilverDescriptionSection] = []
        for desc in descriptions:
            for col in section_columns:
                text = getattr(desc, col)
                if not is_valid_text(text):
                    continue
                silver_rows.append(
                    SilverDescriptionSection(
                        program_description_id=desc.program_description_id,
                        program_name=desc.program_name,
                        section_name=col,
                        section_text=str(text),
                        is_valid=True,
                    )
                )

        session.add_all(silver_rows)
        session.commit()
        return len(silver_rows)
