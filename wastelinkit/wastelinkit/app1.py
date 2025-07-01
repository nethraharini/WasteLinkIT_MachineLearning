from flask import Flask,jsonify, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from flask_mail import Mail, Message
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer
from bson import ObjectId
app = Flask(__name__)

# Flask app configuration
app.secret_key = 'your_secret_key'

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["waste_db"]
collection = db["predictions"]
waste_listings_collection = db["waste_listings"]
users_collection = db["users"]
prebookings_collection=db["prebookings"]
instant_bookings_collections=db["instant_bookings"]

# Token serializer
serializer = URLSafeTimedSerializer(app.secret_key)



# Flask mail configuration (for email notifications)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'csowm0574@gmail.com'
app.config['MAIL_PASSWORD'] = 'nptv umtw oypj mlxq'
app.config['MAIL_DEFAULT_SENDER'] = 'csowm0574@gmail.com'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)


def find_user_by_email(email):
    return users_collection.find_one({"email": email})

def update_user_password(email, new_password):
    hashed_pw = generate_password_hash(new_password)
    users_collection.update_one({"email": email}, {"$set": {"password": hashed_pw}})

def send_reset_email(to_email, reset_link):
    msg = Message("Password Reset Request - Plastic Waste Platform", recipients=[to_email])
    msg.body = f"Click the link below to reset your password:\n{reset_link}"
    try:
        mail.send(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")  # This will give you more info about the failure
        raise  # Reraise the exception to stop the function if it fails

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

        # Additional fields based on user type
        waste_types = request.form.getlist('waste_types') if user_type == 'Producer' else []
        estimated_waste = request.form.get('estimated_waste') if user_type == 'Producer' else ''
        production_facility_address = request.form.get('production_facility_address') if user_type == 'Producer' else ''
        license_registration_id = request.form.get('license_registration_id') if user_type == 'Producer' else ''

        interested_waste_types = request.form.getlist('interested_waste_types') if user_type == 'Buyer' else []
        preferred_quantity_range = request.form.get('preferred_quantity_range') if user_type == 'Buyer' else ''
        usage_purpose = request.form.get('usage_purpose') if user_type == 'Buyer' else ''

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
            'address': address,
            'waste_types': waste_types,
            'estimated_waste': estimated_waste,
            'production_facility_address': production_facility_address,
            'license_registration_id': license_registration_id,
            'interested_waste_types': interested_waste_types,
            'preferred_quantity_range': preferred_quantity_range,
            'usage_purpose': usage_purpose
        }

        # Insert into MongoDB
        db.users.insert_one(user)

        # Send confirmation email
        msg = Message('Welcome to Waste Trading Platform!', recipients=[email])
        msg.body = f"Hello {name},\n\nThank you for signing up as a {user_type}. Your registration is successful!"
        try:
            mail.send(msg)
        except:
            flash('Error sending email confirmation. Please try again later.', 'danger')

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
        
        
        if user:
            # Verify the password
            if check_password_hash(user['password'], password):
                # Successful login: Store user information in session
                session['user_id'] = str(user['_id'])
                session['email'] = user['email']
                session['role'] = user['role']
                session['name'] = user['name']  # assuming user['name'] contains the full name

                
                flash('Login successful!', 'success')
                
                # Redirect based on user role
                if user['role'] == 'Producer':
                    return redirect(url_for('producer_dashboard'))  # Make sure you define the producer_dashboard route
                else:
                    return redirect(url_for('buyer_dashboard'))  # Define buyer_dashboard route if needed
            else:
                flash('Invalid password. Please try again.', 'danger')
        else:
            flash('Email not registered. Please sign up.', 'danger')
        
        return redirect(url_for('login'))
    
    return render_template('login1.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = find_user_by_email(email)
        if user:
            token = serializer.dumps(email, salt='password-reset')  # Consistent salt here
            reset_link = url_for('reset_password', token=token, _external=True)
            send_reset_email(email, reset_link)
            flash('Password reset link has been sent to your email. Please check your inbox.')  # Redirect to a page indicating email was sent.
    return render_template('forgot_password.html')



@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=86400)  # Fixed salt here
    except:
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm_password']
        if password == confirm:
            update_user_password(email, password)
            flash('Your password has been updated successfully.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match.', 'danger')

    return render_template('reset_password.html', token=token)

