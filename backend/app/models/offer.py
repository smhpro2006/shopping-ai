from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    url = Column(String, nullable=True)
    availability = Column(String, nullable=True)
    condition = Column(String, default="new", nullable=False)
    source = Column(String, nullable=True)
    scraped_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="offers")
    retailer = relationship("Retailer", back_populates="offers")
