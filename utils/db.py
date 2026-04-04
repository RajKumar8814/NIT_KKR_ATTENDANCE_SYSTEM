from flask_pymongo import PyMongo

mongo = PyMongo()

def init_db(app):
    # Enforce strict CPU-bound threading profiles preventing free-tier memory/connection cascades
    mongo.init_app(
        app, 
        maxPoolSize=2, 
        serverSelectionTimeoutMS=20000, 
        connectTimeoutMS=20000,
        socketTimeoutMS=20000
    )

def get_db():
    return mongo.db