# Logout route
@app.route("/logout")
def logout():
    session.clear()  # Clear the session
    return redirect(url_for("home"))



@app.route('/producer_dashboard')
def producer_dashboard():
    user_id = session.get('user_id')
    role = session.get('role')

    if not user_id or role != 'Producer':
        flash('Unauthorized access. Please log in as a producer.', 'danger')
        return redirect(url_for('login'))

    user = users_collection.find_one({'_id': ObjectId(user_id)})

    if not user or user.get('role') != 'Producer':
        flash('User not authorized as producer.', 'danger')
        return redirect(url_for('login'))

    return render_template('producer_dashboard1.html', user=user)

@app.route('/producer/edit_profile', methods=['GET', 'POST'])
def edit_producer_profile():
    if 'user_id' not in session or session.get('role') != 'Producer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})

    if request.method == 'POST':
        updated_data = {
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'organization': request.form['organization'],
            'address': request.form['address'],
            'production_facility_address': request.form['production_facility_address'],
            'license_registration_id': request.form['license_registration_id'],
            'waste_types': request.form.getlist('waste_types')
        }

        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': updated_data})
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('producer_dashboard'))

    return render_template('edit_producer_profile.html', user=user)


@app.route('/producer/list_estimated_waste', methods=['GET', 'POST'])
def list_estimated_waste():
    if 'user_id' not in session or session.get('role') != 'Producer':
        flash('Unauthorized access. Please log in as a producer.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        plastic_type = request.form.get('plastic_type')
        quantity = request.form.get('quantity', type=float)
        district = request.form.get('district')
        month = request.form.get('month')

        # Basic validation to prevent errors
        if not all([plastic_type, quantity is not None, district, month]):
            flash('Please fill in all the fields correctly.', 'danger')
            return redirect(url_for('list_estimated_waste'))

        estimated_waste = {
            'producer_id': session['user_id'],
            'plastic_type': plastic_type,
            'quantity': quantity,
            'district': district,
            'month': month,
            'status': 'estimated',
            'timestamp': datetime.utcnow()
        }

        db.waste_listings.insert_one(estimated_waste)
        flash('Estimated waste listed successfully!', 'success')
        return redirect(url_for('producer_dashboard'))

    current_month = datetime.utcnow().strftime("%Y-%m")
    return render_template('list_estimated_waste1.html', current_month=current_month)

@app.route('/producer/list_confirm_waste', methods=['GET', 'POST'])
def list_confirm_waste():
    if 'user_id' not in session or session.get('role') != 'Producer':
        flash('Unauthorized access. Please log in as a producer.', 'danger')
        return redirect(url_for('login'))

    producer_id = session['user_id']

    if request.method == 'POST':
        estimate_id = request.form.get('estimate_id')
        confirmed_quantity_str = request.form.get('confirmed_quantity')

        if not estimate_id or not confirmed_quantity_str:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('list_confirm_waste'))

        try:
            confirmed_quantity = float(confirmed_quantity_str)
        except ValueError:
            flash('Invalid quantity. Please enter a valid number.', 'danger')
            return redirect(url_for('list_confirm_waste'))

        # Get the estimated waste entry
        estimated = db.waste_listings.find_one({
            '_id': ObjectId(estimate_id),
            'producer_id': producer_id,
            'status': 'estimated'
        })

        if not estimated:
            flash('Estimated listing not found.', 'danger')
            return redirect(url_for('list_confirm_waste'))

        # Update status to confirmed
        db.waste_listings.update_one(
            {'_id': ObjectId(estimate_id)},
            {'$set': {
                'quantity': confirmed_quantity,
                'status': 'confirmed',
                'confirmed_timestamp': datetime.utcnow()
            }}
        )

        plastic_type = estimated['plastic_type']
        district = estimated['district']
        month = estimated['month']
        quantity = confirmed_quantity

        # 🔄 Fetch all matching prebookings for this producer, type, month, district
        matching_bookings = list(db.prebookings.find({
            'producer_id': producer_id,
            'waste_type': plastic_type,
            'status': 'confirmed'
        }).sort('timestamp', 1))  # Oldest first

        for booking in matching_bookings:
            buyer = db.users.find_one({'_id': ObjectId(booking['buyer_id'])})
            if not buyer:
                continue

            booked_quantity = float(booking['quantity'])
            if booked_quantity <= quantity:
                # ✅ Enough quantity – confirm
                db.prebookings.update_one(
                    {'_id': booking['_id']},
                    {'$set': {'status': 'confirmed'}}
                )
                send_email(
                    subject="Pre-Booked Waste Confirmed",
                    recipient=buyer['email'],
                    body=f"Your pre-booked {booked_quantity} tons of {plastic_type} waste in {district} for {month} is now confirmed."
                )
                quantity -= booked_quantity
            else:
                # ❌ Not enough quantity – notify shortage
                db.prebookings.update_one(
                    {'_id': booking['_id']},
                    {'$set': {'status': 'shortage'}}
                )
                send_email(
                    subject="Pre-Booking Shortage Alert",
                    recipient=buyer['email'],
                    body=f"Unfortunately, your pre-booking of {booked_quantity} tons of {plastic_type} waste in {district} for {month} could not be fully fulfilled due to shortage."
                )

        flash('Waste quantity confirmed and buyers notified.', 'success')
        return redirect(url_for('producer_dashboard'))

    # GET request: show unconfirmed listings
    estimates = db.waste_listings.find({'producer_id': producer_id, 'status': 'estimated'})
    return render_template('list_confirm_waste.html', estimates=estimates)



