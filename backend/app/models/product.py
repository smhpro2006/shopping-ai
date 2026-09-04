from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    image_url = Column(String, nullable=True)

    offers = relationship("Offer", back_populates="product", lazy="select",
                          order_by="Offer.price")

    def to_dict(self):
        return {
            "id": self.id,
            "brand": self.brand,
            "model": self.model,
            "name": self.name,
            "category": self.category,
            "image_url": self.image_url,
        }

    def live_offers(self) -> list:
        """Offers from real data sources. Explicitly excludes source='seed'."""
        return [o for o in self.offers if o.source != "seed"]

    def lowest_offer(self):
        live = self.live_offers()
        return live[0] if live else None
