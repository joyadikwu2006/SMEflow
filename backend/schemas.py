from pydantic import BaseModel, Field, field_validator


class BusinessCreate(BaseModel):
    business_name: str = Field(..., min_length=1)
    business_type: str = Field(..., min_length=1)

    @field_validator("business_name", "business_type")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be empty")
        return cleaned


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    description: str = Field(default="", max_length=1000)
    image_url: str = Field(default="", max_length=2048)
    stock_quantity: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty")
        return cleaned

    @field_validator("description", "image_url")
    @classmethod
    def clean_optional_text(cls, value: str) -> str:
        return value.strip()

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1)
    customer_email: str = Field(..., min_length=1)
    payment_method: str = Field(..., min_length=1)
    items: list[OrderItemCreate] = Field(..., min_length=1)

    @field_validator("customer_name", "customer_email", "payment_method")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be empty")
        return cleaned


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class PaymentIntentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = "NGN"
    customer_email: str = Field(..., min_length=1)


class CheckoutItem(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class StripeCheckoutRequest(BaseModel):
    items: list[CheckoutItem] = Field(..., min_length=1)
    customer_name: str = Field(..., min_length=1)
    customer_email: str = Field(..., min_length=1)
    currency: str = "NGN"


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1)
