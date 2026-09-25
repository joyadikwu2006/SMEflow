from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import Base, engine, sessionLocal
from backend.models import Business, Product

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

def get_db():
    db = sessionLocal()

    try:
        yield db
    finally:
        db.close()    


@app.get("/health")
def health_check():
    return {"status": "ok"}

class BusinessCreate(BaseModel):
    business_name: str
    business_type: str

class ProductCreate(BaseModel):
    name: str
    price: float    


@app.post("/businesses")
def create_business(
    business: BusinessCreate, 
    db: Session = Depends(get_db)
):
    db_business = Business(
        business_name=business.business_name,
        business_type=business.business_type
    )

    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    
    return {
        "message": "Business created successfully",
        "business": {
            "id": db_business.id,
            "business_name": db_business.business_name,
            "business_type": db_business.business_type
        }
    }

@app.get("/businesses")
def get_businesses(db: Session = Depends(get_db)):
    businesses = db.query(Business).all()

    return businesses   

@app.get("/businesses/{business_id}")
def get_business(business_id: int, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )
    return business    

@app.put("/businesses/{business_id}")
def update_business(
    business_id: int,
    business: BusinessCreate,
    db: Session = Depends(get_db)
):
    db_business = db.query(Business).filter(Business.id == business_id).first()

    if not db_business:
       raise HTTPException(
        status_code=404,
        detail="Business not found"
    )
    db_business.business_name = business.business_name
    db_business.business_type = business.business_type

    db.commit()
    db.refresh(db_business)

    return {
        "message": "Business updated successfully",
        "business": {
            "id": db_business.id,
            "business_name": db_business.business_name,
            "business_type": db_business.business_type
        }
    } 


@app.delete("/businesses/{business_id}")
def delete_business(
    business_id: int,
    db: Session = Depends(get_db)
):
    db_business = db.query(Business).filter(Business.id == business_id).first()

    if not db_business:
        raise HTTPException(
    status_code=404,
    detail="Business not found"
)
    db.delete(db_business)
    db.commit()

    return {
        "message": "Business deleted successfully"
    }

@app.post("/businesses/{business_id}/products")
def create_product(
    business_id: int,
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(
    status_code=404,
    detail="Business not found"
)
    db_product = Product(
        name=product.name,
        price=product.price,
        business_id=business_id
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
            "business_id": db_product.business_id
        }
    }

@app.get("/businesses/{business_id}/products")
def get_business_products(
    business_id: int,
    db: Session = Depends(get_db)
):
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(
    status_code=404,
    detail="Business not found"
)
    products = db.query(Product).filter(
        Product.business_id == business_id
    ).all()

    return products


@app.get("/businesses/{business_id}/products/{product_id}")
def get_product(
    business_id: int,
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == business_id
    ).first()

    if not product:
        raise HTTPException(
    status_code=404,
    detail="Product not found"
)
    return product 

@app.put("/businesses/{business_id}/products/{product_id}")
def update_product(
    business_id: int,
    product_id: int,
    product_data: ProductCreate,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == business_id
    ).first()

    if not product:
       raise HTTPException(
         status_code=404,
        detail="Product not found"
    )

    product.name = product_data.name
    product.price = product_data.price

    db.commit()
    db.refresh(product)

    return product

@app.delete("/businesses/{business_id}/products/{product_id}")
def delete_product(
    business_id: int,
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == business_id
    ).first()

    if not product:
        raise HTTPException(
    status_code=404,
    detail="Product not found"
)
    db.delete(product)
    db.commit()

    return {"message": "Product deleted successfully"}


@app.get("/businesses/{business_id}/details")
def get_business_details(
    business_id: int,
    db: Session = Depends(get_db)
):
    business = db.query(Business).filter(
        Business.id == business_id
    ).first()

    if not business:
        raise HTTPException(
    status_code=404,
    detail="Business not found"
)
    products = db.query(Product).filter(
        Product.business_id == business_id
    ).all()

    return {
        "business": business,
        "products": products
    }  