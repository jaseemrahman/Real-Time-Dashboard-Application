# Import necessary modules and libraries
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from threading import Lock
from datetime import datetime
import pytz

# Create a Flask application
app = Flask(__name__)



# Configure Flask application settings
app.config['SECRET_KEY'] = 'piserve'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

# Initialize SocketIO with the Flask application
socketio = SocketIO(app, cors_allowed_origins='*')

# Initialize SQLAlchemy with the Flask application
db = SQLAlchemy(app)

# Define the maximum number of data entries to be fetched
MAX_DATA_COUNT = 100

# Initialize the thread lock in the global scope
thread = None
thread_lock = Lock()

# Add a global variable to store the current sort order
current_sort_order = 'desc'

# Add a global variable to store filter parameters
global_filter_params = {'start_date': None, 'end_date': None}

# Define the model for sensor data in the database
class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(20), nullable=False)

# Create the database tables before the first request is processed
@app.before_first_request
def before_first_request():
    db.create_all()

# Function to get the current date and time in Asia/Kolkata timezone
def get_current_datetime():
    now_utc = datetime.utcnow()
    utc_timezone = pytz.timezone('UTC')
    now_utc = utc_timezone.localize(now_utc)
    asia_kolkata_timezone = pytz.timezone('Asia/Kolkata')
    now_kolkata = now_utc.astimezone(asia_kolkata_timezone)
    return now_kolkata.strftime("%d/%m/%Y %H:%M:%S")


def background_thread():
    with app.app_context():
        while True:
            # Fetch the latest sensor data from the database with the current sorting order
            query = SensorData.query

            # Apply filtering based on global_filter_params
            start_date = global_filter_params.get('start_date')
            end_date = global_filter_params.get('end_date')

            if start_date:
                query = query.filter(SensorData.date >= start_date)
            if end_date:
                query = query.filter(SensorData.date <= end_date)

            # Use the global variable for sorting order
            if current_sort_order == 'desc':
                query = query.order_by(SensorData.date.desc())
            else:
                query = query.order_by(SensorData.date.asc())

            # Limit the number of entries to fetch
            data = query.limit(10).all()

            # Extract values, ids, and dates from the sensor data
            sensor_values = [entry.value for entry in data]
            sensor_ids = [entry.id for entry in data]
            sensor_dates = [datetime.strptime(entry.date, '%d/%m/%Y %H:%M:%S').isoformat() for entry in data]

            # Emit the sensor data update to connected clients
            socketio.emit('updateSensorData', {'ids': sensor_ids, 'values': sensor_values, 'dates': sensor_dates})

            # Sleep for 1 second before the next iteration
            socketio.sleep(1)

# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')

# Route to fetch sensor data/api
@app.route('/get_data', methods=['GET'])
def get_sensor_data():
    data = SensorData.query.order_by(SensorData.date.desc()).limit(MAX_DATA_COUNT).all()
    return jsonify([{'id': entry.id, 'date': entry.date, 'value': entry.value} for entry in data])

# Route to add sensor data
@app.route('/add_data', methods=['POST'])
def add_sensor_data():
    data = request.get_json()
    value = data.get('value')
    date = get_current_datetime()

    # Create a new sensor data entry and add it to the database
    sensor_data = SensorData(value=value, date=date)
    db.session.add(sensor_data)
    db.session.commit()

    return jsonify({'message': 'Sensor data added successfully'})

# Route to edit sensor data
@app.route('/edit_data/<int:sensor_id>', methods=['PUT'])
def edit_sensor_data(sensor_id):
    data = request.get_json()
    new_value = data.get('value')

    result_data = {
            'value': new_value
        }
    # Update the value if the entry exists
    with app.app_context():
        SensorData.query.filter_by(id=sensor_id).update(result_data)
        db.session.commit()
    return jsonify({'message': 'Sensor data updated successfully'})


# Route to delete sensor data
@app.route('/delete_data/<int:sensor_id>', methods=['DELETE'])
def delete_sensor_data(sensor_id):
    # Find the sensor data entry with the given id
    sensor_data = SensorData.query.get(int(sensor_id))

    # Delete the entry if it exists
    if sensor_data:
        db.session.delete(sensor_data)
        db.session.commit()

        # Trigger a background thread update after deletion
        background_thread()

        return jsonify({'message': 'Sensor data deleted successfully'})
    else:
        return jsonify({'error': 'Sensor data not found'}), 404
    

# SocketIO event handler for client connection
@socketio.on('connect')
def connect():
    print('Client connected')

    # Start the background thread if it hasn't been started
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)

# SocketIO event handler for client disconnection
@socketio.on('disconnect')
def disconnect():
    print('Client disconnected', request.sid)


@socketio.on('changeSortOrder')
def change_sort_order(sort_order):
    # Update the global variable with the new sorting order
    global current_sort_order
    current_sort_order = sort_order

@socketio.on('applyFilter')
def apply_filter(filter_params):
    global global_filter_params
    global_filter_params = filter_params

# Run the application with SocketIO support
if __name__ == '__main__':
    socketio.run(app, debug=True)
