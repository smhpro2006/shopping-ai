from sqlalchemy import Column, Integer, String, Float
from backend.app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    store = Column(String, nullable=False)
    image_url = Column(String, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "brand": self.brand,
            "model": self.model,
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "store": self.store,
            "image_url": self.image_url,
        }
