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


class RenderJobModel(Base):
    __tablename__ = "render_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    condition_hash: Mapped[str] = mapped_column(String(64), index=True)
    render_hash: Mapped[str] = mapped_column(String(64), index=True)
    external_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    vendor: Mapped[str] = mapped_column(String(128), default="mock", index=True)
    model: Mapped[str] = mapped_column(String(128), default="mock-video-v1")
    status: Mapped[str] = mapped_column(String(64), index=True)
    compiled_prompt: Mapped[str] = mapped_column(Text)
    source_map_json: Mapped[str] = mapped_column(Text)
    visual_anchor_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
    )


class ManualJobModel(Base):
    __tablename__ = "manual_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(64), index=True)
    condition_hash: Mapped[str] = mapped_column(String(64), index=True)
    compiled_prompt: Mapped[str] = mapped_column(Text)
    source_map_json: Mapped[str] = mapped_column(Text)
    visual_anchor_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_instructions: Mapped[str] = mapped_column(Text)
    result_video_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
    )


class ManualAuditModel(TimestampMixin, Base):
    __tablename__ = "manual_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    manual_job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("manual_jobs.id"),
        nullable=True,
        index=True,
    )
    render_job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("render_jobs.id"),
        nullable=True,
        index=True,
    )
    condition_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    bad_prompt_fragment_ref: Mapped[str] = mapped_column(String(128))
    raw_failure_type: Mapped[str] = mapped_column(String(128))
    failure_signature: Mapped[str] = mapped_column(String(128), index=True)
    failure_category: Mapped[str] = mapped_column(String(128), index=True)
    recovery_policy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    suggested_positive_lock: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rfs_scores_json: Mapped[str] = mapped_column(Text)
