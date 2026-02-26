from __future__ import annotations

import math
import os
from collections.abc import Sequence
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlmodel import Session, select

from carms.api.schemas import SemanticHit, SemanticQueryRequest, SemanticQueryResponse
from carms.core.database import get_session
from carms.models.gold import GoldProgramEmbedding

router = APIRouter(prefix="/semantic", tags=["semantic"])


@lru_cache(maxsize=1)
def _get_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="sentence-transformers not installed") from exc
    return SentenceTransformer("all-MiniLM-L6-v2")


def _maybe_generate_answer(question: str, hits: list[SemanticHit]) -> str | None:
    """
    Optional LangChain-backed summarization when OPENAI_API_KEY is present.
    Falls back to None when no key or library issues occur.
    """
    if not hits:
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from langchain.chains.combine_documents import create_stuff_documents_chain
        from langchain.prompts import ChatPromptTemplate
        from langchain.schema import Document
        from langchain_openai import ChatOpenAI
    except Exception:
        return None

    llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_template(
        "Use the program snippets to answer the question. "
        "Keep answers grounded and cite program_stream_id when useful.\n\n"
        "Question: {question}\n\nSnippets:\n{context}"
    )
    chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
    docs = [
        Document(
            page_content=hit.description_snippet or "",
            metadata={
                "program_stream_id": hit.program_stream_id,
                "discipline_name": hit.discipline_name,
                "province": hit.province,
            },
        )
        for hit in hits
    ]

    try:
        return chain.invoke({"input_documents": docs, "question": question})
    except Exception:
        return None


@router.post("/query", response_model=SemanticQueryResponse)
def semantic_query(
    payload: SemanticQueryRequest,
    session: Annotated[Session, Depends(get_session)],
) -> SemanticQueryResponse:
    if payload.top_k < 1 or payload.top_k > 20:
        raise HTTPException(status_code=422, detail="top_k must be between 1 and 20")

    model = _get_model()
    query_embedding = model.encode(payload.query, normalize_embeddings=True).tolist()

    hits: list[SemanticHit] = []
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        stmt = text(
            """
            SELECT
                program_stream_id,
                program_name,
                program_stream_name,
                discipline_name,
                province,
                description_text,
                1 - (embedding <=> (:query_embedding)::vector) AS similarity
            FROM gold_program_embedding
            WHERE (:province IS NULL OR province = :province)
              AND (:discipline IS NULL OR discipline_name ILIKE '%' || :discipline || '%')
            ORDER BY embedding <=> (:query_embedding)::vector
            LIMIT :top_k
            """
        )

        rows = session.exec(
            stmt,
            {
                "query_embedding": query_embedding,
                "province": payload.province,
                "discipline": payload.discipline,
                "top_k": payload.top_k,
            },
        ).mappings()

        for row in rows:
            text_val = row.get("description_text")
            snippet = text_val[:320] + "..." if text_val and len(text_val) > 320 else text_val
            hits.append(
                SemanticHit(
                    program_stream_id=row["program_stream_id"],
                    program_name=row["program_name"],
                    program_stream_name=row["program_stream_name"],
                    discipline_name=row["discipline_name"],
                    province=row["province"],
                    similarity=float(row["similarity"]),
                    description_snippet=snippet,
                )
            )
    else:

        def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b, strict=False))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(y * y for y in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        query = select(GoldProgramEmbedding)
        if payload.province:
            query = query.where(GoldProgramEmbedding.province == payload.province)
        if payload.discipline:
            query = query.where(
                GoldProgramEmbedding.discipline_name.ilike(f"%{payload.discipline}%")
            )

        rows = session.exec(query).all()
        scored: list[tuple[float, GoldProgramEmbedding]] = []
        for row in rows:
            score = _cosine_similarity(query_embedding, row.embedding or [])
            scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)

        for score, row in scored[: payload.top_k]:
            text_val = row.description_text
            snippet = text_val[:320] + "..." if text_val and len(text_val) > 320 else text_val
            hits.append(
                SemanticHit(
                    program_stream_id=row.program_stream_id,
                    program_name=row.program_name,
                    program_stream_name=row.program_stream_name,
                    discipline_name=row.discipline_name,
                    province=row.province,
                    similarity=float(score),
                    description_snippet=snippet,
                )
            )

    answer = _maybe_generate_answer(payload.query, hits)
    return SemanticQueryResponse(hits=hits, answer=answer, top_k=payload.top_k)
