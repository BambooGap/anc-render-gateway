from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GatewayTransactionModel(Base):
    __tablename__ = "gateway_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    state_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    shot_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), default="created", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
    )


class CompileJobModel(TimestampMixin, Base):
    __tablename__ = "compile_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    transaction_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gateway_transactions.id"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    raw_prompt: Mapped[str] = mapped_column(Text)
    compiled_prompt: Mapped[str] = mapped_column(Text)
    condition_hash: Mapped[str] = mapped_column(String(64), index=True)
    ruleset_fingerprint: Mapped[str] = mapped_column(String(128))
    compiler_version: Mapped[str] = mapped_column(String(128))
    state_json: Mapped[str] = mapped_column(Text)
    render_contract_json: Mapped[str] = mapped_column(Text)
    source_map_json: Mapped[str] = mapped_column(Text)


class PromptSourceMapRecordModel(TimestampMixin, Base):
    __tablename__ = "prompt_source_map_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    compile_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("compile_jobs.id"),
        index=True,
    )
    fragment_id: Mapped[str] = mapped_column(String(128), index=True)
    original_text: Mapped[str] = mapped_column(Text)
    rewritten_text: Mapped[str] = mapped_column(Text)
    rules_applied: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FailureRecordModel(TimestampMixin, Base):
    __tablename__ = "failure_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    transaction_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gateway_transactions.id"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    condition_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    failure_signature: Mapped[str] = mapped_column(String(128), index=True)
    failure_category: Mapped[str] = mapped_column(String(128), index=True)
    bad_prompt_fragment_ref: Mapped[str] = mapped_column(String(128))
    bad_prompt_fragment: Mapped[str] = mapped_column(Text)
    recovery_policy: Mapped[str] = mapped_column(String(128))
    suggested_positive_lock: Mapped[str] = mapped_column(Text)
    ruleset_fingerprint: Mapped[str] = mapped_column(String(128))
    audit_json: Mapped[str] = mapped_column(Text)


class PatchRecordModel(TimestampMixin, Base):
    __tablename__ = "patch_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    transaction_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gateway_transactions.id"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    failure_record_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("failure_records.id"),
        nullable=True,
        index=True,
    )
    recovery_policy: Mapped[str] = mapped_column(String(128))
    target_fragment_ref: Mapped[str] = mapped_column(String(128))
    positive_lock: Mapped[str] = mapped_column(Text)
    patch_packet_json: Mapped[str] = mapped_column(Text)
