# erp/models.py
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Boolean, DateTime
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from config import DB_URL

Base = declarative_base()
engine = create_engine(DB_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()


# ---------------- ERP PURCHASE ORDER ----------------
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    # ---- Primary Key ----
    id = Column(Integer, primary_key=True)

    # ---- Order Identification ----
    order_number = Column(String, unique=True, index=True)
    order_date = Column(DateTime, default=datetime.utcnow)

    # ---- Order Details ----
    product_name = Column(String)
    quantity_ordered = Column(String)
    unit = Column(String)                  # pcs / kg / g / litre
    delivery_due_date = Column(String)

    # ---- Retailer Details ----
    retailer_name = Column(String)
    retailer_email = Column(String)
    retailer_address = Column(String)

    # ---- AI / NLP ----
    extracted_text = Column(String)         # raw email body
    confidence_score = Column(Float)
    priority_level = Column(String, default="Normal")

    # ---- Duplicate Control ----
    duplicate_flag = Column(Boolean, default=False)
    email_hash = Column(String, unique=True, index=True)

    # ---- ERP Control ----
    order_status = Column(String, default="Pending")   # Approved / Needs Review / Rejected
    source_of_order = Column(String, default="Email")
    remarks = Column(String)

    # ---- Audit ----
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, default=datetime.utcnow)

    # ---- Reference ----
    client_email_subject = Column(String)


Base.metadata.create_all(engine)


# ---------------- CENTRAL INSERT FUNCTION ----------------
def add_order(
    details: dict,
    subject: str,
    email_hash: str,
    order_status: str,
    confidence_score: float,
    priority_level: str,
    remarks: str = None
):
    try:
        order = PurchaseOrder(
            order_number=f"PO-{int(datetime.utcnow().timestamp())}",

            product_name=details.get("product"),
            quantity_ordered=details.get("quantity"),
            unit=details.get("unit"),
            delivery_due_date=details.get("due_date"),

            retailer_name=details.get("retailer_name"),
            retailer_email=details.get("retailer_email"),
            retailer_address=details.get("retailer_address"),

            extracted_text=details.get("raw_text"),

            confidence_score=confidence_score,
            priority_level=priority_level,
            duplicate_flag=False,
            email_hash=email_hash,

            order_status=order_status,
            source_of_order="Email",
            remarks=remarks,

            processed_at=datetime.utcnow(),
            client_email_subject=subject
        )

        session.add(order)
        session.commit()
        print("✅ ERP Order Saved Successfully")

    except SQLAlchemyError as e:
        session.rollback()
        print("❌ Database Error:", e)
