# Creates the connection to your PostgreSQL database and gives every
# part of the app a way to talk to it. 
# Think of it as the bridge between your Python code and pgAdmin.
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.DATABASE_URL) # connect python to pgadmin through url

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)# create session every api request get its own session


Base = declarative_base() #every database model (table) will inherit from this


def get_db(): #a function that opens a session, gives it to a route, then closes it automatically when done
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()