from flask import Flask, jsonify, redirect, url_for, send_from_directory, request
from flask_pymongo import PyMongo
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

@app.route('/', methods=['GET'])
def home():
    return redirect(url_for('get_houses'))

@app.route('/houses', methods=['GET'])
def get_houses():
    houses = mongo.db.houses.find()
    house_list = [
        {
            'id': str(house['_id']),
            'name': f"House Number {i + 1}",
            'image': house.get('image', ''),  # Fetching image directly from database
            'description': house.get('description', '')
        }
        for i, house in enumerate(houses)
        if i < 4
    ]
    return jsonify(house_list)

@app.route('/houses/<string:house_id>/rooms', methods=['GET'])
def get_rooms(house_id):
    rooms = mongo.db.rooms.find({'house_id': house_id})
    return jsonify([{
        'id': str(room['_id']),
        'name': room['name'],
        'color_options': room['color_options'],
        'image': room.get('image', '')  # Fetching room images
    } for room in rooms])

@app.route('/select-house', methods=['POST'])
def select_house():
    data = request.get_json()
    house_id = data.get('house_id')
    house_name = data.get('house_name')

    if not house_id or not house_name:
        return jsonify({'error': 'House ID and name are required.'}), 400

    # Insert user choice into the user_choices collection
    mongo.db.user_choices.insert_one({
        'house_id': house_id,
        'house_name': house_name
    })

    return jsonify({'message': 'House selected successfully!'}), 201

@app.route('/kitchen/images', methods=['GET'])
def get_kitchen_images():
    # Example static list of kitchen color options
    kitchen_images = [
        {'name': 'Default', 'image': '/images/kitchen.jpg', 'color': '#FAF0E6'},
        {'name': 'Caramel', 'image': '/images/kitchenCabinet1.jpg', 'color': '#D2B48C'},
        {'name': 'Yellow', 'image': '/images/kitchenCabinet2.jpg', 'color': '#FFD700'},
        {'name': 'Neon Pink', 'image': '/images/kitchenCabinet3.jpg', 'color': '#FF69B4'},
    ]
    
    # Example static list of wall color options
    wall_images = [
        {'name': 'Pale Green', 'image': '/images/Wall1.jpg', 'color': '#b0c8bf'},
        {'name': 'Pale Olive', 'image': '/images/Wall2.jpg', 'color': '#dad8b9'},
        {'name': 'Warm Beige', 'image': '/images/Wall3.jpg', 'color': '#c8bca6'},
    ]

    # Combine both lists into a single response
    combined_images = {
        'cabinets': kitchen_images,
        'walls': wall_images
    }
    
    return jsonify(combined_images)

if __name__ == '__main__':
    app.run(debug=True)
