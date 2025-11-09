# erp/models.py
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DB_URL

# --- Database setup ---
Base = declarative_base()
engine = create_engine(DB_URL, echo=True)  # echo=True logs SQL commands in terminal
Session = sessionmaker(bind=engine)
session = Session()

# --- Order Table Definition ---
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    product = Column(String)
    quantity = Column(String)
    due_date = Column(String)
    email_subject = Column(String)

# --- Create the database table if not exists ---
Base.metadata.create_all(engine)

# --- Function to Add New Orders ---
def add_order(details, subject):
    from sqlalchemy.exc import SQLAlchemyError

    try:
        order = Order(
            product=details.get("product"),
            quantity=details.get("quantity"),
            due_date=details.get("due_date"),
            email_subject=subject
        )

        # Debug print — to verify data is being saved
        print("🧾 Adding Order:", order.product, order.quantity, order.due_date)

        session.add(order)
        session.commit()
        print("✅ Order saved successfully!\n")
    except SQLAlchemyError as e:
        session.rollback()
        print("❌ Database Error:", e)
