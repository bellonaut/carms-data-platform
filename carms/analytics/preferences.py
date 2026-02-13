from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from sqlmodel import Session, select

from carms.models.gold import GoldProgramEmbedding
from carms.models.silver import SilverProgram

FEATURE_NAMES = ["discipline_freq", "province_mix", "stream_is_cmg", "stream_is_img", "embedding_similarity"]
MODEL_VERSION = "v1"
REG_L2 = 0.1


def get_artifact_path() -> Path:
    """Prefer env override to keep tests/docker predictable."""
    override = os.getenv("PREFERENCE_ARTIFACT_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "data" / "preferences_model.json"


@dataclass
class PreferenceFeatureRow:
    program_stream_id: int
    program_name: str
    program_stream_name: str
    program_stream: str
    discipline_name: str
    province: str
    features: Dict[str, float]
    label: float  # proxy target: normalized quota


@dataclass
class PreferenceModelArtifact:
    version: str
    feature_names: List[str]
    weights: List[float]
    intercept: float
    feature_importances: Dict[str, float]


@dataclass
class PreferenceScore:
    program_stream_id: int
    program_name: str
    program_stream_name: str
    program_stream: str
    discipline_name: str
    province: str
    score: float
    feature_values: Dict[str, float]
    label_proxy: float


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _load_embeddings(session: Session) -> Tuple[Dict[int, List[float]], Dict[str, List[float]]]:
    """Return program embeddings and per-discipline centroids when available."""
    rows = session.exec(select(GoldProgramEmbedding)).all()
    by_program: Dict[int, List[float]] = {}
    by_discipline: Dict[str, List[List[float]]] = defaultdict(list)

    for row in rows:
        if row.embedding is None:
            continue
        emb = list(row.embedding)
        by_program[row.program_stream_id] = emb
        by_discipline[row.discipline_name].append(emb)

    centroids: Dict[str, List[float]] = {}
    for disc, vectors in by_discipline.items():
        if not vectors:
            continue
        arr = np.array(vectors, dtype=float)
        centroid = arr.mean(axis=0).tolist()
        centroids[disc] = [float(v) for v in centroid]

    return by_program, centroids


def build_feature_rows(session: Session) -> List[PreferenceFeatureRow]:
    programs = session.exec(select(SilverProgram).where(SilverProgram.is_valid == True)).all()  # noqa: E712
    if not programs:
        return []

    total_programs = len(programs)
    discipline_counts = Counter(p.discipline_name for p in programs)
    province_disc_counts = Counter(((p.province or "UNKNOWN").upper(), p.discipline_name) for p in programs)
    max_quota = max((p.quota for p in programs if p.quota is not None), default=None)
    max_quota = float(max_quota) if max_quota is not None else 1.0

    program_embeddings, discipline_centroids = _load_embeddings(session)

    rows: List[PreferenceFeatureRow] = []
    for program in programs:
        province = (program.province or "UNKNOWN").upper()
        discipline = program.discipline_name
        stream = (program.program_stream or "").upper()

        features = {
            "discipline_freq": discipline_counts[discipline] / float(total_programs),
            "province_mix": province_disc_counts[(province, discipline)] / float(discipline_counts[discipline]),
            "stream_is_cmg": 1.0 if stream == "CMG" else 0.0,
            "stream_is_img": 1.0 if stream == "IMG" else 0.0,
            "embedding_similarity": 0.0,
        }

        program_emb = program_embeddings.get(program.program_stream_id)
        centroid = discipline_centroids.get(discipline)
        if program_emb and centroid:
            features["embedding_similarity"] = _cosine_similarity(program_emb, centroid)

        quota_val = float(program.quota) if program.quota is not None else 1.0
        label = quota_val / max_quota if max_quota else 0.0

        rows.append(
            PreferenceFeatureRow(
                program_stream_id=program.program_stream_id,
                program_name=program.program_name,
                program_stream_name=program.program_stream_name,
                program_stream=program.program_stream,
                discipline_name=discipline,
                province=province,
                features=features,
                label=label,
            )
        )

    return rows


def _ridge_regression(X: np.ndarray, y: np.ndarray, reg_lambda: float) -> Tuple[float, List[float]]:
    """Closed-form ridge regression to keep the model simple and interpretable."""
    X_design = np.hstack([np.ones((X.shape[0], 1)), X])
    eye = np.eye(X_design.shape[1])
    xtx = X_design.T @ X_design + reg_lambda * eye
    try:
        beta = np.linalg.solve(xtx, X_design.T @ y)
    except np.linalg.LinAlgError:
        beta = np.linalg.pinv(xtx) @ X_design.T @ y
    intercept = float(beta[0])
    weights = [float(w) for w in beta[1:]]
    return intercept, weights


def train_preference_model(session: Session, persist: bool = True) -> PreferenceModelArtifact:
    rows = build_feature_rows(session)
    if not rows:
        raise ValueError("No programs available to train preference model.")

    X = np.array([[r.features[name] for name in FEATURE_NAMES] for r in rows], dtype=float)
    y = np.array([r.label for r in rows], dtype=float)
    intercept, weights = _ridge_regression(X, y, reg_lambda=REG_L2)

    abs_weights = [abs(w) for w in weights]
    total = sum(abs_weights) or 1.0
    feature_importances = {name: abs(w) / total for name, w in zip(FEATURE_NAMES, weights)}

    artifact = PreferenceModelArtifact(
        version=MODEL_VERSION,
        feature_names=list(FEATURE_NAMES),
        weights=weights,
        intercept=intercept,
        feature_importances=feature_importances,
    )

    if persist:
        path = get_artifact_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(artifact)))

    return artifact


def load_artifact(path: Optional[Path] = None) -> Optional[PreferenceModelArtifact]:
    target = path or get_artifact_path()
    if not target.exists():
        return None
    data = json.loads(target.read_text())
    try:
        return PreferenceModelArtifact(
            version=data.get("version", MODEL_VERSION),
            feature_names=data["feature_names"],
            weights=data["weights"],
            intercept=data["intercept"],
            feature_importances=data["feature_importances"],
        )
    except KeyError:
        return None


def ensure_artifact(session: Session) -> PreferenceModelArtifact:
    artifact = load_artifact()
    if artifact:
        return artifact
    return train_preference_model(session, persist=True)


def _predict_score(features: Dict[str, float], artifact: PreferenceModelArtifact) -> float:
    raw = artifact.intercept
    for name, weight in zip(artifact.feature_names, artifact.weights):
        raw += weight * features.get(name, 0.0)
    return 1.0 / (1.0 + math.exp(-raw))


def score_slice(
    session: Session,
    artifact: PreferenceModelArtifact,
    province: Optional[str] = None,
    discipline: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[PreferenceScore]:
    rows = build_feature_rows(session)
    filtered: Iterable[PreferenceFeatureRow] = rows
    if province:
        province_upper = province.upper()
        filtered = (r for r in filtered if r.province == province_upper)
    if discipline:
        filtered = (r for r in filtered if discipline.lower() in r.discipline_name.lower())

    scored: List[PreferenceScore] = []
    for row in filtered:
        score = _predict_score(row.features, artifact)
        scored.append(
            PreferenceScore(
                program_stream_id=row.program_stream_id,
                program_name=row.program_name,
                program_stream_name=row.program_stream_name,
                program_stream=row.program_stream,
                discipline_name=row.discipline_name,
                province=row.province,
                score=score,
                feature_values=row.features,
                label_proxy=row.label,
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    if limit is not None:
        scored = scored[:limit]
    return scored