@app.route('/producer/view_history')
def producer_view_history():
    if 'user_id' not in session or session.get('role') != 'Producer':
        flash('Unauthorized access. Please log in as a producer.', 'danger')
        return redirect(url_for('login'))

    producer_id = session['user_id']
    history = list(db.waste_listings.find({'producer_id': producer_id}).sort('timestamp', -1))  # Most recent first

    return render_template('producer_view_history.html', history=history)



@app.route('/producer/fill_logistics', methods=['GET', 'POST'])
def fill_logistics():
    if 'user_id' not in session or session.get('role') != 'Producer':
        flash('Unauthorized access. Please log in as a producer.', 'danger')
        return redirect(url_for('login'))

    producer_id = session['user_id']
    bookings = []
    selected_booking = None

    for col in [db.prebookings, db.instant_bookings]:
        bookings += list(col.find({
            'producer_id': producer_id,
            'status': {'$in': ['confirmed', 'in_transit']}
        }))

    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        delivery_date = request.form.get('delivery_date')
        logistics_notes = request.form.get('logistics_notes')
        status = request.form.get('status')

        if not booking_id:
            flash('Please select a booking.', 'danger')
            return render_template('fill_logistics.html', bookings=bookings)

        # Determine collection
        collection = None
        for col in [db.prebookings, db.instant_bookings]:
            booking = col.find_one({'_id': ObjectId(booking_id), 'producer_id': producer_id})
            if booking:
                collection = col
                selected_booking = booking
                break

        if 'status' in request.form and all([delivery_date, logistics_notes, status]):
            # Full form submitted: update logistics
            collection.update_one(
                {'_id': ObjectId(booking_id)},
                {'$set': {
                    'delivery_date': delivery_date,
                    'logistics_notes': logistics_notes,
                    'status': status,
                    'logistics_filled_timestamp': datetime.utcnow()
                }}
            )
            flash(f'Logistics updated and status set to "{status}".', 'success')
            return redirect(url_for('producer_dashboard'))

        elif booking_id:
            # Only booking selected, not full form yet
            return render_template('fill_logistics.html', bookings=bookings, selected_booking=selected_booking)

        flash('Please fill in all fields.', 'danger')
        return render_template('fill_logistics.html', bookings=bookings, selected_booking=selected_booking)

    return render_template('fill_logistics.html', bookings=bookings)



