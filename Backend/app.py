from flask import Flask, request, jsonify, session, make_response
import uuid
from datetime import datetime, timedelta
from flask_cors import CORS
from flask_pymongo import PyMongo
import os

# Initialize the Flask app and configure MongoDB URI
app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

# Enable CORS for specific origins (your frontend URL) to allow cross-origin requests
CORS(app, supports_credentials=True)

# Set secret key for session encryption
app.secret_key = os.urandom(24)  # Use a secure random key for session encryption

# Session configurations
app.config.update(
    SESSION_COOKIE_NAME='session_id',  # Name of the session cookie
    SESSION_COOKIE_HTTPONLY=True,  # Make the cookie accessible only to the server
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),  # Session expiry
    SESSION_COOKIE_DOMAIN='.localhost',  # Domain for cross-subdomain cookies
    SESSION_COOKIE_SAMESITE='None',  # Allow cross-origin requests
    SESSION_COOKIE_SECURE=False  # Disable secure flag for localhost (set to True for HTTPS)
)

def get_session_id():
    if 'session_id' in session:
        return session['session_id']
    new_session_id = str(uuid.uuid4())
    session['session_id'] = new_session_id
    return new_session_id

# Helper function to unlock house
def unlock_house(house_id):
    houses_collection = mongo.db.houses
    house = houses_collection.find_one({"house_id": house_id})
    
    if house and house.get("locked"):
        houses_collection.update_one(
            {"house_id": house_id},
            {"$unset": {"locked": "", "locked_at": ""}}  # Remove the lock
        )

@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        session_id = get_session_id()  # This will check or generate session_id

        house_id = request.args.get('house_id')  # Optional query parameter for selecting a specific house

        houses_collection = mongo.db.houses
        all_houses = houses_collection.find({})

        house_list = []

        # If a house_id is provided, handle locking/unlocking
        if house_id:
            house = houses_collection.find_one({"house_id": house_id})

            if not house:  # If the specific house doesn't exist
                return jsonify({"status": "error", "message": "House not found"}), 404

            # Check if the house is already locked
            if house.get("locked") and house.get("locked") != session_id:
                return jsonify({"status": "error", "message": "House already locked"}), 400

            locked_at = house.get('locked_at')
            if locked_at:
                if isinstance(locked_at, str):
                    locked_at = datetime.strptime(locked_at, '%Y-%m-%d %H:%M:%S')
                locked_duration = datetime.now() - locked_at
                if locked_duration > timedelta(minutes=1):
                    unlock_house(house_id)

            locked_at = datetime.now()
            houses_collection.update_one(
                {"house_id": house_id},
                {"$set": {"locked": session_id, "locked_at": locked_at}}
            )

            # Return the status of the locked house
            response_data = {
                "status": "ok",
                "session_id": session_id,
                "house_id": house_id,
                "locked_at": locked_at.strftime('%Y-%m-%d %H:%M:%S')
            }

            response = make_response(jsonify(response_data))
            response.set_cookie('session_id', session_id, max_age=timedelta(days=30), httponly=True, secure=False)
            return response

        # If no house_id is provided, return the list of available houses
        for house in all_houses:
            locked_at = house.get('locked_at')
            if locked_at:
                if isinstance(locked_at, str):
                    locked_at = datetime.strptime(locked_at, '%Y-%m-%d %H:%M:%S')
                locked_duration = datetime.now() - locked_at
                if locked_duration > timedelta(minutes=1):  # Unlock if locked for more than 30 minutes
                    unlock_house(house['house_id'])

            if not house.get("locked"):
                house_data = {
                    "house_id": house.get("house_id"),
                    "house_name": house.get("house_name"),
                    "house_image": house.get("house_image"),
                    "description": house.get("description"),
                }
                house_list.append(house_data)

        if not house_list:
            return jsonify({"status": "error", "message": "No available houses"}), 404

        return jsonify(house_list), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500

