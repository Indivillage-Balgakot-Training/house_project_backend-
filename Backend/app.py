import uuid
import os
from flask import Flask, jsonify, request, session, make_response
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime, timedelta
import logging

# Initialize Flask application
app = Flask(__name__)

# Set a secret key for session management (cookies)
app.secret_key = os.urandom(24)  # Randomly generated key to secure session cookies

# Enable Cross-Origin Resource Sharing (CORS) with credentials, allowing cookies to be sent across domains
CORS(app, supports_credentials=True)

# MongoDB connection configuration
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

# Session settings to ensure persistence across requests
app.config.update(
    SESSION_COOKIE_NAME='session_id',  # Name for the session cookie
    SESSION_COOKIE_HTTPONLY=True,  # Cookie is not accessible via JavaScript
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),  # Set session expiry time to 30 days
    SESSION_COOKIE_DOMAIN='.localhost',  # Set cookie domain for subdomains
    SESSION_COOKIE_SAMESITE='None',  # Allow cookies to be sent across different origins
    SESSION_COOKIE_SECURE=False  # Disable the secure flag for local development (use True for production)
)

# Function to ensure each user has a unique session ID stored in cookies
def get_session_id():
    if 'session_id' not in session:
        session.permanent = True  # Keep session alive across browser restarts
        session['session_id'] = str(uuid.uuid4())  # Generate a new UUID if no session ID exists
    return session['session_id']

# Function to unlock houses whose lock has expired
def unlock_expired_houses():
    # Get all houses with an active lock
    locked_houses = mongo.db.houses.find({"locked": {"$ne": None}})

    # Set the lock expiration time (e.g., 10 seconds for testing)
    lock_timeout = timedelta(seconds=10)

    for house in locked_houses:
        locked_at = house.get('locked_at')
        if locked_at and (datetime.utcnow() - locked_at) > lock_timeout:
            # If the lock has expired, remove the lock from the house
            mongo.db.houses.update_one(
                {"house_id": house['house_id']},
                {"$set": {"locked": None, "locked_at": None}}  # Clear lock and timestamp
            )

