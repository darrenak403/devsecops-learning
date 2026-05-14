import sys
import os

# Ensure we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine
from app.core.config import settings

url = settings.database_url

if not url:
    print("Error: DATABASE_URL is not set in environment or .env file")
    sys.exit(1)

try:
    engine = create_engine(url)
    connection = engine.connect()
    print("Success: Database connection to Supabase established!")
    connection.close()
except Exception as e:
    print(f"Error: Connection failed: {e}")