from flask_pymongo import PyMongo

# Initialize the PyMongo instance
mongo = PyMongo()

def init_db(app):
    # Initialize MongoDB with the Flask app
    mongo.init_app(app)
