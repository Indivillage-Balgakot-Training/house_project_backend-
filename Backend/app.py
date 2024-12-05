import uuid
import os
from flask import Flask, jsonify, request, session, make_response
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime, timedelta
import logging

# Initialize Flask app
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
    # Fetch all houses that are locked
    locked_houses = mongo.db.houses.find({"locked": {"$ne": None}})

    # Define lock timeout period (e.g., 1 hour)
    # Lock expires after 1 hour
    lock_timeout = timedelta(seconds=40)  # Lock expires after 20 seconds

    # Iterate through each locked house
    for house in locked_houses:
        locked_at = house.get('locked_at')
        if locked_at and (datetime.utcnow() - locked_at) > lock_timeout:
            # Unlock the house if the lock time has expired
            mongo.db.houses.update_one(
                {"house_id": house['house_id']},
                {"$set": {"locked": None, "locked_at": None}}  # Clear the lock
            )

@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        unlock_expired_houses()  # Ensure any expired locks are cleared

        session_id = get_session_id()

        if not session_id:
            return jsonify({"error": "Session ID is missing"}), 400

        # Fetch all houses
        houses = mongo.db.houses.find()

        houses_list = []

        for house in houses:
            house_id = house.get('house_id')

            # Check if the house is locked by another user
            if house.get('locked') and house['locked'] != session_id:
                # Skip adding this house to the list if it's locked by another user
                continue

            house_locked = house.get('locked') is not None and house['locked'] == session_id

            houses_list.append({
                'house_id': house_id,
                'house_name': house.get('house_name'),
                'house_image': house.get('house_image', ''),
                'description': house.get('description', ''),
                'locked': house_locked,  # Send lock status to frontend
            })

        return jsonify(houses_list)

    except Exception as e:
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
            return jsonify({"error": "house_id and room_name are required parameters"}), 400

        # Fetch room data from the database
        room_data = mongo.db.rooms.find_one({"house_id": house_id, "rooms.room_name": room_name})

        # If room is found, process the room data
        if room_data:
            # Find the specific room data by room_name
            room = next((r for r in room_data.get("rooms", []) if r["room_name"] == room_name), None)

            if room:
                room_images = room.get("images", [])
                if room_images:
                    room_data = room_images[0]
                else:
                    room_data = {}

                # If it's the bedroom, add the wardrobe_colors to the response
                if room_name.lower() == 'bedroom':
                    room_data = {
                        "room_name": room.get("room_name"),
                        "images": room_images,
                        "cabinet_colors": room_data.get("cabinet_colors", []),
                        "wall_colors": room_data.get("wall_colors", []),
                        "basin_colors": room_data.get("basin_colors", []),
                        "wardrobe_colors": room_data.get("wardrobe_colors", []),  # Only for bedroom
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


@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        # Get the session ID from the request (assumed to be stored in cookies or headers)
        session_id = get_session_id()

        # Get the room details and color selections from the request body
        data = request.get_json()
        house_id = data.get('house_id')
        session_id_from_request = data.get('session_id')  # session_id passed from the request body
        selected_rooms = data.get('selected_rooms')
        cabinet_colors = data.get('cabinet_colors', [])  # Default to empty list if no colors provided
        wall_colors = data.get('wall_colors', [])
        basin_colors = data.get('basin_colors', [])
        wardrobe_colors = data.get('wardrobe_colors', [])

        # Check if house_id, session_id, and selected_rooms are provided
        if not house_id or not session_id_from_request or not selected_rooms:
            return jsonify({"error": "Missing house_id, session_id, or selected_rooms"}), 400

        # Prepare the update data
        update_data = {
            'selected_rooms': selected_rooms,
        }

        # Handle room-specific data
        if 'bedroom' in selected_rooms:
            update_data['wardrobe_colors'] = wardrobe_colors
            update_data['wall_colors'] = wall_colors
        else:
            update_data['cabinet_colors'] = cabinet_colors
            update_data['basin_colors'] = basin_colors
            update_data['wall_colors'] = wall_colors

        # Log the update data for debugging
        print(f"Update data: {update_data}")

        # MongoDB update query
        result = mongo.db.user_selection.update_one(
            {'session_id': session_id_from_request, 'house_id': house_id},
            {'$set': update_data}, 
            upsert=True  # Insert a new document if not found
        )

        # Check if update was successful
        if result.matched_count > 0 or result.upserted_id:
            return jsonify({"message": "Room selection updated successfully"}), 200
        else:
            return jsonify({"error": "House not found or session mismatch"}), 404

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/user-selection', methods=['GET'])
def get_room_selection():
    try:
        # Ensure the user has a session ID
        session_id = get_session_id()

        # Get house_id from query parameters
        house_id = request.args.get('house_id')

        if not house_id or not session_id:
            return jsonify({"error": "Missing house_id or session_id"}), 400

        # Query the user_selection collection to get the stored room selection data
        user_selection = mongo.db.user_selection.find_one({'session_id': session_id, 'house_id': house_id})

        if not user_selection:
            return jsonify({"error": "No previous selection found for this house and user"}), 404

        # Prepare the response data with selected rooms and colors, excluding missing data
        selection_data = {
            'selected_rooms': user_selection.get('selected_rooms', []),
        }

        # Add colors only if they exist
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
        # Log any errors that occur during the process
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)