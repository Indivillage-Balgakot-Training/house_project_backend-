from flask import Flask, jsonify, redirect, url_for, request, make_response
from flask_pymongo import PyMongo
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)

# MongoDB connection URI
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

# Secret key for session management (needed to sign cookies)
app.secret_key = 'your-secret-key-here'

@app.route('/', methods=['GET'])
def home():
    return redirect(url_for('get_houses'))

# Helper function to get the session_id from cookies (or generate one if missing)
def get_session_id():
    session_id = request.cookies.get('session_id')
    if not session_id:
        # Generate a new session ID if not found in cookies
        session_id = str(uuid.uuid4())
    return session_id

@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        # Fetch houses from the database
        houses = mongo.db.houses.find()
        house_list = [
            {'id': str(house['_id']), 'name': house['name'], 'image': house.get('image', ''), 'description': house.get('description', '')}
            for house in houses
        ]
        return jsonify(house_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/houses/<string:house_id>/rooms', methods=['GET'])
def get_rooms(house_id):
    try:
        # Fetch rooms associated with a specific house_id
        rooms = mongo.db.rooms.find({'house_id': house_id})
        room_list = [
            {'id': str(room['_id']), 'name': room['name'], 'color_options': room['color_options'], 'image': room.get('image', '')}
            for room in rooms
        ]
        return jsonify(room_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/select-house', methods=['POST'])
def select_house():
    data = request.get_json()  # Get the incoming data

    session_id = get_session_id()  # Retrieve the session ID (either from cookie or newly generated)
    house_id = data.get('house_id')  # Get the house_id from the data
    house_name = data.get('house_name')  # Get the house_name from the data

    # Check if house_id and house_name are provided
    if not house_id or not house_name:
        return jsonify({'error': 'House ID and house name are required.'}), 400

    try:
        # Store the house_name and house_id with the session_id
        mongo.db.user_choices.update_one(
            {'session_id': session_id},  # Check if this session already exists
            {'$set': {'house_id': house_id, 'house_name': house_name}},  # Set house_id and house_name for this session
            upsert=True  # If no session exists, create a new one
        )
        
        # Log success
        print(f"House selected: {house_name} with ID {house_id} for session {session_id}")
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Create response to set the session_id cookie
    response = jsonify({'session_id': session_id, 'house_id': house_id, 'house_name': house_name})
    
    # Set the session_id in the cookie for future requests
    response.set_cookie('session_id', session_id, max_age=60*60*24, httponly=True)

    return response, 201  # Return the response with status 201

@app.route('/select-room', methods=['POST'])
def select_room():
    data = request.get_json()  # Get the incoming data
    print("Incoming data:", data)  # Log incoming request data for debugging

    session_id = get_session_id()  # Retrieve the session ID from cookie (or newly generated)

    room_type = data.get('room_type')  # Only accept room_type as the data

    # Validate that room_type is provided
    if not session_id or not room_type:
        return jsonify({'error': 'Session ID and room_type are required.'}), 400

    try:
        # Update the user_choices collection with the house_name, house_id, and room_type
        result = mongo.db.user_choices.update_one(
            {'session_id': session_id},  # Find the user session by session_id
            {
                '$set': {  # Set the room_type, house_name, and house_id directly in the document
                    'room_type': room_type  # Store only room_type along with existing house details
                }
            },
            upsert=True  # If no session exists, create a new one
        )

        if result.modified_count == 0:
            return jsonify({'error': 'Failed to update the room type data.'}), 500
        
        # Log success
        print(f"Room type selected: {room_type} for session {session_id}")
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'Room type selected successfully!'}), 201

@app.route('/kitchen/images', methods=['GET'])
def get_kitchen_images():
    kitchen_images = [
        {'name': 'Default', 'image': '/images/kitchen.jpg', 'color': '#FAF0E6'},
        {'name': 'Caramel', 'image': '/images/kitchenCabinet1.jpg', 'color': '#D2B48C'},
        {'name': 'Yellow', 'image': '/images/kitchenCabinet2.jpg', 'color': '#FFD700'},
        {'name': 'Neon Pink', 'image': '/images/kitchenCabinet3.jpg', 'color': '#E37383'},
    ]
    
    wall_images = [
        {'name': 'Pale Green', 'image': '/images/Wall1.jpg', 'color': '#b0c8bf'},
        {'name': 'Pale Olive', 'image': '/images/Wall2.jpg', 'color': '#FFB6C1'},
        {'name': 'Warm Beige', 'image': '/images/Wall3.jpg', 'color': '#c8bca6'},
    ]
    
    basin_images = [  
        {'name': 'Stainless Steel', 'image': '/images/kitchen.jpg', 'color': '#C0C0C0'},
    ]

    combined_images = {
        'cabinets': kitchen_images,
        'walls': wall_images,
        'basins': basin_images
    }
    
    return jsonify(combined_images)

if __name__ == '__main__':
    app.run(debug=True)
