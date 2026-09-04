from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Retailer(Base):
    __tablename__ = "retailers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    url = Column(String, nullable=True)
    affiliate_tag = Column(String, nullable=True)

    offers = relationship("Offer", back_populates="retailer")
