from flask import Flask, request, jsonify, session, make_response
import uuid
from datetime import datetime, timedelta, timezone
from flask_cors import CORS
from flask_pymongo import PyMongo
import os
import logging

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

def get_session_id():
    session_id = request.cookies.get('session_id')  # Get session ID from cookies
    if session_id:
        return session_id  # Return the session ID if it exists
    
    # Generate a new session ID if it doesn't exist
    new_session_id = str(uuid.uuid4())
    response = make_response()  # Create a response object
    response.set_cookie('session_id', new_session_id, max_age=timedelta(days=30), httponly=True, secure=False)
    
    # Ensure the session ID is set in the cookies for future requests
    return new_session_id


def lock_house(house_id, session_id):
    houses_collection = mongo.db.houses  # Access MongoDB's 'houses' collection
    house = houses_collection.find_one({"house_id": house_id})  # Find house by its ID
    
    if house:
        if house.get("locked"):
            # If the house is already locked by another user, raise an error
            if house["locked"] != session_id:
                raise Exception("This house is already locked by another user")
            else:
                return "House is already locked by you."
        else:
            # Lock the house for the current session by updating its 'locked' field
            houses_collection.update_one(
                {"house_id": house_id},
                {"$set": {"locked": session_id, "locked_at": datetime.now(timezone.utc)}}  # Lock the house and record the time
            )
            return "House locked successfully."
    else:
        raise Exception("House not found.")

# Helper function to unlock a house by its ID (set its lock status to False)
def unlock_house(house_id):
    houses_collection = mongo.db.houses  # Access MongoDB's 'houses' collection
    house = houses_collection.find_one({"house_id": house_id})  # Find house by its ID
    if house and house.get("locked"):  # If house is locked
        # Check if the house has been locked for more than 1 minutes
        locked_at = house.get("locked_at")
        if locked_at:
            # Ensure locked_at is timezone-aware
            if locked_at.tzinfo is None:
                locked_at = locked_at.replace(tzinfo=timezone.utc)  # Make it timezone-aware if it's naive

            # Compare with current UTC time (also timezone-aware)
            locked_duration = datetime.now(timezone.utc) - locked_at
            if locked_duration > timedelta(minutes=1):  # Unlock if the house was locked for more than 1 minute
                # Unlock the house
                houses_collection.update_one(
                    {"house_id": house_id},
                    {"$set": {"locked": False, "locked_by": None, "locked_at": None}}
                )

@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        session_id = request.cookies.get('session_id')  # Get session ID from cookies
        if not session_id:
            # If session ID is missing, generate a new one
            session_id = get_session_id()

        houses_collection = mongo.db.houses  # Access MongoDB's 'houses' collection
        all_houses = houses_collection.find()  # Get all houses from the database

        house_list = []  # List to hold available (unlocked) houses
        for house in all_houses:
            if house.get('locked'):
                unlock_house(house['house_id'])  # Unlock house if lock has expired

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

        response = make_response(jsonify(house_list), 200)

        # Set the session cookie in response if not already set
        if not request.cookies.get('session_id'):
            response.set_cookie('session_id', session_id, max_age=timedelta(days=30), httponly=True, secure=False)

        return response
    except Exception as e:
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500


@app.route('/rooms/<house_id>', methods=['GET'])
def get_layout(house_id):
    try:
        # Get session ID from cookies or generate a new one
        session_id = request.cookies.get('session_id')

        house_id = request.args.get('house_id')
        
        if not session_id:
            session_id = get_session_id()  # Generate new session ID if not present

        # Fetch the house from the database
        house = mongo.db.houses.find_one({"house_id": house_id})
        if not house:
            return jsonify({"error": "House not found"}), 404  # If the house doesn't exist, return error

        # Debugging: Log the session ID and the locked status
        print(f"Session ID: {session_id}")
        print(f"House {house_id} is locked by: {house.get('locked_by')}")
        
        # Check if the house is locked by another session
        if house.get('locked'):
            locked_by = house.get('locked_by')
            locked_at = house.get('locked_at')

            # Check if the lock is expired (1 minute here, adjust if needed)
            if locked_at:
                if locked_at.tzinfo is None:
                    locked_at = locked_at.replace(tzinfo=timezone.utc)  # Ensure the locked_at is timezone-aware

                locked_duration = datetime.now(timezone.utc) - locked_at
                if locked_duration > timedelta(minutes=1):  # Unlock if more than 15 minutes
                    # Unlock the house automatically if the session is expired
                    mongo.db.houses.update_one(
                        {"house_id": house_id},
                        {"$set": {"locked": False, "locked_by": None, "locked_at": None}}
                    )
                    print(f"Lock expired for house {house_id}, unlocking it.")  # Debugging log

            # Allow users to view the layout even if it's locked by another session
            if locked_by and locked_by != session_id:
                print(f"The house is locked by another session, but you can still view the layout.")

        # If the house is not locked or is locked by the same session, lock it for the current session
        locked_at = datetime.now(timezone.utc)  # Set lock time to current UTC time
        mongo.db.houses.update_one(
            {"house_id": house_id},
            {"$set": {"locked": True, "locked_by": session_id, "locked_at": locked_at}}  # Lock house for the session
        )

        # Fetch the house layout (rooms and images)
        house_layout = mongo.db.houses.find_one({"house_id": house_id})
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

        # Set the session cookie if it's not already set
        response = make_response(jsonify(layout_response), 200)
        if not request.cookies.get('session_id'):
            response.set_cookie('session_id', session_id, max_age=timedelta(days=30), httponly=True, secure=False)

        return response

    except Exception as e:
        print(f"Error: {str(e)}")  # Debugging log
        return jsonify({"error": str(e)}), 500  # Handle errors

