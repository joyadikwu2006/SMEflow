from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(255), nullable=False)
    business_type = Column(String(255), nullable=False)
    products = relationship(
        "Product",
        back_populates="business",
        cascade="all, delete-orphan",
    )
    orders = relationship("Order", back_populates="business")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String(1000), nullable=False, default="")
    image_url = Column(String(2048), nullable=False, default="")
    stock_quantity = Column(Integer, nullable=False, default=0)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    business = relationship("Business", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)
    payment_method = Column(String(50), nullable=False)
    payment_status = Column(String(50), nullable=False, default="paid")
    status = Column(String(50), nullable=False, default="pending")
    total_amount = Column(Float, nullable=False, default=0.0)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    business = relationship("Business", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")