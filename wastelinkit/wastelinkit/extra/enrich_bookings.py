from pymongo import MongoClient
from bson import ObjectId

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["waste_db"]

bookings_col = db["bookings"]
users_col = db["users"]
waste_listings_col = db["waste_listings"]

for booking in bookings_col.find():
    update_fields = {}

    # Get waste listing
    waste = waste_listings_col.find_one({"_id": booking.get("waste_id")})
    if waste:
        update_fields["plastic_type"] = waste.get("plastic_type", "Unknown")
        update_fields["month"] = waste.get("month", "Unknown")
    else:
        print(f"[!] Waste not found for booking {booking['_id']}")

    # Get buyer info
    try:
        buyer_obj_id = ObjectId(booking["buyer_id"])
        user = users_col.find_one({"_id": buyer_obj_id})
        if user:
            update_fields["buyer_email"] = user.get("email", "Unknown")
        else:
            print(f"[!] Buyer not found for booking {booking['_id']}")
    except Exception as e:
        print(f"[!] Invalid buyer_id in booking {booking['_id']}: {e}")

    # Apply update
    if update_fields:
        bookings_col.update_one(
            {"_id": booking["_id"]},
            {"$set": update_fields}
        )
        print(f"[+] Updated booking {booking['_id']} with {update_fields}")
    else:
        print(f"[-] No update fields found for booking {booking['_id']}")
