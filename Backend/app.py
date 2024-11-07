import uuid
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from flask_cors import CORS  # Import CORS

app = Flask(__name__)

# Enable CORS for all domains (or you can specify the frontend URL like 'http://localhost:3000')
CORS(app)

# MongoDB connection setup
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

@app.route('/houses', methods=['GET'])
def get_houses():
    # Fetch houses from the database
    houses = mongo.db.houses.find()
    houses_list = []

    # Fetch the selected rooms for each house from the 'user_selection' collection
    user_selections = mongo.db.user_selection.find()

    # Create a dictionary for easy look-up of selected rooms by house_id
    selected_rooms_by_house = {}
    for selection in user_selections:
        selected_rooms_by_house[selection['house_id']] = selection.get('selected_rooms', [])

    # Convert the MongoDB cursor to a list of dictionaries
    for house in houses:
        # If house_id is null, generate a UUID
        house_id = house.get('house_id') or str(uuid.uuid4())

        # Get the selected rooms for the house (if any)
        selected_rooms = selected_rooms_by_house.get(house_id, [])

        houses_list.append({
            'house_id': house_id,
            'house_name': house.get('house_name', 'Unnamed House'),
            'house_image': house.get('house_image', '/image2.jpg'),
            'selected_rooms': selected_rooms  # Include the selected rooms
        })

    return jsonify(houses_list)

@app.route('/select-house', methods=['POST'])
def select_house():
    try:
        data = request.json
        house_id = data.get('house_id')
        house_name = data.get('house_name')
        selected_rooms = data.get('selected_rooms', [])

        # Ensure house_id is not null; if it's missing, generate a UUID
        if not house_id:
            house_id = str(uuid.uuid4())  # Generate a UUID if no house_id is provided

        # Create the selection object
        selection = {
            "house_id": house_id,
            "house_name": house_name,
        }

        # Insert the selection into the user_selection collection
        mongo.db.user_selection.update_one(
            {"house_id": house_id},  # Use house_id as the unique key
            {"$set": selection},  # Update the selection with the new data
            upsert=True  # If the house doesn't exist in the selection, insert it
        )
        
        return jsonify({"message": f"House '{house_name}' selected successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/layout', methods=['GET'])
def get_layout():
    # Fetch layout from the database
    layout = mongo.db.layout.find()  # Access the 'layout' collection
    layout_list = []
    
    # Convert the MongoDB cursor to a list of dictionaries
    for item in layout:
        layout_list.append({
            'house_id': item.get('house_id'),
            'rooms_image': item.get('rooms_image', '/default_image.jpg'),  # Default to '/default_image.jpg' if missing
            'rooms': item.get('rooms', []),  # Default to empty list if 'rooms' field is missing
        })
    
    return jsonify(layout_list)

@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        # Get the data from the request
        data = request.json
        house_id = data.get('house_id')  # The ID of the house
        selected_rooms = data.get('selected_rooms', [])  # List of rooms the user selects (default to empty list)

        # Validate the data
        if not house_id:
            return jsonify({"error": "House ID is required"}), 400

        if not selected_rooms:
            return jsonify({"error": "At least one room must be selected"}), 400

        # Fetch the current selection for the house (if any)
        user_selection = mongo.db.user_selection.find_one({"house_id": house_id})

        if user_selection:
            # If the house already exists in the selection, update the selected rooms
            current_selected_rooms = user_selection.get("selected_rooms", [])
            updated_rooms = list(set(current_selected_rooms + selected_rooms))  # Combine and remove duplicates

            # Update the selected rooms field with the new list of rooms
            mongo.db.user_selection.update_one(
                {"house_id": house_id},  # Match on the house_id
                {"$set": {"selected_rooms": updated_rooms}},  # Update the selected_rooms field
            )
            return jsonify({"message": f"Rooms selected for House ID {house_id}: {', '.join(updated_rooms)}"}), 200
        else:
            # If no selection exists for the house, create a new selection document
            mongo.db.user_selection.insert_one({
                "house_id": house_id,
                "house_name": data.get('house_name', ''),  # Store the house_name in the new selection document
                "selected_rooms": selected_rooms
            })
            return jsonify({"message": f"Rooms selected for House ID {house_id}: {', '.join(selected_rooms)}"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
