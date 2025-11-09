import os

# Path for database file (always in main project folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'orders.db')}"

EMAIL_USER="pythonprojectimap@gmail.com"
EMAIL_PASS="wfim pnhj axpq apya"

