from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["waste_db"]
bookings_col = db["bookings"]

for booking in bookings_col.find():
    if booking.get("prebooked"):
        booking_type = "prebooked"
    else:
        booking_type = "instant-booked"

    # Update booking_type in the document
    bookings_col.update_one(
        {"_id": booking["_id"]},
        {"$set": {"booking_type": booking_type}}
    )
    print(f"[+] Updated booking {booking['_id']} with booking_type: {booking_type}")
