import json
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database import Base, SessionLocal, engine
from backend.models import Business, Order, OrderItem, Product
from backend.schemas import (
    BusinessCreate,
    LoginRequest,
    OrderCreate,
    OrderStatusUpdate,
    PaymentIntentRequest,
    ProductCreate,
    StripeCheckoutRequest,
)

app = FastAPI(title="SMEflow API")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def create_session_token(username: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=12)
    payload = {"sub": username, "role": role, "exp": exp.timestamp()}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_auth_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token format")

    return token


def require_owner_session(authorization: str | None = Header(default=None)) -> dict:
    token = get_auth_token(authorization)

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    if payload.get("role") != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")

    return payload


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/auth/owner/login")
def owner_login(credentials: LoginRequest):
    if credentials.username == "owner" and credentials.password == "owner123":
        token = create_session_token(credentials.username, "owner")
        return {
            "role": "owner",
            "username": credentials.username,
            "token": token,
            "token_type": "bearer",
            "message": "Login successful",
        }

    raise HTTPException(status_code=401, detail="Invalid owner credentials")


@app.post("/auth/customer/login")
def customer_login(credentials: LoginRequest):
    if credentials.username == "customer" and credentials.password == "customer123":
        token = create_session_token(credentials.username, "customer")
        return {
            "role": "customer",
            "username": credentials.username,
            "token": token,
            "token_type": "bearer",
            "message": "Login successful",
        }

    raise HTTPException(status_code=401, detail="Invalid customer credentials")


