from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from db import Base
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

class Notebook(Base):
    __tablename__ = "notebooks"
    __table_args__ = {'schema': 'stud_hub_schema'}  # Add this line
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # add cascade + passive_deletes
    sources = relationship(
        "Source",
        back_populates="notebook",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class Source(Base):
    __tablename__ = "sources"
    __table_args__ = {'schema': 'stud_hub_schema'}  # Add this line
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    notebook_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.notebooks.id", ondelete="CASCADE"), nullable=False)  # Update ForeignKey
    type = Column(String, nullable=False)  # 'file', 'website', 'youtube'
    filename = Column(String, nullable=True)
    file_url = Column(String, nullable=True)
    website_url = Column(String, nullable=True)
    youtube_url = Column(String, nullable=True)
    extracted_text = Column(Text, nullable=True)
    source_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notebook = relationship("Notebook", back_populates="sources")
    embeddings = relationship("Embedding", back_populates="source")

class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = {'schema': 'stud_hub_schema'}  # Add this line
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    source_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.sources.id"), nullable=False)  # Update ForeignKey
    chunk = Column(Text, nullable=False)
    vector = Column(Vector(768), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    source = relationship("Source", back_populates="embeddings")
