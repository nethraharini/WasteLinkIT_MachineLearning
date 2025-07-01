from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

app = Flask(__name__)

# Flask app configuration
app.secret_key = 'your_secret_key'

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["waste_db"]
collection = db["predictions"]
waste_listings_collection = db["waste_listings"]
bookings_collection = db["bookings"]
users_collection = db["users"]

# Helper Functions
def find_user_by_email(email):
    return users_collection.find_one({"email": email})

def update_user_password(email, new_password):
    hashed_pw = generate_password_hash(new_password)
    users_collection.update_one({"email": email}, {"$set": {"password": hashed_pw}})

# Fetch profile data for the logged-in user
@app.route('/api/profile', methods=['GET'])
def get_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "name": user['name'],
        "email": user['email'],
        "phone": user['phone'],
        "organization": user.get('organization', ''),
        "address": user.get('address', '')
    })

# Update user profile
@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    data = request.json
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    updated_data = {
        "name": data.get("name"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "organization": data.get("organization", ""),
        "address": data.get("address", "")
    }

    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updated_data})

    return jsonify({
        "message": "Profile updated successfully!",
        "updated_profile": updated_data
    }), 200

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

# Pre-booking page
@app.route("/prebook")
def prebook_page():
    return render_template('prebook.html')  # Render Pre-booking Form Page

# Instant Booking page
@app.route("/instant-book")
def instant_book_page():
    return render_template('instant_book.html')  # Render Instant Booking Page

# My Bookings page
@app.route("/my-bookings")
def my_bookings_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    # Fetch user's bookings from the database
    bookings = bookings_collection.find({"user_id": ObjectId(user_id)})
    return render_template('my_bookings2.html', bookings=bookings)  # Display bookings

# Track Logistics page
@app.route("/track-logistics")
def track_logistics_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    # Fetch user's logistics data from the database
    logistics = bookings_collection.find({"user_id": ObjectId(user_id), "status": "in_transit"})
    return render_template('track_logistics.html', logistics=logistics)  # Display logistics info

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        user_type = request.form.get('role')  # 'Producer' or 'Buyer'
        organization = request.form.get('organization')
        address = request.form.get('address')

        # Check if email already exists
        if db.users.find_one({'email': email}):
            flash('Email already registered. Please log in.', 'danger')
            return redirect(url_for('login'))

        # Check password match
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('signup'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Create the user document
        user = {
            'name': name,
            'email': email,
            'phone': phone,
            'password': hashed_password,
            'role': user_type,
            'organization': organization,
            'address': address
        }

        # Insert into MongoDB
        db.users.insert_one(user)

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup1.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if email exists in the database
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            session['name'] = user['name']

            flash('Login successful!', 'success')
            if user['role'] == 'Producer':
                return redirect(url_for('producer_dashboard'))
            else:
                return redirect(url_for('buyer_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login1.html')

# Logout route
@app.route("/logout")
def logout():
    session.clear()  # Clear the session
    return redirect(url_for("home"))

@app.route('/producer-dashboard')
def producer_dashboard():
    return render_template('producer_dashboard.html')

@app.route('/buyer-dashboard')
def buyer_dashboard():
    return render_template('buyer_dashboard2.html')

if __name__ == "__main__":
    app.run(debug=True)
