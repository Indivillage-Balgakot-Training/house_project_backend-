import uuid
import os
from flask import Flask, jsonify, request, session
from flask_pymongo import PyMongo
from flask_cors import CORS

app = Flask(__name__)

# Set the secret key to enable session management
app.secret_key = os.urandom(24)  # Secure random key for session encryption

# Enable CORS for all domains (or you can specify the frontend URL like 'http://localhost:3000')
CORS(app)

# MongoDB connection setup
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

# Ensure that each user has a session ID
def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())  # Create a new session ID if it doesn't exist
    return session['session_id']


@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        # Ensure the user has a session ID
        session_id = get_session_id()

        if not session_id:
            # Return an error if no session ID is found
            return jsonify({"error": "Session ID is missing"}), 400

        # Fetch all houses from MongoDB
        houses = mongo.db.houses.find()
        houses_list = []

        # Fetch user-specific room selections based on session_id
        user_selections = mongo.db.user_selection.find({"session_id": session_id})

        # Create a dictionary of selected rooms per house for the user
        selected_rooms_by_house = {selection['house_id']: selection.get('selected_rooms', []) for selection in user_selections}

        for house in houses:
            house_id = house.get('house_id') or str(uuid.uuid4())  # Generate a new UUID if missing

            # Get selected rooms for the current house, defaulting to an empty list if none
            selected_rooms = selected_rooms_by_house.get(house_id, [])

            # Build the house response object
            houses_list.append({
                'house_id': house_id,
                'house_name': house.get('house_name'),
                'house_image': house.get('house_image', '/image2.jpg'),
            })

        # Return the list of houses
        return jsonify(houses_list)

    except Exception as e:
        # Return a detailed error message
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/select-house', methods=['POST'])
def select_house():
    try:
        # Get session ID from the user's session
        session_id = get_session_id()  # This assumes you have a method to fetch the session ID

        # Get house details from the request body
        data = request.get_json()
        house_id = data.get('house_id')

        # Respond with confirmation
        return jsonify({
            "message": "House selected successfully",
            "session_id": session_id,
            "house_id": house_id,

        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/rooms/<house_id>', methods=['GET'])
def get_rooms(house_id,):
    try:
        # Fetch house layout based on house_id and house_name
        house_layout = mongo.db.layout.find_one({"house_id": house_id, })
        
        if not house_layout:
            return jsonify({"error": "House layout not found"}), 404
        
        rooms_data = house_layout.get('rooms', [])
        rooms_image = house_layout.get('rooms_image', '/image2.jpg')  # Default image if none provided

        return jsonify({
            "rooms_image": rooms_image,
            "rooms": rooms_data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        # Get session ID from the user's session
        session_id = get_session_id()

        # Get the room details from the request body
        data = request.get_json()
        house_id = data.get('house_id')
        session_id = data.get('session_id')  # Make sure we get session_id from request body if it's passed
        selected_rooms = data.get('selected_rooms')

        if not house_id or not session_id or not selected_rooms:
            return jsonify({"error": "Missing house_id, session_id, or selected_rooms"}), 400

        # Use MongoDB update with $addToSet to prevent duplicates in the selected_rooms array
        result = mongo.db.user_selection.update_one(
            {'session_id': session_id, 'house_id': house_id},  # Find document by session_id and house_id
            {'$addToSet': {'selected_rooms': {'$each': selected_rooms}}},  # Add new room(s) without duplicates
            upsert=True  # Insert the document if it doesn't exist
        )

        # Check result of MongoDB operation
        if result.matched_count == 0:
            print(f"New document created for session_id {session_id} and house_id {house_id}")
        else:
            print(f"Document updated for session_id {session_id} and house_id {house_id}")

        return jsonify({
            "message": "Room selected successfully",
            "session_id": session_id,
            "house_id": house_id,
            "selected_rooms": selected_rooms
        })

    except Exception as e:
        print(f"Error inserting data into MongoDB: {str(e)}")  # Log the error
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500



@app.route('/room-data', methods=['GET'])
def get_kitchen_data():
    try:
        # Ensure the user has a session ID
        session_id = get_session_id()

        # Get room_name (e.g., 'Kitchen') from query parameters
        room_name = request.args.get('room_name', 'Kitchen')  # Default to 'Kitchen' if no room_name is provided

        # Fetch the room data for the specified room_name
        room_data = mongo.db.rooms.find_one({"room_name": room_name})

        # If room is found, return its data
        if room_data:
            kitchen_data = {
                "room_name": room_data["room_name"],
                "images": room_data["images"],
                "cabinet_colors": room_data["images"][0].get("cabinet_colors", []),
                "wall_colors": room_data["images"][0].get("wall_colors", []),
                "basin_colors": room_data["images"][0].get("basin_colors", [])
            }
            return jsonify(kitchen_data), 200
        else:
            # Use an f-string for string formatting (this is the correct approach)
            return jsonify({"error": f"{room_name} data not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
