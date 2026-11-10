# SMEflow

SMEflow is a small business management platform built with Python and FastAPI. It helps small business owners manage their businesses, products, inventory, and customer orders.

Customers can browse available products, add items to their cart, and place orders using the available payment options.

## Features

### Business Management
- Create a business.
- View all businesses.
- View individual business details.
- Update and delete businesses.
- View products belonging to a business.

### Product Management
- Add products to a business.
- View all available products.
- View individual products.
- Update and delete products.
- Manage product prices and stock quantities.

### Authentication
- Owner login.
- Customer login.
- JWT-based session tokens.
- Owner authentication for protected order-management actions.

### Customer Shopping and Orders
- Browse products.
- Add products to a shopping cart.
- Purchase multiple products in one checkout.
- Place bank-transfer orders.
- View order details and order statuses.

### Payment Integration
- Stripe PaymentIntent support.
- Stripe Checkout integration.
- Stripe webhook signature verification.
- Bank-transfer orders remain pending until the owner confirms payment.
- Stripe payments are confirmed through the verified Stripe webhook.

**Important:** Stripe payments require valid Stripe credentials. Payment endpoints return an error when Stripe is not configured; the application does not treat a demo response as a successful payment.

## Technologies Used

- Python 3.12
- FastAPI
- SQLAlchemy
- SQLite
- PostgreSQL support
- Pydantic
- PyJWT
- Stripe
- HTML
- CSS
- JavaScript
- Uvicorn
- Pytest
- Git and GitHub

## Project Structure

```text
SMEflow/
├── backend/
│   ├── __init__.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── frontend/
│   ├── index.html
│   ├── owner.html
│   ├── customer.html
│   ├── script.js
│   ├── customer.js
│   └── style.css
├── tests/
│   └── test_api.py
├── .gitignore
├── pytest.ini
├── README.md
└── requirements.txt
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/joyadikwu2006/SMEflow.git
cd SMEflow
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

On Linux or macOS:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

The backend supports the following environment variables:

| Variable | Purpose |
|---|---|
| `JWT_SECRET_KEY` | Secret used to sign authentication tokens |
| `STRIPE_SECRET_KEY` | Stripe API secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `FRONTEND_URL` | Frontend URL used for Stripe redirects |

For local development, set the variables in your terminal:

```bash
export JWT_SECRET_KEY="your-development-secret"
export STRIPE_SECRET_KEY="your-stripe-secret-key"
export STRIPE_WEBHOOK_SECRET="your-webhook-secret"
export FRONTEND_URL="http://127.0.0.1:5500"
```

Use your actual Stripe credentials when testing payments. Never commit real secrets to GitHub.

The JWT secret must be strong and securely configured before deployment.

### 6. Start the backend

From the project directory, run:

```bash
uvicorn backend.main:app --reload
```

The backend API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation:

```text
http://127.0.0.1:8000/docs
```

### 7. Start the frontend

Open another terminal inside the SMEflow directory.

Activate the virtual environment if needed, then run:

```bash
python3 -m http.server 5500 --directory frontend
```

Open the frontend in your browser:

```text
http://127.0.0.1:5500
```

## API Endpoints

### Health Check

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check API availability |

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/owner/login` | Owner login |
| POST | `/auth/customer/login` | Customer login |

### Businesses

| Method | Endpoint | Description |
|---|---|---|
| POST | `/businesses` | Create a business |
| GET | `/businesses` | Get all businesses |
| GET | `/businesses/{business_id}` | Get one business |
| PUT | `/businesses/{business_id}` | Update a business |
| DELETE | `/businesses/{business_id}` | Delete a business |
| GET | `/businesses/{business_id}/details` | Get business details and products |
| GET | `/businesses/{business_id}/orders` | Get business orders |

### Products

| Method | Endpoint | Description |
|---|---|---|
| GET | `/products` | Get all products |
| GET | `/products/{product_id}` | Get one product |
| POST | `/businesses/{business_id}/products` | Add a product |
| GET | `/businesses/{business_id}/products` | Get business products |
| GET | `/businesses/{business_id}/products/{product_id}` | Get one business product |
| PUT | `/businesses/{business_id}/products/{product_id}` | Update a product |
| DELETE | `/businesses/{business_id}/products/{product_id}` | Delete a product |

### Orders

| Method | Endpoint | Description |
|---|---|---|
| GET | `/orders` | Get all orders |
| POST | `/orders` | Create a bank-transfer order |
| GET | `/orders/{order_id}` | Get one order |
| PATCH | `/orders/{order_id}/status` | Update an order status |

### Payments

| Method | Endpoint | Description |
|---|---|---|
| POST | `/payments/create-intent` | Create a Stripe PaymentIntent |
| POST | `/payments/create-checkout-session` | Create a Stripe Checkout session |
| POST | `/payments/webhook` | Receive and verify Stripe payment events |

## Payment Behaviour

SMEflow supports Stripe checkout and bank-transfer orders.

**Stripe payments**
- Customers are redirected to Stripe Checkout.
- The backend creates a Stripe Checkout session.
- Stripe sends payment events to the webhook endpoint.
- The webhook verifies the event signature before confirming a successful payment.
- Stripe payments cannot be manually marked as paid through the owner order-status endpoint.

**Bank transfers**
- Customers can create bank-transfer orders.
- Orders initially have a pending payment status.
- Stock is deducted when the bank-transfer order is created.
- The owner can confirm the transfer through the order-status endpoint.

## Database Relationship

Each business can have multiple products.

Each order belongs to a business and can contain multiple order items.

```text
Business
   |
   | 1-to-many
   |
 Products

Business
   |
   | 1-to-many
   |
 Orders
   |
   | 1-to-many
   |
Order Items
```

Products and orders are connected through their respective database relationships.

## Running Tests

SMEflow uses Pytest for automated testing.

Install the testing dependencies:

```bash
pip install pytest httpx2
```

Run the test suite:

```bash
python -m pytest -v
```

The tests cover business and product operations, authentication, payment configuration, Stripe checkout, webhook verification, and order behaviour.

## Development Login Credentials

The current development version contains hardcoded demo login credentials:

- Owner: `owner` / `owner123`
- Customer: `customer` / `customer123`

**These credentials are for development and testing only.** They must be replaced with proper user registration and secure password handling before production deployment.

## Project Goal

SMEflow aims to provide small businesses with a simple platform for managing products, inventory, customers, and orders.

Future improvements include stronger inventory protection, improved user authentication, reporting, business analytics, and production deployment.

## Project Status

SMEflow is an actively developed project. Its current implementation includes business and product management, customer shopping, order management, authentication, Stripe integration, and automated backend tests.
