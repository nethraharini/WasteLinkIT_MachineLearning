import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# Step 1: Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")  # Adjust if hosted elsewhere
db = client["waste_db"]  # Database name
collection = db["predictions"]  # Collection name

# Step 2: Read the CSV
df = pd.read_csv(r'C:\Users\nethr\Downloads\wastelinkit\wastelinkit\predicted_plastic_waste_Jan_June_2025.csv')

# Step 3: Convert Month to datetime format
df["Month"] = pd.to_datetime(df["Month"])

# Step 4: Convert each row to a dictionary
records = df.to_dict(orient="records")

# Optional: Clear existing predictions to avoid duplicates
collection.delete_many({})

# Step 5: Insert records into MongoDB
collection.insert_many(records)

print(f"✅ Inserted {len(records)} records into MongoDB.")
