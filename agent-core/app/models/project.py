import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.models.database import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="draft")  # draft / parsing / l1 / l2 / l3 / completed / failed
    current_level = Column(String(10), nullable=True)  # L1 / L2 / L3
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    raw_inputs_json = Column(Text, nullable=True)
    l1_output_json = Column(Text, nullable=True)
    l2_output_json = Column(Text, nullable=True)
    l3_output_json = Column(Text, nullable=True)


class DesignCase(Base):
    __tablename__ = "design_cases"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    title = Column(String(500), nullable=False)
    source_url = Column(String(1000), nullable=True)
    space_type = Column(String(100), nullable=True)  # 中庭 / 走廊 / 快闪店 / 展览
    budget_level = Column(String(20), nullable=True)  # low / medium / high
    theme = Column(String(200), nullable=True)
    style = Column(String(200), nullable=True)
    summary = Column(Text, nullable=True)
    images_json = Column(Text, nullable=True)  # JSON list of image paths
    created_at = Column(DateTime, default=datetime.utcnow)


class MaterialPrice(Base):
    __tablename__ = "material_prices"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    spec = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)
    price_low = Column(Float, nullable=True)
    price_high = Column(Float, nullable=True)
    supplier_hint = Column(String(500), nullable=True)
    source = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MaterialSpec(Base):
    __tablename__ = "material_specs"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    name = Column(String(255), nullable=False)
    material = Column(String(200), nullable=True)
    size = Column(String(200), nullable=True)
    process = Column(String(200), nullable=True)
    unit_price = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    quantity = Column(Integer, nullable=True)
    total_price = Column(Float, nullable=True)
    project_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    project_id = Column(String(36), nullable=False, index=True)
    doc_type = Column(String(50), nullable=False)  # html / ppt / pdf
    file_path = Column(String(1000), nullable=False)
    level = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
