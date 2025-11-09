# erp/models.py
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DB_URL
from sqlalchemy.exc import SQLAlchemyError

Base = declarative_base()
engine = create_engine(DB_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# --- Enhanced ERP Table ---
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True)
    product_name = Column(String)
    quantity_ordered = Column(String)
    delivery_due_date = Column(String)
    retailer_name = Column(String)
    retailer_email = Column(String)
    retailer_address = Column(String)
    client_email_subject = Column(String)

Base.metadata.create_all(engine)

def add_order(details, subject):
    """Insert extracted order data into database"""
    try:
        order = PurchaseOrder(
            product_name=details.get("product"),
            quantity_ordered=details.get("quantity"),
            delivery_due_date=details.get("due_date"),
            retailer_name=details.get("retailer_name"),
            retailer_email=details.get("retailer_email"),
            retailer_address=details.get("retailer_address"),
            client_email_subject=subject
        )

        print(f"🧾 Saving order: {order.product_name}, {order.quantity_ordered}, {order.delivery_due_date}")
        session.add(order)
        session.commit()
        print("✅ Order saved successfully!\n")
    except SQLAlchemyError as e:
        session.rollback()
        print("❌ Database error:", e)
