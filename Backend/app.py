from flask import Flask, request, jsonify, session  # Import necessary modules, including session management
import uuid  # Import uuid to generate unique session IDs
from datetime import datetime  # Import datetime for handling timestamps
from flask_cors import CORS  # Import CORS for cross-origin resource sharing (CORS) handling
from flask_pymongo import PyMongo  # Import PyMongo for MongoDB integration with Flask

# Initialize the Flask app and configure MongoDB URI
app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)  # Set up the PyMongo instance to interact with MongoDB

# Enable CORS for specific origins (your frontend URL) to allow cross-origin requests
CORS(app, supports_credentials=True)

app.secret_key = 'Indivillage@bgk'  # Set a strong secret key for Flask's session management

# Function to generate or retrieve a session ID
def get_session_id():
    """Generate or retrieve the session ID."""
    if 'session_id' not in session:  # If no session ID exists in the session data
        session.permanent = True  # Keep the session active even after the browser is closed
        session['session_id'] = str(uuid.uuid4())  # Generate a new unique session ID (UUID)
    return session['session_id']  # Return the session ID

# Route to fetch all houses that are not locked
@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        # Reference to the houses collection in MongoDB
        houses_collection = mongo.db.houses

        # Fetch all houses (no filtering by locked status in MongoDB)
        all_houses = houses_collection.find()

        # Initialize an empty list to hold the available houses
        house_list = []

        for house in all_houses:
            # Check if the house is not locked (locked is None)
            if house.get("locked") is None:
                # If it's not locked, add it to the list with necessary fields
                house_data = {
                    "house_id": house.get("house_id"),
                    "house_name": house.get("house_name"),
                    "house_image": house.get("house_image"),
                    "description": house.get("description"),
                }
                house_list.append(house_data)  # Add the house data to the list

        # If no houses are available, return an error message
        if not house_list:
            return jsonify({"status": "error", "message": "No available houses"}), 404

        return jsonify(house_list), 200  # Return the list of available houses

    except Exception as e:
        # In case of any unexpected errors, return a 500 error with a message
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500


# Route to handle house selection by a user
@app.route('/select-house', methods=['GET'])
def select_house():
    session_id = request.args.get('session_id')  # Get session ID from query parameters
    house_id = request.args.get('house_id')  # Get house ID from query parameters

    # Check if both session_id and house_id are provided
    if not session_id or not house_id:
        return jsonify({"status": "error", "message": "Missing session_id or house_id"}), 400

    # Check if the house exists and is not locked
    houses_collection = mongo.db.houses  # Reference to the houses collection
    house = houses_collection.find_one({"house_id": house_id})
    
    if not house:  # If house doesn't exist
        return jsonify({"status": "error", "message": "House not found"}), 404

    if house.get("locked_by"):  # If the house is already locked by someone else
        return jsonify({"status": "error", "message": "House already locked"}), 400

    # Lock the house for the current session
    locked_at = datetime.now()  # Get the current timestamp when the house is locked
    print(house_id)  # For debugging: Print the house ID
    print(session_id)  # For debugging: Print the session ID
    houses_collection.update_one(
        {"house_id": house_id},  # Find the house with the given house_id
        {"$set": {"locked_by": session_id, "locked_at": locked_at}}  # Lock the house by setting locked_by and locked_at
    )

    return jsonify({
        "status": "ok",
        "session_id": session_id,  # Return session ID and house ID in the response
        "house_id": house_id,
        "locked_at": locked_at.strftime('%Y-%m-%d %H:%M:%S'),  # Return the formatted locked timestamp
    })


# Route to fetch room layout details for a given house
@app.route('/rooms/<house_id>', methods=['GET'])
def get_layout(house_id):
    try:
        # Fetch the house layout from MongoDB using house_id
        house_layout = mongo.db.houses.find_one({"house_id": house_id})

        if not house_layout:  # If the house layout is not found
            return jsonify({"error": "House layout not found"}), 404

        # Generate a session ID (for layout access)
        session_id = str(uuid.uuid4())

        # Prepare the response data (including rooms, areas, and images)
        rooms_data = house_layout.get('rooms', {})  # Get the rooms data from the house
        rooms_image = house_layout.get('rooms_image', '')  # Get the rooms image path

        # Format the layout response with rooms and their areas
        layout_response = {
            "house_id": house_id,
            "rooms_image": rooms_image,
            "rooms": []
        }

        for room_name, room in rooms_data.items():
            room_data = {
                "name": room_name,
                "areas": []  # Initialize an empty list for areas
            }

            # Extract layout page details using dict.get()
            layout_page_details = room.get('layout_page_details', {})
            
            # Create area_data using dictionary unpacking and default values
            if layout_page_details:
                room_data["areas"].append({
                    "name": room_name,  # Add room name as area name
                    **layout_page_details  # Unpack layout_page_details into room_data
                })

            # If there are images related to the room, include them as well
            if room.get('image_path'):
                room_data["image_path"] = room.get('image_path')  # Include the room image path

            layout_response["rooms"].append(room_data)  # Add the room data to the response

        return jsonify(layout_response)  # Return the layout response

    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error message if something goes wrong


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

        # Validate if the house is locked by the current session
        if locked_by != session_id:
            return jsonify({"status": "error", "message": "House is not locked by your session"}), 400

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

        return jsonify(response_data)  # Return the room data response

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to handle room selection
@app.route('/select-room', methods=['POST'])
def select_room():
    try:
        # Get data from the POST request
        data = request.get_json()  # Parse the incoming JSON data
        house_id = data.get('house_id')  # Extract house_id from the JSON data
        session_id = data.get('session_id')  # Extract session_id from the JSON data
        selected_rooms = data.get('selected_rooms')  # Extract the list of selected rooms
        preferences = data.get('preferences')  # Extract the user's preferences (e.g., colors)

        # Validate the input data
        if not house_id or not session_id or not selected_rooms:
            return jsonify({"status": "error", "message": "Missing house_id, session_id, or selected_rooms"}), 400

        # Fetch the house from the database using house_id
        houses_collection = mongo.db.houses
        house = houses_collection.find_one({"house_id": house_id})

        if not house:
            return jsonify({"status": "error", "message": "House not found"}), 404

        # Lock the house for the session if not already locked
        locked_by = house.get("locked_by")
        if not locked_by:
            houses_collection.update_one(
                {"house_id": house_id},
                {"$set": {"locked_by": session_id}}
            )
            locked_by = session_id  # Lock it for the current session

        if locked_by != session_id:
            return jsonify({"status": "error", "message": "House is not locked by your session"}), 400

        # Update the selected rooms and preferences in the house data
        # You can store the selected_rooms and preferences in a new field or a specific document
        house_preferences = {
            "selected_rooms": selected_rooms,
            "preferences": preferences
        }

        # Assuming there's a 'room_preferences' collection or updating directly in the house document
        mongo.db.room_preferences.update_one(
            {"house_id": house_id, "session_id": session_id},
            {"$set": house_preferences},
            upsert=True  # Create a new document if none exists for this session and house
        )

        # Return a success message
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
    app.run(debug=True)  # Start the Flask development server with debugging enabled
