import uuid
import os
from flask import Flask, jsonify, request, session, make_response
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)

# Set the secret key to enable session management (cookies)
app.secret_key = os.urandom(24)  # Secure random key for session encryption

# Enable CORS with credentials to allow session cookies to be sent
CORS(app, supports_credentials=True)  # This ensures cookies can be sent cross-domain

# MongoDB connection setup
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

# Session configurations to ensure persistence across requests
app.config.update(
    SESSION_COOKIE_NAME='session_id',  # Name of the session cookie
    SESSION_COOKIE_HTTPONLY=True,  # Make the cookie accessible only to the server
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),  # Session expiry
    SESSION_COOKIE_DOMAIN='.localhost',  # Domain for cross-subdomain cookies
    SESSION_COOKIE_SAMESITE='None',  # Allow cross-origin requests
    SESSION_COOKIE_SECURE=False  # Disable secure flag for localhost (set to True for HTTPS)
)

# Ensure that each user has a session ID stored in cookies
def get_session_id():
    if 'session_id' not in session:
        session.permanent = True  # Make session permanent (so it doesn't expire on browser close)
        session['session_id'] = str(uuid.uuid4())  # Create a new session ID if it doesn't exist
    return session['session_id']

# Function to handle session expiration and automatic unlocking
def unlock_expired_houses():
    try:
        # Fetch all houses that are locked
        locked_houses = mongo.db.houses.find({"locked": {"$ne": None}})
        
        # Define lock timeout period (e.g., 2 minutes)
        lock_timeout = timedelta(minutes=2)  # Lock expires after 2 minutes

        # Iterate through each locked house
        for house in locked_houses:
            locked_at = house.get('locked_at')
            if locked_at and (datetime.utcnow() - locked_at) > lock_timeout:
                # Unlock the house if the lock time has expired
                mongo.db.houses.update_one(
                    {"house_id": house['house_id']},
                    {"$set": {"locked": None, "locked_at": None}}  # Clear the lock
                )
    except Exception as e:
        app.logger.error(f"Error unlocking expired houses: {e}")

@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        unlock_expired_houses()  # Ensure any expired locks are cleared

        session_id = get_session_id()

        if not session_id:
            return jsonify({"error": "Session ID is missing"}), 400

        houses = mongo.db.houses.find()
        houses_list = []

        for house in houses:
            house_id = house.get('house_id')

            # Check if the house is locked by another user
            house_locked = house.get('locked') != session_id if house.get('locked') else False

            houses_list.append({
                'house_id': house_id,
                'house_name': house.get('house_name', 'Unnamed House'),
                'house_image': house.get('house_image', ''),
                'description': house.get('description', ''),
                'locked': house_locked,  # Send lock status to frontend
            })

        return jsonify(houses_list)

    except Exception as e:
        app.logger.error(f"Error fetching houses: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/select-house', methods=['POST'])
def select_house():
    try:
        session_id = get_session_id()

        data = request.get_json()
        house_id = data.get('house_id')

        # Check if the house is already locked by another user
        house = mongo.db.houses.find_one({"house_id": house_id})

        if house and house.get('locked'):
            if house['locked'] != session_id:
                return jsonify({"error": "This house is already locked by another user"}), 400

        # Lock the house by setting the session ID and adding a locked timestamp
        mongo.db.houses.update_one(
            {"house_id": house_id},
            {"$set": {"locked": session_id, "locked_at": datetime.utcnow()}}  # Lock the house with timestamp
        )

        return jsonify({
            "message": "House selected successfully",
            "session_id": session_id,
            "house_id": house_id,
        })

    except Exception as e:
        app.logger.error(f"Error selecting house: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/exit', methods=['POST'])
def exit_website():
    try:
        data = request.get_json()  # Get the incoming JSON data
        house_id = data.get("house_id")
        session_id = data.get("session_id")

        if not house_id or not session_id:
            return jsonify({"error": "House ID and Session ID are required"}), 400

        # Find all houses locked by this session ID
        locked_houses = mongo.db.houses.find({"locked": session_id})

        # Unlock all houses for this session
        for house in locked_houses:
            mongo.db.houses.update_one(
                {"house_id": house['house_id']},
                {"$set": {"locked": None, "locked_at": None}}  # Unlock the house and clear timestamp
            )

        # End the session (logout the user)
        session.clear()

        return jsonify({"message": "House unlocked and session ended"}), 200

    except Exception as e:
        app.logger.error(f"Error ending session: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/rooms/<house_id>', methods=['GET'])
def get_rooms(house_id):
    try:
        # Fetch house layout based on house_id
        house_layout = mongo.db.layout.find_one({"house_id": house_id})
        
        if not house_layout:
            return jsonify({"error": "House layout not found"}), 404
        
        rooms_data = house_layout.get('rooms', [])
        rooms_image = house_layout.get('rooms_image', '')  # Default image if none provided

        return jsonify({
            "rooms_image": rooms_image,
            "rooms": rooms_data
        })

    except Exception as e:
        app.logger.error(f"Error fetching house layout for {house_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/room-data', methods=['GET'])
def get_room_data():
    try:
        # Ensure the user has a session ID
        session_id = get_session_id()

        # Get room_name and house_id from query parameters
        room_name = request.args.get('room_name')
        house_id = request.args.get('house_id')

        if not house_id or not room_name:
            app.logger.warning(f"Missing parameters: house_id={house_id}, room_name={room_name}")
            return jsonify({"error": "house_id and room_name are required parameters"}), 400

        # Log the received parameters for debugging
        app.logger.info(f"Received request with house_id: {house_id}, room_name: {room_name}")

        # Fetch room data from the database
        room_data = mongo.db.rooms.find_one({"house_id": house_id, "rooms.room_name": room_name})

        # If room is found, process the room data
        if room_data:
            # Find the specific room data by room_name
            room = next((r for r in room_data.get("rooms", []) if r["room_name"] == room_name), None)

            if room:
                # Safely extract the kitchen data from the room
                room_images = room.get("images", [])
                
                # Handle the case where images might not be available or are empty
                kitchen_image_data = room_images[0] if room_images else {}

                kitchen_data = {
                    "room_name": room.get("room_name"),
                    "images": room_images,
                    "cabinet_colors": kitchen_image_data.get("cabinet_colors", []),
                    "wall_colors": kitchen_image_data.get("wall_colors", []),
                    "basin_colors": kitchen_image_data.get("basin_colors", []),
                }

                return jsonify(kitchen_data), 200
            else:
                app.logger.error(f"Room '{room_name}' not found in house '{house_id}'")
                return jsonify({"error": f"Room '{room_name}' not found in house '{house_id}'"}), 404
        else:
            app.logger.error(f"House '{house_id}' or room '{room_name}' not found in the database")
            return jsonify({"error": f"House '{house_id}' or room '{room_name}' not found"}), 404

    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        # Get session ID from the user's session (it should be in cookies)
        session_id = get_session_id()

        # Get the room details and color selections from the request body
        data = request.get_json()
        house_id = data.get("house_id")
        room_name = data.get("room_name")
        color_selections = data.get("color_selections", {})

        # Log the received data for debugging
        app.logger.info(f"User selecting room: house_id={house_id}, room_name={room_name}, colors={color_selections}")

        # Update the room's color selections in the database
        mongo.db.rooms.update_one(
            {"house_id": house_id, "rooms.room_name": room_name},
            {"$set": {"rooms.$.color_selections": color_selections}}
        )

        return jsonify({"message": "Room color selections saved successfully!"}), 200

    except Exception as e:
        app.logger.error(f"Error selecting room: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
