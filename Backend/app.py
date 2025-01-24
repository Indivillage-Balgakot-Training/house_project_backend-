from flask import Flask, request, jsonify, session  # Add session here
import uuid  # Import uuid for generating unique session IDs
from datetime import datetime
from flask_cors import CORS
from flask_pymongo import PyMongo

# Initialize Flask app and MongoDB
app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

# Enable CORS for specific origin (your frontend URL)
CORS(app, supports_credentials=True, )

app.secret_key = 'Indivillage@bgk'  # Change to a strong secret key

def get_session_id():
    """Generate or retrieve the session ID."""
    if 'session_id' not in session:  # If no session ID exists in the session data
        session.permanent = True  # Keep the session active even after the browser is closed
        session['session_id'] = str(uuid.uuid4())  # Generate a new unique session ID (UUID)
    return session['session_id']  # Return the session ID

@app.route('/houses', methods=['GET'])
def get_houses():
    # Fetch available houses (not locked)
    houses_collection = mongo.db.houses  # Reference to the houses collection
    available_houses = houses_collection.find({"locked_by": None})  # Only fetch houses that are not locked
    
    # Convert the Mongo cursor to a list of dictionaries
    house_list = [
        {
            "house_id": house["house_id"],
            "house_name": house["house_name"],
            "house_image": house["house_image"],
            "description": house["description"],
        }
        for house in available_houses
    ]
    
    # If no houses are available, return an error message
    if not house_list:
        return jsonify({"status": "error", "message": "No available houses"}), 404
    
    return jsonify(house_list)


@app.route('/select-house', methods=['GET'])
def select_house():
    session_id = request.args.get('session_id')
    house_id = request.args.get('house_id')

    if not session_id or not house_id:
        return jsonify({"status": "error", "message": "Missing session_id or house_id"}), 400

    # Check if the house exists and is not locked
    houses_collection = mongo.db.houses  # Reference to the houses collection
    house = houses_collection.find_one({"house_id": house_id})
    
    if not house:
        return jsonify({"status": "error", "message": "House not found"}), 404

    if house.get("locked_by"):
        return jsonify({"status": "error", "message": "House already locked"}), 400

    # Lock the house for the current session
    locked_at = datetime.now()
    houses_collection.update_one(
        {"house_id": house_id},
        {"$set": {"locked_by": session_id, "locked_at": locked_at}}
    )

    return jsonify({
        "status": "ok",
        "session_id": session_id,
        "house_id": house_id,
        "locked_at": locked_at.strftime('%Y-%m-%d %H:%M:%S'),
    })


@app.route('/rooms/<house_id>', methods=['GET'])
def get_layout(house_id):
    try:
        # Fetch the house layout from MongoDB using house_id
        house_layout = mongo.db.houses.find_one({"house_id": house_id})

        if not house_layout:
            return jsonify({"error": "House layout not found"}), 404

        # Generate a session ID
        session_id = str(uuid.uuid4())

        # Prepare the response data (including rooms, areas, and images)
        rooms_data = house_layout.get('rooms', {})
        rooms_image = house_layout.get('rooms_image', '')

        # Format the layout response with rooms and their areas
        layout_response = {
            "session_id": session_id,
            "house_id": house_id,
            "rooms_image": rooms_image,
            "rooms": []
        }

        for room_name, room in rooms_data.items():
            room_data = {
                "name": room_name,
                "areas": []
            }

            # Extract layout page details (assuming this is equivalent to areas)
            layout_page_details = room.get('layout_page_details', {})
            if layout_page_details:
                area_data = {
                    "name": room_name,  # Use room name as area name
                    "left": layout_page_details.get('left', 0),
                    "top": layout_page_details.get('top', 0),
                    "width": layout_page_details.get('width', 0),
                    "height": layout_page_details.get('height', 0),
                    "color": layout_page_details.get('color', '')  # Send color if present
                }
                room_data["areas"].append(area_data)
            
            # If there are images related to the room, include them as well
            if room.get('image_path'):
                room_data["image_path"] = room.get('image_path')

            layout_response["rooms"].append(room_data)

        return jsonify(layout_response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@app.route('/room-data_dev', methods=['GET'])
def get_room_data():
    try:
        # Get the query parameters from the request
        house_id = request.args.get('house_id')
        session_id = request.args.get('session_id')
        room_name = request.args.get('room_name')

        # Validate input
        if not house_id or not session_id or not room_name:
            return jsonify({"status": "error", "message": "Missing house_id, session_id, or room_name"}), 400

        # Fetch the house data from the database based on house_id
        houses_collection = mongo.db.houses  # Reference to the houses collection
        house = houses_collection.find_one({"house_id": house_id})

        if not house:
            return jsonify({"status": "error", "message": "House not found"}), 404

        # Check if the house is locked by the current session_id
        if house.get("locked_by") != session_id:
            return jsonify({"status": "error", "message": "House is not locked by your session"}), 400

        # Fetch the specific room data from the house based on room_name
        rooms = house.get('rooms', {})
        room_data = rooms.get(room_name)

        if not room_data:
            return jsonify({"status": "error", "message": "Room not found"}), 404

        # Prepare the response data (colors and images for wall, ceiling, etc.)
        images = []
        for category, color_data in room_data.get('color_categories', {}).items():
            color_category = {
                "key": category,
                "label": color_data['label'],
                "colors": [
                    {"color": color['color'], "image": color['image']} for color in color_data['colors']
                ],
                "selected_color": color_data.get('selected_color', None)
            }
            images.append(color_category)

        # Construct the response with images and room data
        response_data = {
            "images": images,
            "image_path": room_data.get('image_path', ''),  # Image for the room (like a thumbnail)
            "room_name": room_name
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
