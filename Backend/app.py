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

        houses = mongo.db.houses.find()
        houses_list = []

        # Fetch user-specific selections based on session_id
        user_selections = mongo.db.user_selection.find({"session_id": session_id})

        selected_rooms_by_house = {}
        for selection in user_selections:
            selected_rooms_by_house[selection['house_id']] = selection.get('selected_rooms', [])

        for house in houses:
            house_id = house.get('house_id') or str(uuid.uuid4())

            selected_rooms = selected_rooms_by_house.get(house_id, [])

            houses_list.append({
                'house_id': house_id,
                'house_name': house.get('house_name', 'Unnamed House'),
                'house_image': house.get('house_image', '/image2.jpg'),
                'selected_rooms': selected_rooms
            })

        return jsonify(houses_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/select-house', methods=['POST'])
def select_house():
    try:
        # Ensure the user has a session ID
        session_id = get_session_id()

        data = request.json
        house_id = data.get('house_id')
        house_name = data.get('house_name')
        selected_rooms = data.get('selected_rooms', [])

        if not house_id:
            house_id = str(uuid.uuid4())

        # Prepare the selection data
        selection = {
            "house_id": house_id,
            "house_name": house_name,
            "selected_rooms": selected_rooms,
            "session_id": session_id  # Store the session ID for the user
        }

        # Check if the house and session already exist
        existing_selection = mongo.db.user_selection.find_one({"house_id": house_id, "session_id": session_id})

        if existing_selection:
            # If record exists, update it with the new selected_rooms
            mongo.db.user_selection.update_one(
                {"house_id": house_id, "session_id": session_id},
                {"$set": selection},  # Update the house selection data
            )
            return jsonify({"message": f"House '{house_name}' updated successfully!"}), 200
        else:
            # If no record exists, insert a new one
            mongo.db.user_selection.insert_one(selection)
            return jsonify({"message": f"House '{house_name}' selected successfully!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/layout', methods=['GET'])
def get_layout():
    try:
        # Ensure the user has a session ID
        session_id = get_session_id()

        layout = mongo.db.layout.find()
        layout_list = []

        for item in layout:
            layout_list.append({
                'house_id': item.get('house_id'),
                'rooms_image': item.get('rooms_image', '/default_image.jpg'),
                'rooms': item.get('rooms', []),
            })

        return jsonify(layout_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        # Ensure the user has a session ID
        session_id = get_session_id()

        # Log the incoming data to verify what is being sent
        data = request.json
        print(f"Received data: {data}")  # Log the received data

        house_id = data.get('house_id')
        house_name = data.get('house_name')
        selected_rooms = data.get('selected_rooms', [])

        # Ensure house_id and selected_rooms are provided
        if not house_id:
            return jsonify({"error": "House ID is required"}), 400

        if not selected_rooms:
            return jsonify({"error": "At least one room must be selected"}), 400

        # Check if the house exists in user selection
        user_selection = mongo.db.user_selection.find_one({"house_id": house_id, "session_id": session_id})

        if user_selection:
            # Merge the new selected rooms with the current ones, removing duplicates
            current_selected_rooms = user_selection.get("selected_rooms", [])
            updated_rooms = list(set(current_selected_rooms + selected_rooms))

            # Log the updated rooms before updating the database
            print(f"Updated rooms for house {house_id}: {updated_rooms}")

            # Update the user selection with the new list of selected rooms
            mongo.db.user_selection.update_one(
                {"house_id": house_id, "session_id": session_id},
                {"$set": {"selected_rooms": updated_rooms}},  # Update the rooms
            )
            return jsonify({"message": f"Rooms selected for House ID {house_id}: {', '.join(updated_rooms)}"}), 200
        else:
            # If no existing selection for this house, create a new entry
            mongo.db.user_selection.insert_one({
                "house_id": house_id,
                "house_name": house_name,  # Save house_name as well
                "selected_rooms": selected_rooms,
                "session_id": session_id,  # Store the session_id for the user
            })
            return jsonify({"message": f"Rooms selected for House ID {house_id}: {', '.join(selected_rooms)}"}), 201

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/kitchen-data', methods=['GET'])
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
