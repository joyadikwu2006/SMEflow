from sqlalchemy import Column, Integer, String, Float, ForeignKey

from backend.database import Base

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, nullable=False)
    business_type = Column(String, nullable=False)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)    
    