@app.post("/payments/create-intent")
def create_payment_intent(payment: PaymentIntentRequest):
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")

    if stripe_secret_key:
        try:
            import stripe

            stripe.api_key = stripe_secret_key
            intent = stripe.PaymentIntent.create(
                amount=int(round(payment.amount * 100)),
                currency=payment.currency.lower(),
                receipt_email=payment.customer_email,
            )
            return {
                "provider": "stripe",
                "status": intent.status,
                "client_secret": intent.client_secret,
                "amount": payment.amount,
                "currency": payment.currency,
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Payment gateway error: {exc}")

    return {
        "provider": "demo",
        "status": "succeeded",
        "client_secret": "demo-client-secret",
        "amount": payment.amount,
        "currency": payment.currency,
    }


@app.post("/payments/create-checkout-session")
def create_checkout_session(payload: StripeCheckoutRequest, db: Session = Depends(get_db)):
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
    frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")

    line_items = []
    total_amount = 0.0

    for item in payload.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        line_total = product.price * item.quantity
        total_amount += line_total
        line_items.append(
            {
                "price_data": {
                    "currency": payload.currency.lower(),
                    "product_data": {"name": product.name},
                    "unit_amount": int(round(product.price * 100)),
                },
                "quantity": item.quantity,
            }
        )

    if stripe_secret_key:
        try:
            import stripe

            stripe.api_key = stripe_secret_key
            session = stripe.checkout.Session.create(
                success_url=f"{frontend_url}/customer.html?checkout=success",
                cancel_url=f"{frontend_url}/customer.html?checkout=cancelled",
                mode="payment",
                customer_email=payload.customer_email,
                line_items=line_items,
                metadata={
                    "customer_name": payload.customer_name,
                    "items": str([{"product_id": item.product_id, "quantity": item.quantity} for item in payload.items]),
                },
            )
            return {
                "provider": "stripe",
                "status": getattr(session, "status", "open"),
                "url": session.url,
                "session_id": session.id,
                "amount": total_amount,
                "currency": payload.currency,
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Stripe checkout error: {exc}")

    return {
        "provider": "demo",
        "status": "demo",
        "url": f"{frontend_url}/customer.html?checkout=demo",
        "session_id": "demo-checkout-session",
        "amount": total_amount,
        "currency": payload.currency,
    }


@app.post("/payments/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not stripe_secret_key or not webhook_secret:
        return {"status": "disabled"}

    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing stripe signature")

    try:
        import stripe

        event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook signature: {exc}") from exc

    if event.get("type") != "checkout.session.completed":
        return {"status": "ignored", "event": event.get("type")}

    session = event.get("data", {}).get("object", {})
    metadata = session.get("metadata") or {}
    customer_name = metadata.get("customer_name") or "Customer"
    customer_email = session.get("customer_email") or metadata.get("customer_email") or "unknown@example.com"
    items_raw = metadata.get("items") or "[]"

    try:
        items = json.loads(items_raw)
    except json.JSONDecodeError:
        items = []

    if not items:
        raise HTTPException(status_code=400, detail="Checkout session had no items to process")

    grouped_items = {}
    for item in items:
        product = db.query(Product).filter(Product.id == item["product_id"]).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item['product_id']} not found")
        grouped_items.setdefault(product.business_id, []).append({
            "product_id": product.id,
            "quantity": int(item.get("quantity", 1)),
            "unit_price": product.price,
        })

    created_orders = []
    for business_id, business_items in grouped_items.items():
        total_amount = sum(item["unit_price"] * item["quantity"] for item in business_items)
        order = Order(
            customer_name=customer_name,
            customer_email=customer_email,
            payment_method="stripe",
            payment_status="paid",
            status="paid",
            total_amount=total_amount,
            business_id=business_id,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        for item in business_items:
            db_item = OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                line_total=item["unit_price"] * item["quantity"],
            )
            db.add(db_item)

        db.commit()
        created_orders.append({"id": order.id, "status": order.status, "total_amount": order.total_amount})

    return {"status": "received", "orders": created_orders}


@app.post("/businesses")
def create_business(
    business: BusinessCreate,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_owner_session),
):
    db_business = Business(
        business_name=business.business_name,
        business_type=business.business_type,
    )

    db.add(db_business)
    db.commit()
    db.refresh(db_business)

    return {
        "message": "Business created successfully",
        "business": {
            "id": db_business.id,
            "business_name": db_business.business_name,
            "business_type": db_business.business_type,
        },
    }


@app.get("/businesses")
def get_businesses(db: Session = Depends(get_db)):
    return db.query(Business).all()


@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return [
        {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "business_id": product.business_id,
            "business_name": product.business.business_name,
            "business_type": product.business.business_type,
        }
        for product in products
    ]


@app.get("/products/{product_id}")
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "business_id": product.business_id,
        "business_name": product.business.business_name,
        "business_type": product.business.business_type,
    }


@app.get("/businesses/{business_id}/orders")
def get_business_orders(business_id: int, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    orders = db.query(Order).filter(Order.business_id == business_id).all()
    return [
        {
            "id": order.id,
            "customer_name": order.customer_name,
            "customer_email": order.customer_email,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "status": order.status,
            "total_amount": order.total_amount,
            "business_id": order.business_id,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total,
                }
                for item in order.items
            ],
        }
        for order in orders
    ]


@app.get("/businesses/{business_id}")
def get_business(business_id: int, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    return business


@app.put("/businesses/{business_id}")
def update_business(
    business_id: int,
    business_data: BusinessCreate,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_owner_session),
):
    db_business = db.query(Business).filter(Business.id == business_id).first()

    if not db_business:
        raise HTTPException(status_code=404, detail="Business not found")

    db_business.business_name = business_data.business_name
    db_business.business_type = business_data.business_type

    db.commit()
    db.refresh(db_business)

    return {
        "message": "Business updated successfully",
        "business": {
            "id": db_business.id,
            "business_name": db_business.business_name,
            "business_type": db_business.business_type,
        },
    }


@app.delete("/businesses/{business_id}")
def delete_business(
    business_id: int,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_owner_session),
):
    db_business = db.query(Business).filter(Business.id == business_id).first()

    if not db_business:
        raise HTTPException(status_code=404, detail="Business not found")

    for product in list(db_business.products):
        db.delete(product)

    db.delete(db_business)
    db.commit()

    return {"message": "Business deleted successfully"}