# Route to get room data based on house ID and room name


@app.route('/room-data', methods=['GET'])
def get_room_data():
    try:
        # Get session ID from cookies or generate a new one
        session_id = get_session_id()   # This will retrieve the session ID

        # Get query parameters for house ID and room name
        house_id = request.args.get('house_id')
        room_name = request.args.get('room_name')

        # Validate that house_id, session_id, and room_name are provided
        if not house_id or not session_id or not room_name:
            return jsonify({"status": "error", "message": "Missing house_id, session_id, or room_name"}), 400

        house_id = house_id.strip()
        room_name = room_name.strip()

        # Access the MongoDB 'houses' collection
        houses_collection = mongo.db.houses
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

        # Handle color categories and ensure correct format
        if 'color_categories' in room_data:
            for category in room_data['color_categories']:
                color_category = {
                    "key": category.get('key'),
                    "label": category.get('label'),
                    "colors": category.get('colors', []),
                    "selected_color": category.get('selected_color', None)
                }
                images.append(color_category)

        # Add available selections if they exist
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
        # Log the error for debugging purposes
        logging.error(f"Error in get_room_data: {str(e)}")
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500


    
@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        # Get session ID from cookies (or wherever it’s stored)
        session_id = get_session_id()

        # Get data from the request body (JSON)
        data = request.get_json()
        house_id = data.get('house_id')
        selected_rooms = data.get('selected_rooms')
        preferences = data.get('preferences')

        # Check if all necessary fields are provided
        if not house_id or not session_id or not selected_rooms or not preferences:
            return jsonify({"status": "error", "message": "Missing house_id, session_id, selected_rooms, or preferences"}), 400

        if not isinstance(selected_rooms, list):
            return jsonify({"status": "error", "message": "selected_rooms must be a list"}), 400

        # Reference to MongoDB 'houses' collection
        houses_collection = mongo.db.houses
        house = houses_collection.find_one({"house_id": house_id})

        if not house:  # If house not found
            return jsonify({"status": "error", "message": "House not found"}), 404

        # Check if the house is locked and validate session ID
        locked_by = house.get("locked_by")
        if not locked_by:
            # If the house is not locked, lock it for the current session
            houses_collection.update_one(
                {"house_id": house_id},
                {"$set": {"locked_by": session_id}}
            )
            locked_by = session_id

        # Ensure the house is locked by the current session before making selections
        if locked_by != session_id:
            return jsonify({"status": "error", "message": "House is locked by another session"}), 403

        # Prepare the update data for selected rooms and preferences
        room_preferences = {}

        # If preferences are room-specific, update for each selected room
        for room in selected_rooms:
            if room in preferences:
                room_preferences[room] = preferences[room]
            else:
                return jsonify({"status": "error", "message": f"Preferences for room {room} are missing"}), 400

        # Update the house document with the selected rooms and preferences for the session
        houses_collection.update_one(
            {"house_id": house_id},
            {"$set": {
                "selected_rooms": selected_rooms,
                "preferences": room_preferences,  # Save preferences by room
                "locked_by": session_id
            }}
        )

        return jsonify({
            "status": "success",
        }), 200

    except Exception as e:
        # Log the error for debugging purposes
        logging.error(f"Error in select_room: {str(e)}")
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500



# Run the Flask app (start the server)
if __name__ == '__main__':
    app.run(debug=True)
#code