from flask import jsonify, request, session
from models import User, House, Room, mongo  # Import models

def register_routes(app):
    @app.route('/houses', methods=['GET'])
    def get_houses():
        houses = House.all()  # Get all houses from MongoDB
        return jsonify([{'id': str(house['_id']), 'name': house['name'], 'image': house['image'], 'description': house['description']} for house in houses])

    @app.route('/houses/<string:house_id>/rooms', methods=['GET'])
    def get_rooms(house_id):
        rooms = Room.filter_by(house_id)  # Get rooms for a specific house
        return jsonify([{'id': str(room['_id']), 'name': room['name'], 'color_options': room['color_options']} for room in rooms])

    @app.route('/user/data', methods=['POST'])
    def add_user_data():
        user_id = session.get('user_id')
        if not user_id:
            session['user_id'] = str(mongo.db.sessions.insert_one({}).inserted_id)  # Store session ID
            user_id = session['user_id']
        
        user_data = request.json
        mongo.db.users.update_one({'_id': user_id}, {'$set': user_data}, upsert=True)

        return jsonify({'message': 'Data saved successfully', 'user_id': user_id})

    @app.route('/user/data', methods=['GET'])
    def get_user_data():
        user_id = session.get('user_id')
        if user_id:
            user_data = mongo.db.users.find_one({'_id': user_id})
            return jsonify(user_data) if user_data else jsonify({'message': 'No data found'})
        return jsonify({'message': 'No session found'})