@app.route('/buyer/dashboard')
def buyer_dashboard():
    user_id = session.get('user_id')
    role = session.get('role')

    if not user_id or role != 'Buyer':
        flash('Unauthorized access. Please log in as a buyer.', 'danger')
        return redirect(url_for('login'))

    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user or user.get('role', '') != 'Buyer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    
    return render_template('buyer_dashboard1.html', user=user)

@app.route('/buyer/edit_profile', methods=['GET', 'POST'])
def edit_buyer_profile():
    if 'user_id' not in session or session.get('role') != 'Buyer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})

    if request.method == 'POST':
        updated_data = {
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'organization': request.form['organization'],
            'address': request.form['address'],
            'interested_waste_types': request.form.getlist('interested_waste_types'),
            'preferred_quantity_range': request.form['preferred_quantity_range'],
            'usage_purpose': request.form['usage_purpose']
        }

        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': updated_data})
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('buyer_dashboard'))

    return render_template('edit_buyer_profile.html', user=user)


@app.route('/show_available_waste')
def show_available_waste():
    if 'user_id' not in session:
        flash("Login first", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    listings = []
    all_listings = db.waste_listings.find({'status': 'estimated'})

    # Fetch all prebookings to calculate remaining quantity per listing
    all_prebookings = db.prebookings.find()
    booking_map = {}  # key: (producer_id, waste_type), value: total booked

    for booking in all_prebookings:
        key = (booking['producer_id'], booking['waste_type'])
        booking_map[key] = booking_map.get(key, 0) + float(booking['quantity'])

    # Prebooked listings by this buyer
    my_prebooked = db.prebookings.find({'buyer_id': user_id})
    my_prebooked_set = {(p['producer_id'], p['waste_type']) for p in my_prebooked}

    # In the backend route
    for listing in all_listings:
        producer_id = listing.get('producer_id')
        waste_type = listing['plastic_type']
        estimated = float(listing.get('quantity', 0))
        key = (producer_id, waste_type)
        booked = booking_map.get(key, 0)
        remaining = estimated - booked

        # Find producer details
        producer = db.users.find_one({'_id': ObjectId(producer_id)})
        if not producer:
            continue  # ⛔ Skip this listing if the producer doesn't exist

        listings.append({
            'producer_id': producer_id,
            'organization': producer.get('organization', 'Unknown'),
            'waste_type': waste_type,
            'estimated_waste': remaining,
            'district': listing.get('district', 'N/A'),
            'month': listing.get('month', 'N/A'),
            'address': producer.get('address', 'N/A'),
            'facility_address': producer.get('production_facility_address', 'N/A'),
            'license_id': producer.get('license_registration_id', 'N/A'),
            'prebooked': (producer_id, waste_type) in my_prebooked_set,
            'fully_prebooked': remaining == 0
        })

    return render_template('show_available_waste.html', listings=listings)

        

@app.route('/prebook', methods=['POST'])
def prebook_waste():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    name=session['name']
    email=session['email']
    delivery_address=request.form['address']
    producer_id = request.form['producer_id']
    waste_type = request.form['waste_type']
    

    try:
        quantity = float(request.form['quantity'])
    except ValueError:
        flash('Invalid quantity entered.', 'danger')
        return redirect(url_for('show_available_waste'))

    # Check if the requested quantity is within available estimate
    listing = db.waste_listings.find_one({
        'producer_id': producer_id,
        'plastic_type': waste_type,
        'status': 'estimated'
    })

    if not listing:
        flash('Waste listing not found.', 'danger')
        return redirect(url_for('show_available_waste'))

    if quantity > float(listing['quantity']):
        flash('Requested quantity exceeds available estimate.', 'danger')
        return redirect(url_for('show_available_waste'))

    # Record the prebooking
    db.prebookings.insert_one({
        'buyer_id': user_id,
        'producer_id': producer_id,
        'waste_type': waste_type,
        'quantity': quantity,
        'delivery_address': delivery_address,
        'status': 'confirmed'
    })

    # Send confirmation email to buyer
    buyer_email = session.get('email')
    send_email(
        subject="Pre-Booking Confirmation",
        recipient=buyer_email,
        body=f"Your pre-booking for {quantity} tons of {waste_type} waste has been confirmed. Delivery Address: {delivery_address}."
    )

    # Send email to producer
    producer = db.users.find_one({'_id': ObjectId(producer_id)})
    producer_email = producer.get('email')
    send_email(
        subject="New Pre-Booking",
        recipient=producer_email,
        body=f" {name} , {email} has pre-booked {quantity} tons of {waste_type} waste. Delivery Address: {delivery_address}."
    )
    flash(f'Successfully pre-booked {quantity} units of {waste_type}.', 'success')
    return redirect(url_for('show_available_waste'))

    
@app.route('/cancel_prebook', methods=['POST'])
def cancel_prebook():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    name=session['name']
    waste_type = request.form['waste_type']
    producer_id = request.form['producer_id']

    result = db.prebookings.delete_one({
        'buyer_id': user_id,
        'producer_id': producer_id,
        'waste_type': waste_type
    })

    if result.deleted_count:
                # Send email to buyer
        buyer_email = session.get('email')
        send_email(
            subject="Pre-Booking Cancellation",
            recipient=buyer_email,
            body=f"Your pre-booking for {waste_type} waste with producer {producer_id} has been canceled."
        )

        # Send email to producer
        producer = db.users.find_one({'_id': ObjectId(producer_id)})
        producer_email = producer.get('email')
        send_email(
            subject="Pre-Booking Canceled",
            recipient=producer_email,
            body=f"A pre-booking for {waste_type} waste has been canceled by {name}."
        )

        flash('Prebooking cancelled.', 'success')
    else:
        flash('No matching prebooking found.', 'warning')

    return redirect(url_for('show_available_waste'))



@app.route('/show_instant_booking')
def show_instant_booking():
    if 'user_id' not in session:
        flash('Login first', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    listings = []

    confirmed_listings = db.waste_listings.find({'status': 'confirmed'})
    prebookings = list(db.prebookings.find())
    instant_bookings = list(db.instant_bookings.find())
    my_instant = {(i['producer_id'], i['waste_type']): i for i in instant_bookings if i['buyer_id'] == user_id}

    # Calculate remaining confirmed waste
    for listing in confirmed_listings:
        
        producer_id = listing.get('producer_id', None) 
        waste_type = listing['plastic_type']
        confirmed_qty = float(listing.get('quantity', 0))

        prebooked_total = sum(float(p['quantity']) for p in prebookings
                              if p['producer_id'] == producer_id and p['waste_type'] == waste_type)

        instant_total = sum(float(i['quantity']) for i in instant_bookings
                            if i['producer_id'] == producer_id and i['waste_type'] == waste_type)

        remaining = confirmed_qty - prebooked_total - instant_total

        if remaining > 0 or (producer_id, waste_type) in my_instant:
            producer = db.users.find_one({'_id': ObjectId(producer_id)})

            # Check if producer exists
            if producer:
                listings.append({
                    'producer_id': producer_id,
                    'organization': producer.get('organization', 'Unknown'),
                    'waste_type': waste_type,
                    'remaining': remaining,
                    'district': listing.get('district', 'N/A'),  # ✅ added
                    'month': listing.get('month', 'N/A'),   
                    'address': producer.get('address', 'N/A'),
                    'facility_address': producer.get('production_facility_address', 'N/A'),
                    'license_id': producer.get('license_registration_id', 'N/A'),
                    'already_booked': (producer_id, waste_type) in my_instant,
                    'booked_quantity': my_instant.get((producer_id, waste_type), {}).get('quantity')
                })
            else:
                # If no producer found, log or handle it
                print(f"No producer found for producer_id: {producer_id}")

    return render_template('show_instant_booking.html', listings=listings)



@app.route('/instant_book', methods=['POST'])
def instant_book():
    if 'user_id' not in session:
        flash('Please log in to book.', 'danger')
        return redirect(url_for('login'))

    buyer_id = session['user_id']
    name=session['name']
    email=session['email']
    producer_id = request.form.get('producer_id')
    waste_type = request.form.get('waste_type')
    delivery_address=request.form.get('address')
    quantity = float(request.form.get('quantity'))

    # Fetch the confirmed listing
    listing = db.waste_listings.find_one({
        'producer_id': producer_id,
        'plastic_type': waste_type,
        'status': 'confirmed'
    })

    if not listing:
        flash('Confirmed waste listing not found.', 'danger')
        return redirect(url_for('show_instant_booking'))

    confirmed_qty = float(listing.get('quantity', 0))

    # Calculate already booked quantity (prebooked + instant)
    prebooked_total = sum(
        float(p['quantity']) for p in db.prebookings.find({
            'producer_id': producer_id,
            'waste_type': waste_type
        })
    )

    instant_total = sum(
        float(i['quantity']) for i in db.instant_bookings.find({
            'producer_id': producer_id,
            'waste_type': waste_type
        })
    )

    remaining = confirmed_qty - prebooked_total - instant_total

    if quantity > remaining:
        flash(f"Only {remaining} tons left for instant booking.", "warning")
        return redirect(url_for('show_instant_booking'))

    # Insert instant booking
    db.instant_bookings.insert_one({
        'buyer_id': buyer_id,
        'producer_id': producer_id,
        'waste_type': waste_type,
        'quantity': quantity,
        'delivery_address': delivery_address,
        'status': 'confirmed',
        'timestamp': datetime.utcnow()
    })

    # Send email to buyer
    buyer_email = session.get('email')
    send_email(
        subject="Instant Booking Confirmation",
        recipient=buyer_email,
        body=f"Your instant booking for {quantity} tons of {waste_type} waste has been confirmed."
    )

    # Send email to producer
    producer = db.users.find_one({'_id': ObjectId(producer_id)})
    
    producer_email = producer.get('email')
    send_email(
        subject="New Instant Booking",
        recipient=producer_email,
        body=f" {name} , {email} has pre-booked {quantity} tons of {waste_type} waste. Delivery Address: {delivery_address}."
    )


    flash(f"Successfully booked {quantity} tons of {waste_type}.", "success")
    return redirect(url_for('show_instant_booking'))

@app.route('/cancel_instant_booking', methods=['POST'])
def cancel_instant_booking():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    buyer_id = session['user_id']
    name=session['name']
    producer_id = request.form.get('producer_id')
    producer_organisation=request.form.get('organisation')
    waste_type = request.form.get('waste_type')

    result = db.instant_bookings.delete_one({
        'buyer_id': buyer_id,
        'producer_id': producer_id,
        'waste_type': waste_type
    })

    if result.deleted_count:
                # Send email to buyer
        buyer_email = session.get('email')
        send_email(
            subject="Instant Booking Cancellation",
            recipient=buyer_email,
            body=f"Your instant booking for {waste_type} waste with producer {producer_organisation} has been canceled."
        )

        # Send email to producer
        producer = db.users.find_one({'_id': ObjectId(producer_id)})
        producer_email = producer.get('email')
        send_email(
            subject="Instant Booking Canceled",
            recipient=producer_email,
            body=f"An instant booking for {waste_type} waste has been canceled by the {name}."
        )

        flash('Instant booking canceled successfully.', 'success')
    else:
        flash('Could not cancel booking.', 'warning')

    return redirect(url_for('show_instant_booking'))


@app.route('/booking_history')
def booking_history():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    buyer_id = session['user_id']

    # Fetch prebookings
    prebookings = list(db.prebookings.find({'buyer_id': buyer_id}))
    for pb in prebookings:
        producer = db.users.find_one({'_id': ObjectId(pb['producer_id'])})
        pb['organization'] = producer.get('organization', 'Unknown')
        pb['type'] = 'Pre-booking'
        pb['timestamp'] = pb.get('timestamp', None)

    # Fetch instant bookings
    instant_bookings = list(db.instant_bookings.find({'buyer_id': buyer_id}))
    for ib in instant_bookings:
        producer = db.users.find_one({'_id': ObjectId(ib['producer_id'])})
        ib['organization'] = producer.get('organization', 'Unknown')
        ib['type'] = 'Instant Booking'
        ib['timestamp'] = ib.get('timestamp', None)

    all_bookings = prebookings + instant_bookings

    # Sort by most recent booking
    all_bookings.sort(
    key=lambda x: x['timestamp'] if x.get('timestamp') else datetime.min,
    reverse=True
)
    return render_template('booking_history.html', bookings=all_bookings)



@app.route('/buyer/track_logistics')
def track_logistics():
    if 'user_id' not in session or session.get('role') != 'Buyer':
        flash('Unauthorized access. Please log in as a buyer.', 'danger')
        return redirect(url_for('login'))

    buyer_id = session['user_id']

    # Fetch prebookings and instant bookings that are either in transit or delivered
    bookings = []

    # Fetching from prebookings collection
    prebookings = db.prebookings.find({
        'buyer_id': buyer_id,
        'status': {'$in': ['in_transit', 'delivered']}  # Get prebookings that are in transit or delivered
    })
    
    # Fetching from instant_bookings collection
    instant_bookings = db.instant_bookings.find({
        'buyer_id': buyer_id,
        'status': {'$in': ['in_transit', 'delivered']}  # Get instant bookings that are in transit or delivered
    })
    
    # Combine both prebookings and instant_bookings
    bookings.extend(prebookings)
    bookings.extend(instant_bookings)

    for booking in bookings:
        # Fetch the producer information for the booking
        producer = db.users.find_one({'_id': ObjectId(booking['producer_id'])})
        
        # Add the producer's details to the booking dictionary
        booking['producer_name'] = producer.get('name', 'Unknown')  # Producer's name
        booking['producer_organization'] = producer.get('organization', 'Unknown')  # Producer's organization
        booking['producer_address'] = producer.get('production_facility_address', 'Unknown')  # Producer's address
         # Add the delivery address to the booking
        booking['delivery_address'] = booking.get('delivery_address', 'Not Provided')  # Delivery address

    return render_template('track_logistics.html', bookings=bookings)


@app.route('/mark_as_delivered/<booking_id>', methods=['POST'])
def mark_as_delivered(booking_id):
    # Try updating in the instant_bookings collection first
    result = db.instant_bookings.update_one(
        {'_id': ObjectId(booking_id)},  # Find the specific booking by ID
        {'$set': {'status': 'delivered'}}  # Update the status to 'delivered'
    )
    
    # If not found in instant_bookings, check prebookings collection
    if result.modified_count == 0:
        result = db.prebookings.update_one(
            {'_id': ObjectId(booking_id)},  # Find the specific booking by ID in prebookings
            {'$set': {'status': 'delivered'}}  # Update the status to 'delivered'
        )
    
    # Check if the update was successful
    if result.modified_count > 0:
        flash('Booking marked as delivered!', 'success')
    else:
        flash('Failed to update the status. Booking not found or already delivered.', 'danger')
    
    return redirect(url_for('track_logistics'))


if __name__ == '__main__':
    app.run(debug=True)
