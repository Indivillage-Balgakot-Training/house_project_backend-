from flask import Flask, request, jsonify, session, make_response
import uuid
from datetime import datetime, timedelta
from flask_cors import CORS
from flask_pymongo import PyMongo
import os

# Initialize the Flask app and configure MongoDB URI
app = Flask(__name__)
# Connect to MongoDB database using URI
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

# Enable CORS to allow cross-origin requests from frontend (important for handling requests from different domains)
CORS(app, supports_credentials=True)

# Set secret key for session encryption (helps secure cookies and sessions)
app.secret_key = os.urandom(24)

# Session configuration (for cookie handling and security)
app.config.update(
    SESSION_COOKIE_NAME='session_id',  # Cookie name for session ID
    SESSION_COOKIE_HTTPONLY=True,  # Prevent client-side scripts from accessing cookie
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),  # Session duration
    SESSION_COOKIE_DOMAIN='.localhost',  # Allow cookies from localhost domain
    SESSION_COOKIE_SAMESITE='None',  # Enable cross-site requests for the session cookie
    SESSION_COOKIE_SECURE=False  # Disable secure flag for cookies (for testing purposes)
)

# Helper function to get or generate a session ID
def get_session_id():
    session_id = request.cookies.get('session_id')  # Get session ID from the cookies
    if session_id:
        return session_id  # Return the session ID if it exists
    # Generate a new session ID if it doesn't exist
    new_session_id = str(uuid.uuid4())
    session['session_id'] = new_session_id  # Store the session ID in the server session
    return new_session_id

# Helper function to unlock a house by its ID (set its lock status to False)
def unlock_house(house_id):
    houses_collection = mongo.db.houses  # Access MongoDB's 'houses' collection
    house = houses_collection.find_one({"house_id": house_id})  # Find house by its ID
    if house and house.get("locked"):  # If house is locked
        # Unlock the house and clear lock details
        houses_collection.update_one(
            {"house_id": house_id},
            {"$set": {"locked": False, "locked_by": None, "locked_at": None}}
        )

# Route to get the list of houses
@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        # Get or generate session ID
        session_id = request.cookies.get('session_id') or get_session_id()
        house_id = request.args.get('house_id')  # Get house ID from query parameters
        houses_collection = mongo.db.houses  # Access MongoDB's 'houses' collection
        all_houses = houses_collection.find({})  # Get all houses from the database

        house_list = []  # List to hold houses that are available (not locked)
        if house_id:
            # Check if specific house is locked, and if the session is allowed to interact with it
            house = houses_collection.find_one({"house_id": house_id})
            if not house:
                return jsonify({"status": "error", "message": "House not found"}), 404
            if house.get("locked") and house.get("locked_by") != session_id:
                return jsonify({"status": "error", "message": "House already locked"}), 400

            locked_at = house.get('locked_at')
            if locked_at:
                if isinstance(locked_at, str):
                    locked_at = datetime.strptime(locked_at, '%Y-%m-%d %H:%M:%S')  # Convert to datetime if string
                locked_duration = datetime.now() - locked_at
                if locked_duration > timedelta(minutes=1):  # Unlock if the house was locked for more than a minute
                    unlock_house(house_id)

            locked_at = datetime.now()
            houses_collection.update_one(
                {"house_id": house_id},
                {"$set": {"locked": True, "locked_by": session_id, "locked_at": locked_at}}  # Lock the house
            )

            response_data = {
                "status": "ok",
                "session_id": session_id,
                "house_id": house_id,
                "locked_at": locked_at.strftime('%Y-%m-%d %H:%M:%S')  # Return locked time in response
            }
            response = make_response(jsonify(response_data))
            response.set_cookie('session_id', session_id, max_age=timedelta(days=30), httponly=True, secure=False)  # Set session cookie
            return response

        # If no house_id was provided, return a list of available houses
        for house in all_houses:
            locked_at = house.get('locked_at')
            if locked_at:
                if isinstance(locked_at, str):
                    locked_at = datetime.strptime(locked_at, '%Y-%m-%d %H:%M:%S')
                locked_duration = datetime.now() - locked_at
                if locked_duration > timedelta(minutes=1):
                    unlock_house(house['house_id'])

            if not house.get("locked"):  # Only add available (unlocked) houses
                house_data = {
                    "house_id": house.get("house_id"),
                    "house_name": house.get("house_name"),
                    "house_image": house.get("house_image"),
                    "description": house.get("description"),
                }
                house_list.append(house_data)

        if not house_list:
            return jsonify({"status": "error", "message": "No available houses"}), 404

        return jsonify(house_list), 200  # Return available houses

    except Exception as e:
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500  # Handle errors

