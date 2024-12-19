import uuid
import os
from flask import Flask, jsonify, request, session, make_response
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime, timedelta
import logging

# Initialize Flask application (this sets up the web server)
app = Flask(__name__)

# Set a secret key for session management (this key helps secure user sessions, so users' data stays safe)
app.secret_key = os.urandom(24)  # Generates a random secret key for securing session cookies

# Enable Cross-Origin Resource Sharing (CORS) with credentials
# This allows the app to share data across different websites while keeping the user's session secure
CORS(app, supports_credentials=True)

# MongoDB connection configuration (this connects the app to a MongoDB database to store and retrieve data)
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)  # Setting up the MongoDB connection using Flask-PyMongo

# Session settings to ensure persistence across requests (this keeps the user logged in even if they refresh the page)
app.config.update(
    SESSION_COOKIE_NAME='session_id',  # Name for the session cookie, used to identify the user
    SESSION_COOKIE_HTTPONLY=True,  # Makes sure cookies can't be accessed through JavaScript, improving security
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),  # The session lasts for 30 days
    SESSION_COOKIE_DOMAIN='.localhost',  # Allow session cookie on subdomains (useful for local development)
    SESSION_COOKIE_SAMESITE='None',  # Allows cookies to be sent across different domains
    SESSION_COOKIE_SECURE=False  # Don't require a secure (HTTPS) cookie for local development
)

# Function to generate and retrieve a unique session ID for each user
def get_session_id():
    if 'session_id' not in session:  # If no session ID exists in the session data
        session.permanent = True  # Keep the session active even after the browser is closed
        session['session_id'] = str(uuid.uuid4())  # Generate a new unique session ID (UUID)
    return session['session_id']  # Return the session ID for the current user

# Function to unlock houses whose lock has expired (checking if a house is still locked)
def unlock_expired_houses():
    # Find all houses that have an active lock
    locked_houses = mongo.db.houses.find({"locked": {"$ne": None}})

    # Set the lock expiration time (e.g., 10 seconds for testing purposes)
    lock_timeout = timedelta(seconds=10)

    # Loop through each house to check if its lock has expired
    for house in locked_houses:
        locked_at = house.get('locked_at')  # Get the time when the house was locked
        if locked_at and (datetime.utcnow() - locked_at) > lock_timeout:  # Check if the lock has expired
            # If the lock has expired, remove the lock from the house
            mongo.db.houses.update_one(
                {"house_id": house['house_id']},  # Find the house by its unique ID
                {"$set": {"locked": None, "locked_at": None}}  # Clear the lock and its timestamp
            )

# Route to get the list of available houses
@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        unlock_expired_houses()  # Ensure any expired locks are cleared before fetching the house list

        session_id = get_session_id()  # Get the session ID to track the current user

        if not session_id:  # If no session ID exists, return an error
            return jsonify({"error": "Session ID is missing"}), 400

        # Retrieve all houses from the database
        houses = mongo.db.houses.find()

        houses_list = []  # List to store available houses

        # Loop through each house and check if it's locked by another user
        for house in houses:
            house_id = house.get('house_id')  # Get the unique ID of the house

            # Check if the house is locked by someone else
            if house.get('locked') and house['locked'] != session_id:
                # If the house is locked by another user, skip it and don't add it to the list
                continue

            house_locked = house.get('locked') is not None and house['locked'] == session_id  # Check if the house is locked by the current user

            # Add house details to the list (e.g., name, image, description, and whether it is locked)
            houses_list.append({
                'house_id': house_id,
                'house_name': house.get('house_name'),
                'house_image': house.get('house_image', ''),
                'description': house.get('description', ''),
                'locked': house_locked,  # Indicate if the house is locked by the current user
            })

        return jsonify(houses_list)  # Return the list of houses as a JSON response

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return an error if something goes wrong