# Route to get the list of available houses
@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        unlock_expired_houses()  # Ensure expired locks are cleared

        session_id = get_session_id()

        if not session_id:
            return jsonify({"error": "Session ID is missing"}), 400

        # Retrieve all houses from the database
        houses = mongo.db.houses.find()

        houses_list = []

        for house in houses:
            house_id = house.get('house_id')

            # Check if the house is locked by another user
            if house.get('locked') and house['locked'] != session_id:
                # Skip adding this house if it is locked by another user
                continue

            house_locked = house.get('locked') is not None and house['locked'] == session_id

            houses_list.append({
                'house_id': house_id,
                'house_name': house.get('house_name'),
                'house_image': house.get('house_image', ''),
                'description': house.get('description', ''),
                'locked': house_locked,  # Indicate whether the house is locked by the current user
            })

        return jsonify(houses_list)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to lock a house for the current user
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

        # Lock the house for the current session
        mongo.db.houses.update_one(
            {"house_id": house_id},
            {"$set": {"locked": session_id, "locked_at": datetime.utcnow()}}  # Lock with timestamp
        )

        return jsonify({
            "message": "House selected successfully",
            "session_id": session_id,
            "house_id": house_id,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to unlock houses and end the session
@app.route('/exit', methods=['POST'])
def exit_website():
    try:
        data = request.get_json()
        house_id = data.get("house_id")
        session_id = data.get("session_id")

        if not house_id or not session_id:
            return jsonify({"error": "House ID and Session ID are required"}), 400

        # Find and unlock all houses locked by the session
        locked_houses = mongo.db.houses.find({"locked": session_id})

        for house in locked_houses:
            mongo.db.houses.update_one(
                {"house_id": house['house_id']},
                {"$set": {"locked": None, "locked_at": None}}  # Remove lock and timestamp
            )

        # Clear the session (log the user out)
        session.clear()

        return jsonify({"message": "House unlocked and session ended"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to get the layout and rooms of a specific house
@app.route('/rooms/<house_id>', methods=['GET'])
def get_rooms(house_id):
    try:
        # Fetch the house layout for the given house ID
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
        return jsonify({"error": str(e)}), 500

# Route to get data for a specific room
@app.route('/room-data', methods=['GET'])
def get_room_data():
    try:
        session_id = get_session_id()

        # Get room and house details from query parameters
        room_name = request.args.get('room_name')
        house_id = request.args.get('house_id')

        if not house_id or not room_name:
            return jsonify({"error": "house_id and room_name are required parameters"}), 400

        # Fetch room data for the given house and room name
        room_data = mongo.db.rooms.find_one({"house_id": house_id, "rooms.room_name": room_name})

        if room_data:
            # Find the specific room from the list of rooms
            room = next((r for r in room_data.get("rooms", []) if r["room_name"] == room_name), None)

            if room:
                room_images = room.get("images", [])
                if room_images:
                    room_data = room_images[0]  # Get the first image if available
                else:
                    room_data = {}

                # Special handling for bedroom and living room rooms
                if room_name.lower() == 'bedroom':
                    room_data = {
                        "room_name": room.get("room_name"),
                        "images": room_images,
                        "cabinet_colors": room_data.get("cabinet_colors", []),
                        "wall_colors": room_data.get("wall_colors", []),
                        "basin_colors": room_data.get("basin_colors", []),
                        "wardrobe_colors": room_data.get("wardrobe_colors", []),  # For bedroom
                    }
                elif room_name.lower() == 'living room':
                    room_data = {
                        "room_name": room.get("room_name"),
                        "images": room_images,
                        "cabinet_colors": room_data.get("cabinet_colors", []),
                        "wall_colors": room_data.get("wall_colors", []),
                        "ceiling_colors": room_data.get("ceiling_colors", []),  # Living room specific ceiling colors
                    }
                else:
                    room_data = {
                        "room_name": room.get("room_name"),
                        "images": room_images,
                        "cabinet_colors": room_data.get("cabinet_colors", []),
                        "wall_colors": room_data.get("wall_colors", []),
                        "basin_colors": room_data.get("basin_colors", []),
                    }

                return jsonify(room_data), 200
            else:
                return jsonify({"error": f"Room '{room_name}' not found in house '{house_id}'"}), 404
        else:
            return jsonify({"error": f"House '{house_id}' or room '{room_name}' not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route to select rooms and update preferences (like colors)
@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        session_id = get_session_id()

        data = request.get_json()
        house_id = data.get('house_id')
        session_id_from_request = data.get('session_id')  # Passed session ID
        selected_rooms = data.get('selected_rooms')
        cabinet_colors = data.get('cabinet_colors', [])  # Default empty if not provided
        wall_colors = data.get('wall_colors', [])
        basin_colors = data.get('basin_colors', [])
        wardrobe_colors = data.get('wardrobe_colors', [])
        ceiling_colors = data.get('ceiling_colors', [])  # For living room

        if not house_id or not session_id_from_request or not selected_rooms:
            return jsonify({"error": "Missing house_id, session_id, or selected_rooms"}), 400

        update_data = {
            'selected_rooms': selected_rooms,
        }

        # Update room-specific preferences based on the room type
        if 'bedroom' in selected_rooms:
            update_data['wardrobe_colors'] = wardrobe_colors
            update_data['wall_colors'] = wall_colors
        elif 'living room' in selected_rooms:
            update_data['ceiling_colors'] = ceiling_colors  # Add ceiling colors
            update_data['wall_colors'] = wall_colors
        else:
            update_data['cabinet_colors'] = cabinet_colors
            update_data['basin_colors'] = basin_colors
            update_data['wall_colors'] = wall_colors

        # Log for debugging
        print(f"Update data: {update_data}")

        # MongoDB update query
        result = mongo.db.user_selection.update_one(
            {'session_id': session_id_from_request, 'house_id': house_id},
            {'$set': update_data},  # Update selected room data
            upsert=True  # Insert new if not already present
        )

        if result.matched_count > 0 or result.upserted_id:
            return jsonify({"message": "Room selection updated successfully"}), 200
        else:
            return jsonify({"error": "House not found or session mismatch"}), 404

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Route to fetch user selections for a house
@app.route('/user-selection', methods=['GET'])
def get_room_selection():
    try:
        session_id = get_session_id()

        house_id = request.args.get('house_id')

        if not house_id or not session_id:
            return jsonify({"error": "Missing house_id or session_id"}), 400

        # Fetch user room selections from the database
        user_selection = mongo.db.user_selection.find_one({'session_id': session_id, 'house_id': house_id})

        if not user_selection:
            return jsonify({"error": "No previous selection found for this house and user"}), 404

        # Prepare the response data with selected rooms and colors
        selection_data = {
            'selected_rooms': user_selection.get('selected_rooms', []),
        }

        if 'cabinet_colors' in user_selection:
            selection_data['cabinet_colors'] = user_selection['cabinet_colors']
        if 'wall_colors' in user_selection:
            selection_data['wall_colors'] = user_selection['wall_colors']
        if 'basin_colors' in user_selection:
            selection_data['basin_colors'] = user_selection['basin_colors']
        if 'wardrobe_colors' in user_selection:
            selection_data['wardrobe_colors'] = user_selection['wardrobe_colors']

        return jsonify(selection_data), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True)