@app.route('/rooms/<house_id>', methods=['GET'])
def get_layout(house_id):
    try:
        session_id = get_session_id()  # Retrieve session ID from cookie
        house_layout = mongo.db.houses.find_one({"house_id": house_id})

        if not house_layout:
            return jsonify({"error": "House layout not found"}), 404

        rooms_data = house_layout.get('rooms', {})
        rooms_image = house_layout.get('rooms_image', '')

        layout_response = {
            "house_id": house_id,
            "rooms_image": rooms_image,
            "rooms": []
        }

        for room_name, room in rooms_data.items():
            room_data = {
                "name": room_name,
                "areas": []
            }

            layout_page_details = room.get('layout_page_details', {})
            if layout_page_details:
                room_data["areas"].append({
                    "name": room_name,
                    **layout_page_details
                })

            if room.get('image_path'):
                room_data["image_path"] = room.get('image_path')

            layout_response["rooms"].append(room_data)

        return jsonify(layout_response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/room-data', methods=['GET'])
def get_room_data():
    try:
        # Get the session_id from the cookie if not present in query parameters
        session_id = request.args.get('session_id') or request.cookies.get('session_id')

        # Generate a new session_id if it's not found
        if not session_id:
            session_id = get_session_id()  # Retrieve session_id from session (this will set a cookie)

        # Get the query parameters from the request
        house_id = request.args.get('house_id')
        room_name = request.args.get('room_name')

        # Validate input
        if not house_id or not session_id or not room_name:
            return jsonify({"status": "error", "message": "Missing house_id, session_id, or room_name"}), 400

        # Fetch the house data from the database based on house_id
        houses_collection = mongo.db.houses  # Reference to the houses collection
        house = houses_collection.find_one({"house_id": house_id})

        if not house:  # If house not found
            return jsonify({"status": "error", "message": "House not found"}), 404

        # Check if the house is locked by the current session_id
        locked_by = house.get("locked_by")
        if not locked_by:
            # If the house is not locked by any session, we can lock it for the current session
            houses_collection.update_one(
                {"house_id": house_id},
                {"$set": {"locked_by": session_id}}
            )
            locked_by = session_id  # Lock it for the current session



        # Fetch the specific room data from the house based on room_name
        rooms = house.get('rooms', {})
        room_data = rooms.get(room_name)

        if not room_data:  # If the room is not found
            return jsonify({"status": "error", "message": "Room not found"}), 404

        # Prepare the response data (colors and images for wall, ceiling, etc.)
        images = []
        available_selections = []

        for category, color_data in room_data.get('color_categories', {}).items():
            color_category = {
                "key": category,
                "label": color_data['label'],
                "colors": [
                    {"color": color['color'], "image": color['image']} for color in color_data['colors']
                ],
                "selected_color": color_data.get('selected_color', None)
            }
            images.append(color_category)  # Add color data to images list

        # Include available selections in the response
        if "available_selections" in room_data:
            available_selections = room_data["available_selections"]

        # Construct the response with images, available selections, and room data
        response_data = {
            "images": images,
            "image_path": room_data.get('image_path', ''),  # Image for the room (like a thumbnail)
            "room_name": room_name,
            "available_selections": available_selections
        }

        # Set the session cookie if it's not already set
        response = make_response(jsonify(response_data))
        if not request.cookies.get('session_id'):
            response.set_cookie('session_id', session_id, max_age=timedelta(days=30), httponly=True, secure=False)

        return response  # Return the room data response

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        data = request.get_json()
        house_id = data.get('house_id')
        session_id = get_session_id()  # Retrieve session ID from cookie
        selected_rooms = data.get('selected_rooms')
        preferences = data.get('preferences')

        if not house_id or not selected_rooms:
            return jsonify({"status": "error", "message": "Missing house_id or selected_rooms"}), 400

        houses_collection = mongo.db.houses
        house = houses_collection.find_one({"house_id": house_id})

        if not house:
            return jsonify({"status": "error", "message": "House not found"}), 404

        locked_by = house.get("locked_by")
        if not locked_by:
            houses_collection.update_one(
                {"house_id": house_id},
                {"$set": {"locked_by": session_id}}
            )
            locked_by = session_id

        if locked_by != session_id:
            return jsonify({"status": "error", "message": "House is not locked by your session"}), 400

        house_preferences = {
            "selected_rooms": selected_rooms,
            "preferences": preferences
        }

        mongo.db.user_selection.update_one(
            {"house_id": house_id, "session_id": session_id},
            {"$set": house_preferences},
            upsert=True
        )

        return jsonify({
            "message": "Room selection updated successfully",
            "house_id": house_id,
            "session_id": session_id,
            "selected_rooms": selected_rooms,
            "preferences": preferences
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