# Route to get the layout of a specific house by its ID
@app.route('/rooms/<house_id>', methods=['GET'])
def get_layout(house_id):
    try:
        session_id = request.cookies.get('session_id') or get_session_id()  # Get session ID
        house_layout = mongo.db.houses.find_one({"house_id": house_id})  # Fetch house layout from DB
        if not house_layout:
            return jsonify({"error": "House layout not found"}), 404  # If no layout found

        rooms_data = house_layout.get('rooms', {})  # Get room data from house layout
        rooms_image = house_layout.get('rooms_image', '')  # Get room images if available

        layout_response = {
            "house_id": house_id,
            "rooms_image": rooms_image,
            "rooms": []  # Store room data
        }

        # Loop through rooms and build room data for response
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
        return jsonify({"error": str(e)}), 500  # Handle errors


# Route to get room data based on house ID and room name
@app.route('/room-data', methods=['GET'])
def get_room_data():
    try:
        # Get session ID from cookies
        session_id = request.cookies.get('session_id') or get_session_id()

        # Get query parameters for house ID and room name
        house_id = request.args.get('house_id')
        room_name = request.args.get('room_name')

        if not house_id or not session_id or not room_name:
            return jsonify({"status": "error", "message": "Missing house_id, session_id, or room_name"}), 400

        houses_collection = mongo.db.houses  # Reference to MongoDB 'houses' collection
        house = houses_collection.find_one({"house_id": house_id})

        if not house:  # If house not found
            return jsonify({"status": "error", "message": "House not found"}), 404

        # Check if the house is locked by the current session_id
        locked_by = house.get("locked_by")
        if not locked_by:
            # If the house is not locked, lock it for the current session
            houses_collection.update_one(
                {"house_id": house_id},
                {"$set": {"locked_by": session_id}}
            )
            locked_by = session_id

        # Fetch the specific room data
        rooms = house.get('rooms', {})
        room_data = rooms.get(room_name)

        if not room_data:  # If room not found
            return jsonify({"status": "error", "message": "Room not found"}), 404

        # Prepare the response with images, available selections, and color options
        images = []
        available_selections = []

        for category, color_data in room_data.get('color_categories', {}).items():
            color_category = {
                "key": category,
                "label": color_data['label'],
                "colors": [
                  {"color": color['color']} for color in color_data['colors']  # Removed the 'image' field
                ],
                "selected_color": color_data.get('selected_color', None)
            }
            images.append(color_category)

        if "available_selections" in room_data:
            available_selections = room_data["available_selections"]

        # Construct the final response
        response_data = {
            "images": images,
            "image_path": room_data.get('image_path', ''),
            "room_name": room_name,
            "available_selections": available_selections
        }

        # Set the session cookie if it's not already set
        response = make_response(jsonify(response_data))
        if not request.cookies.get('session_id'):
            response.set_cookie('session_id', session_id, max_age=timedelta(days=30), httponly=True, secure=False)

        return response

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to select a room and save preferences
@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        # Get session ID from cookies (use this as the only source of session ID)
        session_id = request.cookies.get('session_id') or get_session_id()

        # Get data from the request body (JSON)
        data = request.get_json()
        house_id = data.get('house_id')
        selected_rooms = data.get('selected_rooms')
        preferences = data.get('preferences')

        print("Request Data: ", data)
        print("Session ID: ", session_id)

        if not house_id or not selected_rooms:
            return jsonify({"status": "error", "message": "Missing house_id or selected_rooms"}), 400

        # Reference to MongoDB 'houses' collection
        houses_collection = mongo.db.houses
        house = houses_collection.find_one({"house_id": house_id})

        if not house:  # If house not found
            return jsonify({"status": "error", "message": "House not found"}), 404

        locked_by = house.get("locked_by")
        if not locked_by:
            houses_collection.update_one(
                {"house_id": house_id},
                {"$set": {"locked_by": session_id}}
            )
            locked_by = session_id

        # Ensure the house is locked by the current session before making selections
        if locked_by != session_id:
            return jsonify({"status": "error", "message": "House is not locked by your session"}), 400

        # Save the selected rooms and preferences to the database
        house_preferences = {
            "selected_rooms": selected_rooms,
            "preferences": preferences
        }

        mongo.db.user_selection.update_one(
            {"house_id": house_id, "session_id": session_id},
            {"$set": house_preferences},
            upsert=True  # Create a new record if it doesn't exist
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


# Run the Flask app (start the server)
if __name__ == '__main__':
    app.run(debug=True)