# Route to lock a house for the current user
@app.route('/select-house', methods=['POST'])
def select_house():
    try:
        session_id = get_session_id()  # Get the session ID to track which user is making the request

        data = request.get_json()  # Get the data from the request body (house_id of the selected house)
        house_id = data.get('house_id')  # Extract the house ID from the request data

        # Check if the house is already locked by another user
        house = mongo.db.houses.find_one({"house_id": house_id})

        if house and house.get('locked'):  # If the house is locked
            if house['locked'] != session_id:  # If the house is locked by someone else
                return jsonify({"error": "This house is already locked by another user"}), 400  # Return an error

        # Lock the house for the current session by updating its 'locked' field
        mongo.db.houses.update_one(
            {"house_id": house_id},  # Find the house by its unique ID
            {"$set": {"locked": session_id, "locked_at": datetime.utcnow()}}  # Lock the house and record the time
        )

        return jsonify({
            "message": "House selected successfully",
            "session_id": session_id,
            "house_id": house_id,
        })  # Return a success message with session and house ID

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return an error if something goes wrong

# Route to unlock houses and end the session
@app.route('/exit', methods=['POST'])
def exit_website():
    try:
        data = request.get_json()  # Get the data from the request body (house_id and session_id)
        house_id = data.get("house_id")
        session_id = data.get("session_id")

        if not house_id or not session_id:  # If house ID or session ID is missing
            return jsonify({"error": "House ID and Session ID are required"}), 400

        # Find and unlock all houses locked by the session (user)
        locked_houses = mongo.db.houses.find({"locked": session_id})

        for house in locked_houses:
            mongo.db.houses.update_one(
                {"house_id": house['house_id']},  # Find the house by its ID
                {"$set": {"locked": None, "locked_at": None}}  # Clear the lock and unlock the house
            )

        # Clear the session data (logging the user out)
        session.clear()

        return jsonify({"message": "House unlocked and session ended"}), 200  # Return a success message

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return an error if something goes wrong

