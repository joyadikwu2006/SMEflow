# SMEflow

SMEflow is a small business management system built with Python and FastAPI.

It allows small business owners to create businesses, manage their products, and view the products belonging to each business.

## Features

- Create a business
- View all businesses
- View a single business
- Update a business
- Delete a business
- Add products to a business
- View products belonging to a business
- View a single product
- Update a product
- Delete a product
- Handle invalid business and product IDs with 404 errors
- Web frontend connected to the FastAPI backend

## Technologies Used

- Python
- FastAPI
- SQLAlchemy
- SQLite
- HTML
- CSS
- JavaScript
- Uvicorn
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
│   ├── script.js
│   └── style.css
├── tests/
├── .gitignore
├── README.md
└── requirements.txt


How to Run
1. Clone the project
git clone https://github.com/joyadikwu2006/SMEflow.git
cd SMEflow
2. Create a virtual environment
python3 -m venv venv
3. Activate the virtual environment
source venv/bin/activate
4. Install dependencies
pip install -r requirements.txt
5. Start the backend
uvicorn backend.main:app --reload

The API will run at:

http://127.0.0.1:8000

FastAPI documentation is available at:

http://127.0.0.1:8000/docs
6. Start the frontend

Open another terminal inside the SMEflow directory and run:

python3 -m http.server 5500 --directory frontend

Then open:

http://127.0.0.1:5500
API Endpoints
Businesses
Method	Endpoint	Description
GET	/businesses	Get all businesses
POST	/businesses	Create a business
GET	/businesses/{business_id}	Get one business
PUT	/businesses/{business_id}	Update a business
DELETE	/businesses/{business_id}	Delete a business
Products
Method	Endpoint	Description
POST	/businesses/{business_id}/products	Create a product
GET	/businesses/{business_id}/products	Get business products
GET	/businesses/{business_id}/products/{product_id}	Get one product
PUT	/businesses/{business_id}/products/{product_id}	Update a product
DELETE	/businesses/{business_id}/products/{product_id}	Delete a product
Business Details
GET /businesses/{business_id}/details

Returns the business together with its products.

Health Check
GET /health

Returns:

{
  "status": "ok"
}
Database Relationship

Each product belongs to a business.

Business
   |
   | 1-to-many
   |
   └── Products

The business_id field in the products table is a foreign key that references the id of a business.

Project Goal

SMEflow is designed as a foundation for a small business management platform. Future versions can include features such as sales tracking, inventory management, expenses, reports, and business analytics.


Then save it in **nano**:

1. Press `Ctrl + O`
2. Press `Enter`
3. Press `Ctrl + X`

Then check it:

```bash
cat README.md