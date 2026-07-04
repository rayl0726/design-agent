import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime

from app.models.database import Base


class CrawledUrl(Base):
    __tablename__ = "crawled_urls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(String(2000), nullable=False, unique=True, index=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)