@app.post("/businesses/{business_id}/products")
def create_product(
    business_id: int,
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_owner_session),
):
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    db_product = Product(
        name=product_data.name,
        price=product_data.price,
        business_id=business_id,
    )

    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return {
        "message": "Product created successfully",
        "product": {
            "id": db_product.id,
            "name": db_product.name,
            "price": db_product.price,
            "business_id": db_product.business_id,
        },
    }


@app.get("/businesses/{business_id}/products")
def get_business_products(business_id: int, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    return db.query(Product).filter(Product.business_id == business_id).all()


@app.get("/businesses/{business_id}/products/{product_id}")
def get_product(business_id: int, product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == business_id,
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@app.put("/businesses/{business_id}/products/{product_id}")
def update_product(
    business_id: int,
    product_id: int,
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_owner_session),
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == business_id,
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.name = product_data.name
    product.price = product_data.price

    db.commit()
    db.refresh(product)

    return product


@app.delete("/businesses/{business_id}/products/{product_id}")
def delete_product(
    business_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_owner_session),
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == business_id,
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return {"message": "Product deleted successfully"}


@app.get("/businesses/{business_id}/details")
def get_business_details(business_id: int, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business_data = {
        "id": business.id,
        "business_name": business.business_name,
        "business_type": business.business_type,
    }

    products = [
        {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "business_id": product.business_id,
        }
        for product in business.products
    ]

    return {"business": business_data, "products": products}


@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return [
        {
            "id": order.id,
            "customer_name": order.customer_name,
            "customer_email": order.customer_email,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "status": order.status,
            "total_amount": order.total_amount,
            "business_id": order.business_id,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_total": item.line_total,
                }
                for item in order.items
            ],
        }
        for order in orders
    ]


@app.post("/orders")
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    if not order_data.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    total_amount = 0.0
    item_payload = []

    for item in order_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        line_total = product.price * item.quantity
        total_amount += line_total
        item_payload.append(
            {
                "product_id": product.id,
                "quantity": item.quantity,
                "unit_price": product.price,
                "line_total": line_total,
                "business_id": product.business_id,
            }
        )

    if not item_payload:
        raise HTTPException(status_code=400, detail="Order cannot be empty")

    business_id = item_payload[0]["business_id"]
    for item in item_payload:
        if item["business_id"] != business_id:
            raise HTTPException(
                status_code=400,
                detail="All items in one order must belong to the same business",
            )

    db_order = Order(
        customer_name=order_data.customer_name,
        customer_email=order_data.customer_email,
        payment_method=order_data.payment_method,
        payment_status="paid",
        status="paid",
        total_amount=total_amount,
        business_id=business_id,
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    for item in item_payload:
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=item["product_id"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            line_total=item["line_total"],
        )
        db.add(db_item)

    db.commit()

    return {
        "id": db_order.id,
        "customer_name": db_order.customer_name,
        "customer_email": db_order.customer_email,
        "payment_method": db_order.payment_method,
        "payment_status": "paid",
        "status": db_order.status,
        "total_amount": db_order.total_amount,
        "business_id": db_order.business_id,
        "items": [
            {
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "line_total": item["line_total"],
            }
            for item in item_payload
        ],
    }


@app.patch("/orders/{order_id}/status")
def update_order_status(order_id: int, update: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    valid_statuses = {"pending", "paid", "processing", "shipped", "delivered", "cancelled"}
    status_value = update.status.strip().lower()

    if status_value not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid order status")

    order.status = status_value
    if status_value == "paid":
        order.payment_status = "paid"

    db.commit()
    db.refresh(order)

    return {"id": order.id, "status": order.status, "payment_status": order.payment_status}


@app.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "id": order.id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "total_amount": order.total_amount,
        "business_id": order.business_id,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
            }
            for item in order.items
        ],
    }