from app.database import Base, engine
from app import models
import sqlite3

# Create any missing database tables
Base.metadata.create_all(bind=engine)

# Verify tables
conn = sqlite3.connect("lyftr.db")
cursor = conn.cursor()

cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
)

print("Database tables:", cursor.fetchall())

conn.close()