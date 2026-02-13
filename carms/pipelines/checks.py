from dagster import AssetCheckResult, AssetCheckSeverity, asset_check
from sqlmodel import Session, select

from carms.core.database import engine
from carms.models.gold import GoldGeoSummary, GoldProgramEmbedding, GoldProgramProfile
from carms.models.silver import SilverDescriptionSection, SilverProgram


@asset_check(asset="silver_programs", name="silver_programs_not_empty")
def silver_programs_not_empty() -> AssetCheckResult:
    with Session(engine) as session:
        count = len(session.exec(select(SilverProgram.program_stream_id)).all())
    return AssetCheckResult(
        passed=count > 0,
        severity=AssetCheckSeverity.ERROR,
        metadata={"row_count": count},
    )


@asset_check(asset="silver_programs", name="silver_programs_valid_province")
def silver_programs_valid_province() -> AssetCheckResult:
    allowed = {"NL", "PE", "NS", "NB", "QC", "ON", "MB", "SK", "AB", "BC", "YT", "NT", "NU", "UNKNOWN"}
    with Session(engine) as session:
        rows = session.exec(select(SilverProgram.province)).all()
    invalid = [p for p in rows if p not in allowed]
    return AssetCheckResult(
        passed=len(invalid) == 0,
        severity=AssetCheckSeverity.ERROR,
        metadata={"invalid_count": len(invalid)},
    )


@asset_check(asset="silver_description_sections", name="silver_description_sections_not_empty")
def silver_description_sections_not_empty() -> AssetCheckResult:
    with Session(engine) as session:
        count = len(session.exec(select(SilverDescriptionSection.id)).all())
    return AssetCheckResult(
        passed=count > 0,
        severity=AssetCheckSeverity.WARN,
        metadata={"row_count": count},
    )


@asset_check(asset="gold_program_profiles", name="gold_program_profiles_unique_program_stream_id")
def gold_program_profiles_unique_program_stream_id() -> AssetCheckResult:
    with Session(engine) as session:
        ids = session.exec(select(GoldProgramProfile.program_stream_id)).all()
    unique_count = len(set(ids))
    total = len(ids)
    return AssetCheckResult(
        passed=unique_count == total,
        severity=AssetCheckSeverity.ERROR,
        metadata={"row_count": total, "unique_program_stream_ids": unique_count},
    )


@asset_check(asset="gold_geo_summary", name="gold_geo_summary_non_negative_program_count")
def gold_geo_summary_non_negative_program_count() -> AssetCheckResult:
    with Session(engine) as session:
        values = session.exec(select(GoldGeoSummary.program_count)).all()
    negatives = sum(1 for count in values if count < 0)
    return AssetCheckResult(
        passed=negatives == 0,
        severity=AssetCheckSeverity.ERROR,
        metadata={"negative_count": negatives, "checked_rows": len(values)},
    )


@asset_check(asset="gold_program_embeddings", name="gold_program_embeddings_not_empty")
def gold_program_embeddings_not_empty() -> AssetCheckResult:
    with Session(engine) as session:
        count = len(session.exec(select(GoldProgramEmbedding.program_stream_id)).all())
    return AssetCheckResult(
        passed=count > 0,
        severity=AssetCheckSeverity.WARN,
        metadata={"row_count": count},
    )
