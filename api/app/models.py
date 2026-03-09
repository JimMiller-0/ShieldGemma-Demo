from sqlalchemy import Column, String, Text, Boolean, DateTime, Float, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from api.app.database import Base


class SafetyPolicy(Base):
    __tablename__ = "safety_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    policy_content = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    predefined_policy_config = Column(
        JSONB,
        nullable=False,
        server_default=text(
            """'{"dangerous_content": true, "harassment": true, "hate_speech": true, "sexually_explicit": true}'::jsonb"""
        ),
    )
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    def __repr__(self):
        return f"<SafetyPolicy(id={self.id}, name='{self.name}', is_default={self.is_default})>"


class AnalysisLog(Base):
    __tablename__ = "analysis_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    text_input = Column(Text, nullable=False)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("safety_policies.id", ondelete="SET NULL"), nullable=True)
    policy_name = Column(String(255), nullable=True)
    is_safe = Column(Boolean, nullable=False)
    safety_categories = Column(JSONB, nullable=False)
    model_used = Column(String(255), nullable=False)
    max_score = Column(Float, nullable=False)
    inference_time_seconds = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    def __repr__(self):
        return f"<AnalysisLog(id={self.id}, is_safe={self.is_safe}, model={self.model_used})>"
