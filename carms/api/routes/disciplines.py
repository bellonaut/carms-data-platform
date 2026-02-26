from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from carms.core.database import get_session
from carms.models.silver import SilverDiscipline

router = APIRouter(prefix="/disciplines", tags=["disciplines"])


@router.get("/", response_model=list[SilverDiscipline])
def list_disciplines(
    session: Annotated[Session, Depends(get_session)],
) -> list[SilverDiscipline]:
    statement = select(SilverDiscipline).where(SilverDiscipline.is_valid == True)  # noqa: E712
    return session.exec(statement).all()
