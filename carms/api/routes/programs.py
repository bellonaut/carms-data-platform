from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from carms.api.schemas import ProgramDetail, ProgramListItem, ProgramListResponse
from carms.core.database import get_session
from carms.models.gold import GoldProgramProfile

router = APIRouter(prefix="/programs", tags=["programs"])

PROVINCE_PATTERN = "^(AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT|UNKNOWN)$"


def make_preview(text: str | None, preview_chars: int) -> str | None:
    if not text or preview_chars <= 0:
        return None
    if len(text) <= preview_chars:
        return text
    return text[:preview_chars].rstrip() + "..."


# ---------- Routes ----------


@router.get("/", response_model=ProgramListResponse)
def list_programs(
    session: Annotated[Session, Depends(get_session)],
    discipline: str | None = Query(
        default=None, description="Filter by discipline name (substring match)"
    ),
    province: str | None = Query(
        default=None,
        description="Filter by province code (exact match)",
        pattern=PROVINCE_PATTERN,
    ),
    school: str | None = Query(default=None, description="Filter by school name (substring match)"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of rows to return"),
    offset: int = Query(default=0, ge=0, description="Row offset for pagination"),
    include_total: bool = Query(default=False, description="Include full filtered row count"),
    preview_chars: int = Query(
        default=900, ge=0, le=5000, description="Max characters for description_preview"
    ),
) -> ProgramListResponse:
    statement = select(GoldProgramProfile)

    if discipline:
        statement = statement.where(GoldProgramProfile.discipline_name.ilike(f"%{discipline}%"))
    if province:
        statement = statement.where(GoldProgramProfile.province == province)
    if school:
        statement = statement.where(GoldProgramProfile.school_name.ilike(f"%{school}%"))

    total: int | None = None
    if include_total:
        count_statement = select(func.count()).select_from(statement.subquery())
        total = session.exec(count_statement).one()

    rows = session.exec(statement.offset(offset).limit(limit)).all()

    items: list[ProgramListItem] = [
        ProgramListItem(
            program_stream_id=r.program_stream_id,
            program_stream_name=r.program_stream_name,
            discipline_name=r.discipline_name,
            school_name=r.school_name,
            program_url=r.program_url,
            is_valid=r.is_valid,
            program_stream=r.program_stream,
            program_name=r.program_name,
            province=r.province,
            program_site=r.program_site,
            description_preview=make_preview(r.description_text, preview_chars),
        )
        for r in rows
    ]

    return ProgramListResponse(items=items, limit=limit, offset=offset, total=total)


@router.get("/{program_stream_id}", response_model=ProgramDetail)
def get_program(
    program_stream_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> ProgramDetail:
    row = session.exec(
        select(GoldProgramProfile).where(GoldProgramProfile.program_stream_id == program_stream_id)
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="Program not found")

    return ProgramDetail(
        program_stream_id=row.program_stream_id,
        program_stream_name=row.program_stream_name,
        discipline_name=row.discipline_name,
        school_name=row.school_name,
        program_url=row.program_url,
        is_valid=row.is_valid,
        program_stream=row.program_stream,
        program_name=row.program_name,
        province=row.province,
        program_site=row.program_site,
        description_preview=None,  # not needed on detail
        description_text=row.description_text,
    )
