from sqlmodel import Field, SQLModel


class BronzeProgram(SQLModel, table=True):
    __tablename__ = "bronze_program"
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


class BronzeDiscipline(SQLModel, table=True):
    __tablename__ = "bronze_discipline"
    discipline_id: int = Field(primary_key=True)
    discipline: str


class BronzeDescription(SQLModel, table=True):
    __tablename__ = "bronze_description"
    document_id: str = Field(primary_key=True)
    source: str | None = None
    n_program_description_sections: int | None = None
    program_name: str
    match_iteration_name: str | None = None
    program_contracts: str | None = None
    general_instructions: str | None = None
    supporting_documentation_information: str | None = None
    review_process: str | None = None
    interviews: str | None = None
    selection_criteria: str | None = None
    program_highlights: str | None = None
    program_curriculum: str | None = None
    training_sites: str | None = None
    additional_information: str | None = None
    return_of_service: str | None = None
    faq: str | None = None
    summary_of_changes: str | None = None
    match_iteration_id: int | None = None
    program_description_id: int
