import json
import os

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.database import Base, engine
from backend.models import Business, Order, Product, ProcessedStripeSession
from backend.main import app, get_db


TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_business_and_product_lifecycle():
    owner_login = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    token = owner_login.json()["token"]

    business_response = client.post(
        "/businesses",
        json={"business_name": "Acme Stores", "business_type": "Retail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert business_response.status_code == 200, business_response.text
    business_id = business_response.json()["business"]["id"]

    product_response = client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Notebook", "price": 250.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert product_response.status_code == 200, product_response.text

    list_response = client.get(f"/businesses/{business_id}/products")
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "Notebook"

    delete_response = client.delete(f"/businesses/{business_id}", headers={"Authorization": f"Bearer {token}"})
    assert delete_response.status_code == 200, delete_response.text

    business_lookup = client.get(f"/businesses/{business_id}")
    assert business_lookup.status_code == 404


def test_product_price_must_be_positive():
    owner_login = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    token = owner_login.json()["token"]

    response = client.post(
        "/businesses",
        json={"business_name": "Bad Business", "business_type": "Wholesale"},
        headers={"Authorization": f"Bearer {token}"},
    )
    business_id = response.json()["business"]["id"]

    product_response = client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Free Item", "price": 0},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert product_response.status_code == 422


def test_business_name_cannot_be_blank():
    owner_login = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    token = owner_login.json()["token"]

    response = client.post(
        "/businesses",
        json={"business_name": "", "business_type": "Services"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_owner_and_customer_login_routes():
    owner_response = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    assert owner_response.status_code == 200
    payload = owner_response.json()
    assert payload["role"] == "owner"
    assert payload["token_type"] == "bearer"
    claims = jwt.decode(payload["token"], os.getenv("JWT_SECRET_KEY", "dev-secret-change-me"), algorithms=["HS256"])
    assert claims["role"] == "owner"

    customer_response = client.post(
        "/auth/customer/login",
        json={"username": "customer", "password": "customer123"},
    )
    assert customer_response.status_code == 200
    assert customer_response.json()["role"] == "customer"


def test_owner_routes_require_valid_session_token():
    unauthorized_response = client.post(
        "/businesses",
        json={"business_name": "No Token Store", "business_type": "Retail"},
    )
    assert unauthorized_response.status_code == 401

    owner_login = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    token = owner_login.json()["token"]

    authorized_response = client.post(
        "/businesses",
        json={"business_name": "Secure Store", "business_type": "Retail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert authorized_response.status_code == 200

def test_payment_intent_returns_503_without_stripe_secret(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    response = client.post(
        "/payments/create-intent",
        json={
            "amount": 1000,
            "currency": "NGN",
            "customer_email": "jane@example.com",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Stripe payments are not configured on this server."
    )
    assert "status" not in response.json()


def test_checkout_session_returns_503_without_stripe_secret(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    response = client.post(
        "/payments/create-checkout-session",
        json={
            "items": [{"product_id": 999999, "quantity": 1}],
            "customer_name": "Jane Doe",
            "customer_email": "jane@example.com",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Stripe payments are not configured on this server."
    )
    assert "url" not in response.json()


def test_checkout_session_uses_stripe_when_configured(monkeypatch):
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
    stripe_calls = []

    class FakeSession:
        url = "https://checkout.stripe.com/test_session"
        id = "cs_test_123"
        status = "open"

    def fake_create(**kwargs):
        stripe_calls.append(kwargs)
        return FakeSession()

    class FakeStripeModule:
        checkout = type(
            "Checkout",
            (),
            {
                "Session": type(
                    "Session",
                    (),
                    {"create": staticmethod(fake_create)},
                )
            },
        )()

    monkeypatch.setitem(
        __import__("sys").modules,
        "stripe",
        FakeStripeModule(),
    )

    owner_login = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    token = owner_login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    business_response = client.post(
        "/businesses",
        json={"business_name": "Stripe Shop", "business_type": "Retail"},
        headers=headers,
    )
    business_id = business_response.json()["business"]["id"]

    first_product = client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Headphones", "price": 20.0},
        headers=headers,
    ).json()["product"]["id"]

    second_product = client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Keyboard", "price": 35.0},
        headers=headers,
    ).json()["product"]["id"]

    checkout_response = client.post(
        "/payments/create-checkout-session",
        json={
            "items": [
                {"product_id": first_product, "quantity": 2},
                {"product_id": second_product, "quantity": 1},
            ],
            "customer_name": "Jane Doe",
            "customer_email": "jane@example.com",
        },
    )

    assert checkout_response.status_code == 200
    assert checkout_response.json()["provider"] == "stripe"
    assert checkout_response.json()["url"] == (
        "https://checkout.stripe.com/test_session"
    )

    assert len(stripe_calls) == 1

    line_items = stripe_calls[0]["line_items"]
    assert len(line_items) == 2
    assert line_items[0]["price_data"]["product_data"]["name"] == "Headphones"
    assert line_items[0]["price_data"]["unit_amount"] == 2000
    assert line_items[0]["quantity"] == 2
    assert line_items[1]["price_data"]["product_data"]["name"] == "Keyboard"
    assert line_items[1]["price_data"]["unit_amount"] == 3500
    assert line_items[1]["quantity"] == 1
    assert checkout_response.json()["amount"] == 75.0


def test_checkout_rejects_duplicate_products_before_calling_stripe(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    stripe_calls = []

    def fake_create(**kwargs):
        stripe_calls.append(kwargs)

    fake_stripe = type(
        "Stripe",
        (),
        {
            "checkout": type(
                "Checkout",
                (),
                {"Session": type("Session", (), {"create": staticmethod(fake_create)})()},
            )(),
        },
    )()
    monkeypatch.setitem(__import__("sys").modules, "stripe", fake_stripe)

    owner_login = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    token = owner_login.json()["token"]
    business_response = client.post(
        "/businesses",
        json={"business_name": "Duplicate Checkout Shop", "business_type": "Retail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    business_id = business_response.json()["business"]["id"]
    product_response = client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Notebook", "price": 12.5, "stock_quantity": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    product_id = product_response.json()["product"]["id"]

    response = client.post(
        "/payments/create-checkout-session",
        json={
            "items": [
                {"product_id": product_id, "quantity": 1},
                {"product_id": product_id, "quantity": 2},
            ],
            "customer_name": "Jane Doe",
            "customer_email": "jane@example.com",
        },
    )

    assert response.status_code == 400
    assert "more than once" in response.json()["detail"]
    assert stripe_calls == []


def test_stripe_webhook_confirms_completed_checkout(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")
    stripe_calls = []
    event_holder = {"event": None}

    class FakeSession:
        url = "https://checkout.stripe.com/test_session"
        id = "cs_test_webhook_001"
        status = "open"

    def fake_create(**kwargs):
        stripe_calls.append(kwargs)
        return FakeSession()

    class FakeWebhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            assert sig == "valid-signature"
            assert secret == "whsec_test_123"
            return event_holder["event"]

    fake_stripe = type(
        "Stripe",
        (),
        {
            "Webhook": FakeWebhook,
            "checkout": type(
                "Checkout",
                (),
                {"Session": type("Session", (), {"create": staticmethod(fake_create)})()},
            )(),
        },
    )()
    monkeypatch.setitem(__import__("sys").modules, "stripe", fake_stripe)

    owner_login = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    token = owner_login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    business_response = client.post(
        "/businesses",
        json={"business_name": "Webhook Shop", "business_type": "Retail"},
        headers=headers,
    )
    business_id = business_response.json()["business"]["id"]
    product_response = client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Smartphone", "price": 250.0, "stock_quantity": 2},
        headers=headers,
    )
    product_id = product_response.json()["product"]["id"]

    checkout_response = client.post(
        "/payments/create-checkout-session",
        json={
            "items": [{"product_id": product_id, "quantity": 2}],
            "customer_name": "Jane Doe",
            "customer_email": "jane@example.com",
            "currency": "NGN",
        },
    )
    assert checkout_response.status_code == 200, checkout_response.text

    metadata = stripe_calls[0]["metadata"]
    assert metadata["items"] == json.dumps(
        [{"product_id": product_id, "quantity": 2, "unit_amount": 25000}],
        separators=(",", ":"),
    )
    assert metadata["amount_total"] == "50000"
    assert metadata["currency"] == "ngn"

    # Send the exact metadata generated above through the webhook parser.
    event_holder["event"] = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": checkout_response.json()["session_id"],
                "payment_status": "paid",
                "amount_total": 50000,
                "currency": "ngn",
                "customer_email": "jane@example.com",
                "metadata": metadata,
            }
        },
    }
    response = client.post(
        "/payments/webhook",
        data=b'{"event": "test"}',
        headers={"stripe-signature": "valid-signature"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "received"
    second_response = client.post(
        "/payments/webhook",
        data=b'{"event": "test"}',
        headers={"stripe-signature": "valid-signature"},
    )
    assert second_response.status_code == 200, second_response.text
    assert second_response.json()["status"] == "already_processed"

    order_response = client.get("/orders")
    webhook_orders = [
        order for order in order_response.json()
        if order["customer_email"] == "jane@example.com"
        and order["payment_method"] == "stripe"
    ]
    assert len(webhook_orders) == 1
    assert webhook_orders[0]["items"][0]["quantity"] == 2
    assert webhook_orders[0]["total_amount"] == 500.0

    products_response = client.get("/products")
    webhook_product = next(
        product for product in products_response.json()
        if product["id"] == product_id
    )
    assert webhook_product["stock_quantity"] == 0

    mismatched_session = event_holder["event"]["data"]["object"].copy()
    mismatched_session["id"] = "cs_test_amount_mismatch"
    mismatched_session["amount_total"] = 49999
    event_holder["event"] = {
        "type": "checkout.session.completed",
        "data": {"object": mismatched_session},
    }
    amount_mismatch_response = client.post(
        "/payments/webhook",
        data=b'{"event": "test"}',
        headers={"stripe-signature": "valid-signature"},
    )
    assert amount_mismatch_response.status_code == 400
    assert "amount does not match" in amount_mismatch_response.json()["detail"]

    mismatched_session["id"] = "cs_test_currency_mismatch"
    mismatched_session["amount_total"] = 50000
    mismatched_session["currency"] = "usd"
    currency_mismatch_response = client.post(
        "/payments/webhook",
        data=b'{"event": "test"}',
        headers={"stripe-signature": "valid-signature"},
    )
    assert currency_mismatch_response.status_code == 400
    assert "currency does not match" in currency_mismatch_response.json()["detail"]

def test_customer_can_buy_products():
    owner_login = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    token = owner_login.json()["token"]

    business_response = client.post(
        "/businesses",
        json={"business_name": "Market Hub", "business_type": "Retail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    business_id = business_response.json()["business"]["id"]

    product_response = client.post(
        f"/businesses/{business_id}/products",
        json={"name": "Smartphone", "price": 250.0, "stock_quantity": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    product_id = product_response.json()["product"]["id"]

    storefront_response = client.get("/products")
    assert storefront_response.status_code == 200
    assert any(product["id"] == product_id for product in storefront_response.json())

    order_response = client.post(
        "/orders",
        json={
            "customer_name": "Jane Doe",
            "customer_email": "jane@example.com",
            "payment_method": "transfer",
            "items": [{"product_id": product_id, "quantity": 2}],
        },
    )

    assert order_response.status_code == 200, order_response.text
    payload = order_response.json()
    assert payload["total_amount"] == 500.0
    assert payload["payment_status"] == "pending"
    assert payload["items"][0]["quantity"] == 2

    products_response = client.get("/products")
    purchased_product = next(
        product for product in products_response.json()
        if product["id"] == product_id
    )
    assert purchased_product["stock_quantity"] == 0

    excess_order_response = client.post(
        "/orders",
        json={
            "customer_name": "Jane Doe",
            "customer_email": "jane@example.com",
            "payment_method": "transfer",
            "items": [{"product_id": product_id, "quantity": 1}],
        },
    )
    assert excess_order_response.status_code == 400
    owner_orders_response = client.get(f"/businesses/{business_id}/orders")
    assert owner_orders_response.status_code == 200
    assert owner_orders_response.json()[0]["customer_name"] == "Jane Doe"

    status_update = client.patch(
        f"/orders/{order_response.json()['id']}/status",
        json={"status": "paid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_update.status_code == 200
    assert status_update.json()["payment_status"] == "paid"

    shipping_update = client.patch(
        f"/orders/{order_response.json()['id']}/status",
        json={"status": "shipped"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert shipping_update.status_code == 200
    assert shipping_update.json()["status"] == "shipped"


def test_bank_transfer_rejects_insufficient_stock_without_order_or_deduction():
    db = TestingSessionLocal()
    try:
        business = Business(business_name="Transfer Stock Shop", business_type="Retail")
        db.add(business)
        db.flush()
        product = Product(
            name="Limited Item",
            price=10.0,
            description="",
            image_url="",
            stock_quantity=1,
            business_id=business.id,
        )
        db.add(product)
        db.commit()
        product_id = product.id
    finally:
        db.close()

    response = client.post(
        "/orders",
        json={
            "customer_name": "Insufficient Transfer Buyer",
            "customer_email": "transfer-insufficient@example.com",
            "payment_method": "transfer",
            "items": [{"product_id": product_id, "quantity": 2}],
        },
    )

    assert response.status_code == 400
    db = TestingSessionLocal()
    try:
        assert db.query(Product).filter_by(id=product_id).one().stock_quantity == 1
        assert (
            db.query(Order)
            .filter_by(customer_email="transfer-insufficient@example.com")
            .count()
            == 0
        )
    finally:
        db.close()


def test_transfer_rolls_back_all_reservations_when_second_product_fails():
    db = TestingSessionLocal()
    try:
        business = Business(business_name="Atomic Transfer Shop", business_type="Retail")
        db.add(business)
        db.flush()
        products = [
            Product(
                name=f"Item {index}",
                price=10.0,
                description="",
                image_url="",
                stock_quantity=2,
                business_id=business.id,
            )
            for index in range(2)
        ]
        db.add_all(products)
        db.commit()
        product_ids = [product.id for product in products]
    finally:
        db.close()

    trigger_name = "fail_second_transfer_reservation"
    with engine.begin() as connection:
        connection.exec_driver_sql(
            f"CREATE TRIGGER {trigger_name} BEFORE UPDATE OF stock_quantity ON products "
            f"WHEN OLD.id = {product_ids[1]} BEGIN SELECT RAISE(IGNORE); END"
        )

    try:
        response = client.post(
            "/orders",
            json={
                "customer_name": "Atomic Transfer Buyer",
                "customer_email": "transfer-rollback@example.com",
                "payment_method": "transfer",
                "items": [
                    {"product_id": product_ids[0], "quantity": 1},
                    {"product_id": product_ids[1], "quantity": 1},
                ],
            },
        )
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trigger_name}")

    assert response.status_code == 400
    db = TestingSessionLocal()
    try:
        assert [
            db.query(Product).filter_by(id=product_id).one().stock_quantity
            for product_id in product_ids
        ] == [2, 2]
        assert (
            db.query(Order)
            .filter_by(customer_email="transfer-rollback@example.com")
            .count()
            == 0
        )
    finally:
        db.close()


def test_stripe_insufficient_stock_rolls_back_processed_session_and_order(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")

    db = TestingSessionLocal()
    try:
        business = Business(business_name="Stripe Stock Shop", business_type="Retail")
        db.add(business)
        db.flush()
        product = Product(
            name="Limited Stripe Item",
            price=10.0,
            description="",
            image_url="",
            stock_quantity=1,
            business_id=business.id,
        )
        db.add(product)
        db.commit()
        product_id = product.id
    finally:
        db.close()

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_insufficient_stock_001",
                "payment_status": "paid",
                "amount_total": 2000,
                "currency": "ngn",
                "customer_email": "stripe-insufficient@example.com",
                "metadata": {
                    "customer_name": "Insufficient Stripe Buyer",
                    "items": json.dumps(
                        [{"product_id": product_id, "quantity": 2, "unit_amount": 1000}],
                        separators=(",", ":"),
                    ),
                    "currency": "ngn",
                    "amount_total": "2000",
                },
            }
        },
    }

    class FakeWebhook:
        @staticmethod
        def construct_event(payload, signature, secret):
            assert signature == "valid-signature"
            assert secret == "whsec_test_123"
            return event

    monkeypatch.setitem(
        __import__("sys").modules,
        "stripe",
        type("Stripe", (), {"Webhook": FakeWebhook})(),
    )

    response = client.post(
        "/payments/webhook",
        data=b'{"event": "test"}',
        headers={"stripe-signature": "valid-signature"},
    )

    assert response.status_code == 400
    db = TestingSessionLocal()
    try:
        assert db.query(Product).filter_by(id=product_id).one().stock_quantity == 1
        assert (
            db.query(ProcessedStripeSession)
            .filter_by(session_id="cs_insufficient_stock_001")
            .count()
            == 0
        )
        assert (
            db.query(Order)
            .filter_by(customer_email="stripe-insufficient@example.com")
            .count()
            == 0
        )
    finally:
        db.close()

def test_owner_cannot_manually_mark_stripe_payment_as_paid():
    owner_login = client.post(
        "/auth/owner/login",
        json={"username": "owner", "password": "owner123"},
    )
    token = owner_login.json()["token"]

    db = TestingSessionLocal()

    try:
        business = Business(
            business_name="Test Store",
            business_type="Retail",
        )
        db.add(business)
        db.commit()
        db.refresh(business)

        order = Order(
            customer_name="Jane Doe",
            customer_email="jane@example.com",
            payment_method="stripe",
            payment_status="pending",
            status="pending",
            total_amount=1000,
            business_id=business.id,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        order_id = order.id
    finally:
        db.close()

    response = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "paid"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "Stripe payments must be confirmed" in response.json()["detail"]

    db = TestingSessionLocal()
    try:
        saved_order = db.query(Order).filter(Order.id == order_id).first()
        assert saved_order.payment_status == "pending"
    finally:
        db.close()
