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

app.secret_key = 'your_secret_key_here'  # Change to a strong secret key

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
    available_houses = houses_collection.find({"locked_by": None})  # Filter houses where locked_by is None
    
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

if __name__ == '__main__':
    app.run(debug=True)