# Route to get the layout and rooms of a specific house
@app.route('/rooms/<house_id>', methods=['GET'])
def get_rooms(house_id):
    try:
        # Fetch the house layout for the given house ID from the database
        house_layout = mongo.db.layout.find_one({"house_id": house_id})

        if not house_layout:  # If the layout is not found
            return jsonify({"error": "House layout not found"}), 404  # Return an error

        rooms_data = house_layout.get('rooms', [])  # Get the list of rooms in the house layout
        rooms_image = house_layout.get('rooms_image', '')  # Get the image of the rooms, if any

        return jsonify({
            "rooms_image": rooms_image,  # Return the rooms image (if any)
            "rooms": rooms_data  # Return the list of rooms in the house
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return an error if something goes wrong

# Route to get data for a specific room in a house
@app.route('/room-data', methods=['GET'])
def get_room_data():
    try:
        session_id = get_session_id()  # Get the session ID for the current user

        # Get room and house details from query parameters
        room_name = request.args.get('room_name')
        house_id = request.args.get('house_id')

        if not house_id or not room_name:  # If house ID or room name is missing
            return jsonify({"error": "house_id and room_name are required parameters"}), 400

        # Fetch room data for the given house and room name from the database
        room_data = mongo.db.rooms.find_one({"house_id": house_id, "rooms.room_name": room_name})

        if room_data:  # If room data is found
            # Find the specific room from the list of rooms in the house
            room = next((r for r in room_data.get("rooms", []) if r["room_name"] == room_name), None)

            if room:
                room_images = room.get("images", [])  # Get the images for the room

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

                return jsonify(room_data), 200  # Return the room data in JSON format
            else:
                return jsonify({"error": f"Room '{room_name}' not found in house '{house_id}'"}), 404
        else:
            return jsonify({"error": f"House '{house_id}' or room '{room_name}' not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return an error if something goes wrong


# Route to select rooms and update preferences (like colors)
@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        session_id = get_session_id()  # Get the session ID for the current user

        # Get the data from the request body (selected rooms and their preferences)
        data = request.get_json()
        house_id = data.get('house_id')
        session_id_from_request = data.get('session_id')  # The session ID passed with the request
        selected_rooms = data.get('selected_rooms')  # The list of rooms selected by the user
        cabinet_colors = data.get('cabinet_colors', [])  # Default empty if not provided
        wall_colors = data.get('wall_colors', [])
        basin_colors = data.get('basin_colors', [])
        wardrobe_colors = data.get('wardrobe_colors', [])  # Specific to bedroom
        ceiling_colors = data.get('ceiling_colors', [])  # Specific to living room

        if not house_id or not session_id_from_request or not selected_rooms:  # If required data is missing
            return jsonify({"error": "Missing house_id, session_id, or selected_rooms"}), 400

        update_data = {
            'selected_rooms': selected_rooms,  # Update the list of selected rooms
        }

        # Update room-specific preferences based on the room type
        if 'bedroom' in selected_rooms:
            update_data['wardrobe_colors'] = wardrobe_colors
            update_data['wall_colors'] = wall_colors
        elif 'living room' in selected_rooms:
            update_data['ceiling_colors'] = ceiling_colors  # Add ceiling colors for living room
            update_data['wall_colors'] = wall_colors
        else:
            update_data['cabinet_colors'] = cabinet_colors
            update_data['basin_colors'] = basin_colors
            update_data['wall_colors'] = wall_colors

        # Log the update data for debugging purposes
        print(f"Update data: {update_data}")

        # MongoDB update query to save the user's preferences for the selected rooms
        result = mongo.db.user_selection.update_one(
            {'session_id': session_id_from_request, 'house_id': house_id},
            {'$set': update_data},  # Set the new preferences in the database
            upsert=True  # If no existing data, create new record
        )

        if result.matched_count > 0 or result.upserted_id:
            return jsonify({"message": "Room selection updated successfully"}), 200
        else:
            return jsonify({"error": "House not found or session mismatch"}), 404  # If no matching record found

    except Exception as e:
        print(f"Error: {str(e)}")  # Log any errors that occur
        return jsonify({"error": str(e)}), 500  # Return an error if something goes wrong


# Route to fetch user selections for a house
@app.route('/user-selection', methods=['GET'])
def get_room_selection():
    try:
        session_id = get_session_id()  # Get the session ID for the current user

        house_id = request.args.get('house_id')  # Get the house ID from the request query parameters

        if not house_id or not session_id:  # If either house ID or session ID is missing
            return jsonify({"error": "Missing house_id or session_id"}), 400

        # Fetch user room selections from the database
        user_selection = mongo.db.user_selection.find_one({'session_id': session_id, 'house_id': house_id})

        if not user_selection:  # If no selection is found for the user and house
            return jsonify({"error": "No previous selection found for this house and user"}), 404

        # Prepare the response data with selected rooms and colors
        selection_data = {
            'selected_rooms': user_selection.get('selected_rooms', []),
        }

        # Include the selected color preferences for each room type
        if 'cabinet_colors' in user_selection:
            selection_data['cabinet_colors'] = user_selection['cabinet_colors']
        if 'wall_colors' in user_selection:
            selection_data['wall_colors'] = user_selection['wall_colors']
        if 'basin_colors' in user_selection:
            selection_data['basin_colors'] = user_selection['basin_colors']
        if 'wardrobe_colors' in user_selection:
            selection_data['wardrobe_colors'] = user_selection['wardrobe_colors']

        return jsonify(selection_data), 200  # Return the selection data as a JSON response

    except Exception as e:
        print(f"Error: {str(e)}")  # Log any errors that occur
        return jsonify({"error": str(e)}), 500  # Return an error if something goes wrong


# Start the Flask application (this runs the web server)
if __name__ == '__main__':
    app.run(debug=True)
