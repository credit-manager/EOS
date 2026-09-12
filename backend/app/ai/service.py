"""AI-powered features for the EOS metadata platform.

Provides smart search (TF-IDF scoring), auto-tagging, record similarity,
smart deduplication, and anomaly detection — all implemented with pure
Python (no external ML dependencies).
"""
import math
import re
from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..metadata.models import MetadataEntity
from ..records.models import Record

# ---------------------------------------------------------------------------
# Text preprocessing
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in to for on with "
    "at by from as into through during before after above below between "
    "out off over under again further then once here there when where "
    "why how all each every both few more most other some such no nor "
    "not only own same so than too very s t just don now d ll m o re "
    "ve y ain aren couldn didn doesn hadn hasn haven isn ma mightn mustn "
    "needn shan shouldn wasn weren won wouldn".split()
)


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip non-alphanumeric, remove stop words."""
    tokens = re.findall(r"[a-z0-9\u0600-\u06FF]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _extract_text(record: Record, metadata: MetadataEntity) -> str:
    """Extract all searchable text from a record."""
    parts: list[str] = []
    for field in metadata.definition.get("fields", []):
        if field.get("type") in {"text", "enum", "email", "url"}:
            value = record.data.get(field["code"])
            if isinstance(value, str) and value:
                parts.append(value)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# TF-IDF scoring
# ---------------------------------------------------------------------------

def _compute_idf(documents: list[list[str]]) -> dict[str, float]:
    """Compute inverse document frequency for all tokens."""
    n_docs = len(documents)
    if n_docs == 0:
        return {}
    doc_freq: Counter[str] = Counter()
    for doc in documents:
        unique_tokens = set(doc)
        for token in unique_tokens:
            doc_freq[token] += 1
    return {token: math.log((n_docs + 1) / (freq + 1)) + 1 for token, freq in doc_freq.items()}


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """Compute TF-IDF vector for a token list."""
    tf = Counter(tokens)
    total = len(tokens) or 1
    return {token: (count / total) * idf.get(token, 1.0) for token, count in tf.items()}


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""
    if not vec_a or not vec_b:
        return 0.0
    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in common)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Smart Search
# ---------------------------------------------------------------------------

def smart_search(
    db: Session,
    *,
    tenant_id: UUID,
    entity_code: str,
    query: str,
    limit: int = 25,
) -> list[dict]:
    """Search records with TF-IDF scoring and fuzzy matching."""
    metadata = db.scalar(
        select(MetadataEntity).where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        ).order_by(MetadataEntity.version.desc())
    )
    if metadata is None:
        return []

    records = db.scalars(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    ).all()

    if not records:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    doc_token_lists = [_tokenize(_extract_text(rec, metadata)) for rec in records]
    idf = _compute_idf(doc_token_lists + [query_tokens])
    query_vec = _tfidf_vector(query_tokens, idf)

    scored: list[dict] = []
    for rec, doc_tokens in zip(records, doc_token_lists):
        doc_vec = _tfidf_vector(doc_tokens, idf)
        score = _cosine_similarity(query_vec, doc_vec)

        # Fuzzy bonus: partial token match
        for q_token in query_tokens:
            for d_token in doc_tokens:
                if q_token in d_token or d_token in q_token:
                    if q_token != d_token:
                        score += 0.1

        if score > 0:
            scored.append({
                "id": str(rec.id),
                "data": rec.data,
                "score": round(score, 4),
                "version": rec.version,
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# Auto-tagging
# ---------------------------------------------------------------------------

def auto_tag(
    db: Session,
    *,
    tenant_id: UUID,
    entity_code: str,
    record_id: UUID,
    max_tags: int = 10,
) -> list[str]:
    """Extract keywords from a record's text fields as tags."""
    metadata = db.scalar(
        select(MetadataEntity).where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        ).order_by(MetadataEntity.version.desc())
    )
    if metadata is None:
        return []

    record = db.scalar(
        select(Record).where(
            Record.id == record_id,
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    )
    if record is None:
        return []

    text = _extract_text(record, metadata)
    tokens = _tokenize(text)
    if not tokens:
        return []

    # TF scoring: most frequent tokens in this record
    tf = Counter(tokens)
    total = len(tokens)
    scored_tags = [
        (token, count / total)
        for token, count in tf.most_common(max_tags * 3)
    ]

    # Get all records to compute IDF
    all_records = db.scalars(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    ).all()
    all_docs = [_tokenize(_extract_text(rec, metadata)) for rec in all_records]
    idf = _compute_idf(all_docs)

    # TF-IDF ranking
    final = [
        (token, tf_score * idf.get(token, 1.0))
        for token, tf_score in scored_tags
    ]
    final.sort(key=lambda x: x[1], reverse=True)
    return [token for token, _ in final[:max_tags]]


# ---------------------------------------------------------------------------
# Record Similarity
# ---------------------------------------------------------------------------

def find_similar(
    db: Session,
    *,
    tenant_id: UUID,
    entity_code: str,
    record_id: UUID,
    limit: int = 5,
    min_score: float = 0.1,
) -> list[dict]:
    """Find records similar to a given record using TF-IDF cosine similarity."""
    metadata = db.scalar(
        select(MetadataEntity).where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        ).order_by(MetadataEntity.version.desc())
    )
    if metadata is None:
        return []

    target = db.scalar(
        select(Record).where(
            Record.id == record_id,
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    )
    if target is None:
        return []

    records = db.scalars(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    ).all()

    doc_token_lists = [_tokenize(_extract_text(rec, metadata)) for rec in records]
    idf = _compute_idf(doc_token_lists)
    target_tokens = _tokenize(_extract_text(target, metadata))
    target_vec = _tfidf_vector(target_tokens, idf)

    scored: list[dict] = []
    for rec, doc_tokens in zip(records, doc_token_lists):
        if rec.id == record_id:
            continue
        doc_vec = _tfidf_vector(doc_tokens, idf)
        score = _cosine_similarity(target_vec, doc_vec)
        if score >= min_score:
            scored.append({
                "id": str(rec.id),
                "data": rec.data,
                "similarity": round(score, 4),
                "version": rec.version,
            })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# Smart Deduplication
# ---------------------------------------------------------------------------

def detect_duplicates(
    db: Session,
    *,
    tenant_id: UUID,
    entity_code: str,
    threshold: float = 0.8,
    limit: int = 50,
) -> list[dict]:
    """Detect potential duplicate records using TF-IDF similarity."""
    metadata = db.scalar(
        select(MetadataEntity).where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        ).order_by(MetadataEntity.version.desc())
    )
    if metadata is None:
        return []

    records = db.scalars(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    ).all()

    if len(records) < 2:
        return []

    doc_token_lists = [_tokenize(_extract_text(rec, metadata)) for rec in records]
    idf = _compute_idf(doc_token_lists)
    vectors = [_tfidf_vector(tokens, idf) for tokens in doc_token_lists]

    pairs: list[dict] = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            score = _cosine_similarity(vectors[i], vectors[j])
            if score >= threshold:
                pairs.append({
                    "record_a": str(records[i].id),
                    "record_b": str(records[j].id),
                    "data_a": records[i].data,
                    "data_b": records[j].data,
                    "similarity": round(score, 4),
                })

    pairs.sort(key=lambda x: x["similarity"], reverse=True)
    return pairs[:limit]


# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------

def detect_anomalies(
    db: Session,
    *,
    tenant_id: UUID,
    entity_code: str,
    z_score_threshold: float = 2.0,
) -> list[dict]:
    """Detect anomalous numeric values using Z-score analysis."""
    metadata = db.scalar(
        select(MetadataEntity).where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        ).order_by(MetadataEntity.version.desc())
    )
    if metadata is None:
        return []

    numeric_fields = [
        field["code"]
        for field in metadata.definition.get("fields", [])
        if field.get("type") in {"integer", "decimal"}
    ]
    if not numeric_fields:
        return []

    records = db.scalars(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
        )
    ).all()

    if len(records) < 3:
        return []

    anomalies: list[dict] = []

    for field_code in numeric_fields:
        values: list[float] = []
        for rec in records:
            val = rec.data.get(field_code)
            if val is not None:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    continue

        if len(values) < 3:
            continue

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)
        if std == 0:
            continue

        for rec in records:
            val = rec.data.get(field_code)
            if val is not None:
                try:
                    fval = float(val)
                except (ValueError, TypeError):
                    continue
                z_score = (fval - mean) / std
                if abs(z_score) >= z_score_threshold:
                    anomalies.append({
                        "record_id": str(rec.id),
                        "field": field_code,
                        "value": fval,
                        "mean": round(mean, 4),
                        "std": round(std, 4),
                        "z_score": round(z_score, 4),
                        "direction": "high" if z_score > 0 else "low",
                    })

    anomalies.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return anomalies
