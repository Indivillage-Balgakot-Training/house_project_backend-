from flask_pymongo import PyMongo

mongo = PyMongo()

def get_next_sequence_id(sequence_name):
    sequence_document = mongo.db.counters.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'seq': 1}},
        return_document=True
    )
    return sequence_document['seq']

class User:
    # User model remains unchanged
    pass

class House:
    @staticmethod
    def insert(house_data):
        house_id = get_next_sequence_id('house_id')
        house_data['id'] = house_id  # Add custom ID to house data
        return mongo.db.houses.insert_one(house_data)

    @staticmethod
    def all():
        return list(mongo.db.houses.find())

class Room:
    @staticmethod
    def filter_by(house_id):
        return list(mongo.db.rooms.find({"house_id": house_id}))  # Convert cursor to a list

    @staticmethod
    def insert(room_data):
        return mongo.db.rooms.insert_one(room_data)
