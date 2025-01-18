import os
import uuid
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from flask_cors import CORS

# Initialize Flask application
app = Flask(__name__)

# Enable Cross-Origin Resource Sharing (CORS) with credentials
CORS(app, supports_credentials=True)

# MongoDB connection configuration
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        # Fetch houses from MongoDB
        houses = mongo.db.houses.find()  # Directly fetch from the database
        houses_list = []
        for house in houses:
            house_id = house.get('house_id')
            house_locked = house.get('locked') is not None

            houses_list.append({
                'house_id': house_id,
                'house_name': house.get('house_name'),
                'house_image': house.get('house_image', ''),
                'description': house.get('description', ''),
                'locked': house_locked,
            })

        return jsonify(houses_list)  # Return the list of houses

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/rooms/<house_id>', methods=['GET'])
def get_layout(house_id):
    try:
        # Fetch the house layout from MongoDB using house_id
        house_layout = mongo.db.houses.find_one({"house_id": house_id})

        if not house_layout:
            return jsonify({"error": "House layout not found"}), 404

        # Generate a session ID
        session_id = str(uuid.uuid4())

        # Lock the house and set the session ID
        mongo.db.houses.update_one(
            {"house_id": house_id},
            {"$set": {"locked": True, "session_id": session_id}}
        )

        # Prepare the response data (including rooms, areas, and images)
        rooms_data = house_layout.get('rooms', [])
        rooms_image = house_layout.get('rooms_image', '')

        # Format the layout response with rooms and their areas
        layout_response = {
            "session_id": session_id,
            "house_id": house_id,
            "rooms_image": rooms_image,
            "rooms": []
        }

        for room in rooms_data:
            room_data = {
                "name": room.get('name'),
                "areas": []
            }

            for area in room.get('areas', []):
                area_data = {
                    "name": area.get('name'),
                    "left": area.get('left'),
                    "top": area.get('top'),
                    "width": area.get('width'),
                    "height": area.get('height'),
                    "color": area.get('color', '')  # Send color if present
                }
                room_data["areas"].append(area_data)
            
            # If there are images related to the room (like kitchen images), include them as well
            if room.get('images'):
                room_data["images"] = room.get('images')
            
            layout_response["rooms"].append(room_data)

        return jsonify(layout_response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True)
