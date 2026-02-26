from sqlmodel import Field, SQLModel


class SilverProgram(SQLModel, table=True):
    __tablename__ = "silver_program"
    program_stream_id: int = Field(primary_key=True)
    discipline_id: int
    discipline_name: str
    school_id: int
    school_name: str
    program_stream_name: str
    program_site: str
    program_stream: str
    program_name: str
    program_url: str | None = None
    quota: int | None = None
    province: str = "UNKNOWN"
    is_valid: bool = True


class SilverDiscipline(SQLModel, table=True):
    __tablename__ = "silver_discipline"
    discipline_id: int = Field(primary_key=True)
    discipline: str
    province: str | None = None
    is_valid: bool = True


class SilverDescriptionSection(SQLModel, table=True):
    __tablename__ = "silver_description_section"
    id: int | None = Field(default=None, primary_key=True)
    program_description_id: int
    program_name: str | None = None
    section_name: str
    section_text: str | None = None
    is_valid: bool = True
