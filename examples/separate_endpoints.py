"""
    Separate URLs example
    ~~~~~~~~~~~~~~~~~~~~~

    This provides an example of creating separate API endpoints for different
    HTTP methods.

    You can read from the database by making a
    :http:get:`http://localhost:5000/get/person` request, add a new person
    using :http:get:`http://localhost:5000/add/person`, etc.

    :copyright: 2012 Jeffrey Finkelstein <jeffrey.finkelstein@gmail.com>
    :license: GNU AGPLv3+ or BSD

"""
import flask
import flask.ext.sqlalchemy
import flask.ext.restless

# Create the Flask application and the Flask-SQLAlchemy object.
app = flask.Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = flask.ext.sqlalchemy.SQLAlchemy(app)

# Create your Flask-SQLALchemy models as usual but with the following two
# (reasonable) restrictions:
#   1. They must have an id column of type Integer.
#   2. They must have an __init__ method which accepts keyword arguments for
#      all columns (the constructor in flask.ext.sqlalchemy.SQLAlchemy.Model
#      supplies such a method, so you don't need to declare a new one).
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, unique=True)
    birth_date = db.Column(db.Date)
    computers = db.relationship('Computer', backref=db.backref('owner',
                                                               lazy='dynamic'))


class Computer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, unique=True)
    vendor = db.Column(db.Unicode)
    owner_id = db.Column(db.Integer, db.ForeignKey('person.id'))
    purchase_time = db.Column(db.DateTime)


# Create the database tables.
db.create_all()

# Create the Flask-Restless API manager.
manager = flask.ext.restless.APIManager(app, flask_sqlalchemy_db=db)

# Create API endpoints, each at a different URL and with different allowed HTTP
# methods, but which all affect the Person model.
manager.create_api(Person, methods=['GET'], url_prefix='/get')
manager.create_api(Person, methods=['POST'], url_prefix='/add')
manager.create_api(Person, methods=['PATCH'], url_prefix='/update')
manager.create_api(Person, methods=['DELETE'], url_prefix='/remove')

# start the flask loop
app.run()
