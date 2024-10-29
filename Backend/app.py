from flask import Flask, jsonify, redirect, url_for, send_from_directory
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
    return jsonify([
        {
            'id': str(room['_id']),
            'name': room['name'],
            'color_options': room['color_options'],
            'image': room.get('image', '')  # Fetching room images
        }
        for room in rooms
    ])

@app.route('/kitchen/images', methods=['GET'])
def get_kitchen_images():
    # Example static list of kitchen color options, could be fetched from DB
    kitchen_images = [
        { 'name': 'Default', 'image': '/images/kitchen.jpg', 'color': '#FAF0E6' },
        { 'name': 'Caramel', 'image': '/images/kitchenCabinet1.jpg', 'color': '#D2B48C' },
        { 'name': 'Yellow', 'image': '/images/kitchenCabinet2.jpg', 'color': '#FFD700' },
        { 'name': 'Neon Pink', 'image': '/images/kitchenCabinet3.jpg', 'color': '#FF69B4' },
    ]
    return jsonify(kitchen_images)

if __name__ == '__main__':
    app.run(debug=True)
