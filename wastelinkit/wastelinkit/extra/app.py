from flask import Flask, jsonify, render_template, request, redirect, flash, url_for, session
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime, timezone
import os
from flask_mail import Mail, Message

app = Flask(__name__)
CORS(app)

# Secret key for session management (change to a random secret key in production)
app.secret_key = 'your_secret_key_here'

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["waste_db"]
collection = db["predictions"]

# New collection for producer availability
waste_listings_collection=db["waste_listings"]
# New collection for bookings
bookings_collection = db["bookings"]
# New collection for users (for login/signup)
users_collection = db["users"]


# Email config (Gmail SMTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'csowm0574@gmail.com'
app.config['MAIL_PASSWORD'] = 'nptv umtw oypj mlxq'
app.config['MAIL_DEFAULT_SENDER'] = 'csowm0574@gmail.com'

mail = Mail(app)

def send_email(subject, recipient, body):
    try:
        msg = Message(subject=subject, recipients=[recipient])
        msg.body = body
        mail.send(msg)
        print(f"Email sent to {recipient}")
    except Exception as e:
        print(f"Error sending email to {recipient}: {str(e)}")

# Serve the homepage
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/prediction")
def show_prediction_page():
    return render_template("prediction.html")

@app.route("/api/predictions")
def get_predictions():
    data = []
    for doc in collection.find():
        month_raw = doc.get("Month")
        if isinstance(month_raw, str):
            try:
                dt = datetime.fromisoformat(month_raw)
            except:
                dt = datetime.strptime(month_raw, "%a, %d %b %Y %H:%M:%S GMT")
        else:
            dt = month_raw

        month_str = dt.strftime("%b %Y")

        data.append({
            "Month": month_str,
            "District": doc.get("District", ""),
            "PET_Tons": float(doc.get("PET_Tons", 0)),
            "HDPE_Tons": float(doc.get("HDPE_Tons", 0)),
            "PVC_Tons": float(doc.get("PVC_Tons", 0)),
            "LDPE_Tons": float(doc.get("LDPE_Tons", 0)),
            "PP_Tons": float(doc.get("PP_Tons", 0)),
            "PS_Tons": float(doc.get("PS_Tons", 0)),
        })

    return jsonify(data)

#signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        # Check if email already exists
        if users_collection.find_one({'email': email}):
            flash('Email already registered. Please log in.')
            return redirect(url_for('login'))

        # Check password match
        if password != confirm_password:
            flash('Passwords do not match. Please try again.')
            return redirect(url_for('signup'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Create the user document
        user = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'role': role
        }

        # Insert into MongoDB
        users_collection.insert_one(user)

        flash('Account created successfully! Please log in.')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = users_collection.find_one({'email': email})

        if not user:
            flash('No account found with that email.')
            return redirect(url_for('login'))

        if not check_password_hash(user['password'], password):
            flash('Incorrect password.')
            return redirect(url_for('login'))

        # Login success: store safe session data (convert _id to str)
        session['user_id'] = str(user['_id'])
        session['email'] = user['email']
        session['name'] = user['name']
        session['role'] = user['role']

        flash('Login successful!')
        if user['role'] == 'producer':
            return redirect(url_for('producer_dashboard'))
        elif user['role'] == 'buyer':
            return redirect(url_for('buyer_dashboard'))
        else:
            return redirect(url_for('home'))


    return render_template('login.html')


# Logout route
@app.route("/logout")
def logout():
    session.clear()  # Clear the session
    return redirect(url_for("home"))

@app.route('/producer_dashboard')
def producer_dashboard():
    if 'user_id' not in session or session['role'] != 'producer':
        return redirect('/login')

    # fetch producer data if needed
    return render_template('producer_dashboard.html', email=session['email'])





@app.route('/producer/list_estimated_waste', methods=['GET', 'POST'])
def list_estimated_waste():
    if 'user_id' not in session or session['role'] != 'producer':
        return redirect('/login')

    if request.method == 'POST':
        plastic_type = request.form['plastic_type']
        quantity = int(request.form['quantity'])
        district = request.form['district']
        month = request.form['month']

        estimated_waste_entry = {
            "producer_email": session['email'],
            "plastic_type": plastic_type,
            "quantity": quantity,
            "district": district,
            "month": month,
            "status": "estimated"
        }

        db.waste_listings.insert_one(estimated_waste_entry)
        return "Estimated waste listed successfully!"

    return render_template('list_estimated_waste.html')


@app.route('/producer/list_confirmed_waste', methods=['GET', 'POST'])
def list_confirmed_waste():
    if 'user_id' not in session or session['role'] != 'producer':
        return redirect('/login')

    if request.method == 'POST':
        plastic_type = request.form['plastic_type']
        quantity = int(request.form['quantity'])
        district = request.form['district']
        month = request.form['month']
        producer_email = session['email']

        # Check if confirmed waste already exists for same producer/plastic/month/district
        existing = db.waste_listings.find_one({
            "producer_email": producer_email,
            "plastic_type": plastic_type,
            "district": district,
            "month": month,
            "status": "confirmed"
        })

        if existing:
            # Update the existing confirmed listing's quantity
            db.waste_listings.update_one(
                {"_id": existing["_id"]},
                {"$set": {"quantity": quantity}}
            )
            listing_id = existing["_id"]
        else:
            # Insert a new confirmed listing
            result = db.waste_listings.insert_one({
                "producer_email": producer_email,
                "plastic_type": plastic_type,
                "quantity": quantity,
                "district": district,
                "month": month,
                "status": "confirmed"
            })
            listing_id = result.inserted_id

        # Notify buyers whose pre-bookings match this confirmed listing
        matching_bookings = list(db.bookings.find({
            "waste_id": {"$exists": True},
            "status": "prebooked"
        }))

        for booking in matching_bookings:
            waste = db.waste_listings.find_one({"_id": booking["waste_id"]})
            if not waste:
                continue
            if (waste["producer_email"] == producer_email and
                waste["plastic_type"] == plastic_type and
                waste["district"] == district and
                waste["month"] == month):

                buyer = db.users.find_one({"_id": ObjectId(booking["buyer_id"])})
                if not buyer:
                    continue

                booked_quantity = booking["quantity"]
                if booked_quantity <= quantity:
                    # Confirm booking
                    db.bookings.update_one(
                        {"_id": booking["_id"]},
                        {"$set": {"status": "confirmed"}}
                    )
                    send_email(
                        subject="Pre-Booked Waste Confirmed",
                        recipient=buyer["email"],
                        body=f"Your pre-booked {booked_quantity} tons of {plastic_type} waste in {district} for {month} is now confirmed."
                    )
                    quantity -= booked_quantity  # Reduce available quantity
                else:
                    # Not enough confirmed quantity – notify shortage
                    db.bookings.update_one(
                        {"_id": booking["_id"]},
                        {"$set": {"status": "shortage"}}
                    )
                    send_email(
                        subject="Pre-Booking Shortage Alert",
                        recipient=buyer["email"],
                        body=f"Unfortunately, your pre-booked {booked_quantity} tons of {plastic_type} waste in {district} for {month} could not be fully fulfilled due to shortage."
                    )

        return "Confirmed waste listed and buyers notified."

    return render_template('list_confirmed_waste.html')


def list_confirmed_waste():
    producer_email = request.args.get("email")

    confirmed = bookings_collection.find({
        "producer_email": producer_email,
        "status": "confirmed"
    })

    result = []

    for entry in confirmed:
        logistics = entry.get("logistics", {})
        result.append({
            "plastic_type": entry["plastic_type"],
            "month": entry["month"],
            "quantity": entry["quantity"],
            "buyer_email": entry["buyer_email"],
            "logistics": {
                "pickup_address": logistics.get("pickup_address", "Not Set"),
                "delivery_address": logistics.get("delivery_address", "Not Set"),
                "pickup_date": logistics.get("pickup_date", "Not Set"),
                "status": logistics.get("status", "Not Set")
            }
        })

    return jsonify(result), 200

@app.route("/producer/update_logistics", methods=["GET", "POST"])
def update_logistics():
    if request.method == "GET":
        producer_email = session.get("email")

        # Step 1: Get waste listings by this producer
        listings = list(waste_listings_collection.find({"producer_email": producer_email}))
        waste_ids = [listing["_id"] for listing in listings]

        # Step 2: Find confirmed bookings related to these listings
        confirmed = list(bookings_collection.find({
            "waste_id": {"$in": waste_ids},
            "status": "confirmed"
        }))

        booking_details = []
        for b in confirmed:
            booking_details.append({
                "_id": str(b["_id"]),
                "plastic_type": b.get("plastic_type", "N/A"),
                "month": b.get("month", "N/A"),
                "quantity": b.get("quantity", "N/A"),
                "buyer_email": b.get("buyer_email", "N/A")
            })

        return render_template("update_logistics.html", booking_details=booking_details)


    # Existing POST logic remains unchanged
    data = request.get_json()
    booking_id = data.get("booking_id")
    logistics_info = data.get("logistics")

    if not booking_id or not logistics_info:
        return jsonify({"error": "booking_id and logistics data are required"}), 400

    try:
        result = bookings_collection.update_one(
            {"_id": ObjectId(booking_id), "status": "confirmed"},
            {"$set": {"logistics": logistics_info}}
        )
        if result.modified_count == 0:
            return jsonify({"message": "No matching confirmed booking found."}), 404

        return jsonify({"message": "Logistics updated successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Buyer Dashboard
@app.route('/buyer/dashboard')
def buyer_dashboard():
    if 'user_id' not in session or session.get('role') != 'buyer':
        return redirect('/login')

    buyer_email = session.get('email')
    
    bookings = list(bookings_collection.find({"buyer_email": buyer_email}))

    return render_template('buyer_dashboard.html', bookings=bookings)




@app.route('/buyer/prebook', methods=['GET', 'POST'])
def prebook_waste():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        waste_id = request.form['waste_id']
        quantity = int(request.form['quantity'])

        waste = db.waste_listings.find_one({'_id': ObjectId(waste_id)})
        if not waste:
            flash("Invalid waste listing selected.")
            return redirect('/buyer/prebook')

        db.bookings.insert_one({
            'buyer_id': session['user_id'],
            'waste_id': ObjectId(waste_id),
            'quantity': quantity,
            'status': 'prebooked',
            'booking_date': datetime.now(timezone.utc),
            'booking_type': 'prebooked'
        })

        db.waste_listings.update_one(
            {'_id': ObjectId(waste_id)},
            {'$inc': {'quantity': -quantity}}
        )

        buyer_email = session['email']
        producer_email = waste['producer_email']
        plastic_type = waste['plastic_type']
        district = waste['district']

        send_email(
            subject="Waste Pre-Booking Confirmed",
            recipient=buyer_email,
            body=f"Your pre-booking for {quantity} tons of {plastic_type} waste in {district} has been confirmed."
        )

        send_email(
            subject="New Waste Pre-Booking",
            recipient=producer_email,
            body=f"A buyer has pre-booked {quantity} tons of your {plastic_type} waste in {district}."
        )

        flash("Pre-booking successful!")
        return redirect('/buyer/prebook')

    # 👉 Handle GET request — fetch listings and existing bookings to show in the template
    listings = list(db.waste_listings.find({'quantity': {'$gt': 0}}))
    bookings = list(db.bookings.aggregate([
        {"$match": {"buyer_id": session['user_id']}},
        {"$lookup": {
            "from": "waste_listings",
            "localField": "waste_id",
            "foreignField": "_id",
            "as": "waste"
        }},
        {"$unwind": "$waste"},
        {"$project": {
            "plastic_type": "$waste.plastic_type",
            "district": "$waste.district",
            "month": "$waste.month",
            "waste_status": "$waste.status",
            "booking_type": 1,
            "quantity": 1,
            "booking_date": 1
        }}
    ]))

    return render_template('buyer_prebook.html', listings=listings, bookings=bookings)

@app.route('/buyer/my-bookings')
def my_bookings():
    if 'user_id' not in session or session.get('role') != 'buyer':
        return redirect('/login')

    # Fetch the buyer's bookings from the database
    buyer_email = session.get('email')
    bookings = list(db.bookings.find({"buyer_email": buyer_email}))

    

    # Organize and display detailed bookings
    detailed_bookings = []
    for booking in bookings:
    # Convert string booking_date to datetime if it's a string
        if isinstance(booking['booking_date'], str):
            # Convert string to datetime (adjust the format if needed)
            booking['booking_date'] = datetime.strptime(booking['booking_date'], "%Y-%m-%dT%H:%M:%S.%fZ")
    
        # Fetch the waste listing associated with this booking
        waste = db.waste_listings.find_one({'_id': booking['waste_id']})
    
        # If a matching waste listing is found, append the detailed booking
        if waste:
            detailed_bookings.append({
                'plastic_type': waste.get('plastic_type'),
                'district': waste.get('district'),
                'month': waste.get('month'),
                'waste_status': waste.get('status'),
                'booking_type': booking.get('status'),
                'quantity': booking.get('quantity'),
                'booking_date': booking['booking_date']
            })
    # Render the My Bookings page with the detailed bookings
    return render_template('my_bookings.html', bookings=detailed_bookings)


if __name__ == "__main__":
    app.run(debug=True)
