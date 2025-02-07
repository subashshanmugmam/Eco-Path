import openrouteservice
import csv
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, render_template, request, redirect, url_for, jsonify
import math
from geopy.geocoders import Nominatim
from flask_cors import CORS
from flask import session
from geopy.distance import geodesic

 # Replace with a strong, random string

# OpenRouteService API client
client = openrouteservice.Client(key='5b3ce3597851110001cf624861a6dc3b44ba4091b737bb4b3c461b08')

# CSV file to store emission data
CSV_FILE = r'C:\Users\subas\OneDrive\Desktop\flask_project\data.csv'

# Flask app
app = Flask(__name__)
CORS(app)
CSV_FILE1=r'C:\Users\subas\OneDrive\Desktop\flask_project\emissions_data.csv'


app.secret_key = 'subash' 
# Helper function to calculate distance and directions using OpenRouteService

def calculate_distance_and_directions(start_coords, end_coords):
    try:
        # Ensure the coordinates are in the correct format (tuple of lat, lon)
        if not isinstance(start_coords, tuple) or not isinstance(end_coords, tuple):
            raise ValueError("Coordinates must be tuples (lat, lon).")
        
        if len(start_coords) != 2 or len(end_coords) != 2:
            raise ValueError("Coordinates must contain exactly two elements: latitude and longitude.")
        
        # Calculate the distance using geopy's geodesic method (in kilometers)
        distance = geodesic(start_coords, end_coords).kilometers

        # Placeholder for actual directions (you can implement a routing API here)
        directions = ["Head north", "Turn right onto the highway"]  # This should be replaced with actual logic

        # Return distance and directions
        return distance, directions

    except ValueError as ve:
        raise Exception(f"Value error: {ve}")
    except Exception as e:
        raise Exception(f"Error calculating distance and directions: {e}")



# Helper function to calculate carbon emissions
def calculate_carbon_emissions(distance, mode_of_transport):
    try:
        emission_factors = {
            'car': 0.2,  # kg of CO2 per km for car
            'bus': 0.05,  # kg of CO2 per km for bus
            'train': 0.03,  # kg of CO2 per km for train
            'bike': 0  # kg of CO2 per km for bike (no emissions)
        }
        emission_factor = emission_factors.get(mode_of_transport, 0.2)  # Default to 'car'
        emissions = distance * emission_factor
        return emissions
    except KeyError as e:
        raise Exception(f"Invalid transport mode: {mode_of_transport}")
    except Exception as e:
        raise Exception(f"Error calculating emissions: {e}")

# Save data to CSV
def save_data_to_csv(start_coords, end_coords, distance, mode_of_transport, emissions):
    try:
        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([datetime.now(), start_coords, end_coords, distance, mode_of_transport, emissions])
    except Exception as e:
        raise Exception(f"Error saving data to CSV: {e}")

@app.route('/submit', methods=['POST'])
def submit_data():
    try:
        start = request.form['start']
        end = request.form['end']
        distance = float(request.form['distance'])
        mode_of_transport = request.form['mode_of_transport']
        emissions = float(request.form['emissions'])
        save_data_to_csv(start, end, distance, mode_of_transport, emissions)
        return jsonify({"message": "Data submitted successfully!"}), 200
    except Exception as e:
        print(f"Error during submission: {e}")
        return jsonify({"error": f"An error occurred while submitting the data: {e}"}), 500

@app.route('/get_route', methods=['GET'])
def get_route():
    try:
        start_lat = float(request.args.get('start_lat'))
        start_lon = float(request.args.get('start_lon'))
        end_lat = float(request.args.get('end_lat'))
        end_lon = float(request.args.get('end_lon'))
        
        route = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [start_lon, start_lat],  # Start point
                        [end_lon, end_lat]       # End point
                    ]
                },
                "properties": {}
            }]
        }
        distance = 10.5  # Example distance in km
        return jsonify({"status": "success", "route": route, "distance": distance})
    except Exception as e:
        return jsonify({"error": f"Error calculating route: {e}"}), 500

@app.route('/leaderboard')
def leaderboard():
    try:
        # Load data from emissions_data.csv
        data = pd.read_csv(CSV_FILE1)

        # Normalize column names
        data.columns = data.columns.str.strip().str.lower()

        # Ensure the 'timestamp' column exists
        if 'timestamp' not in data.columns:
            return "Error: 'timestamp' column not found in emissions data CSV.", 500

        # Convert 'timestamp' to datetime
        data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce')

        # Drop rows with invalid 'timestamp' or 'emission'
        data = data.dropna(subset=['timestamp', 'emission'])

        # Filter for current week's data
        current_week = pd.Timestamp.now().isocalendar().week
        week_data = data[data['timestamp'].dt.isocalendar().week == current_week]

        # Sort and pick top 5 least CO2 emitters
        week_data_sorted = week_data.sort_values(by='emission').head(5)

        # Debugging step: Print the data being passed to the template
        print("Filtered and sorted leaderboard data:")
        print(week_data_sorted)

        # If no data is available
        if week_data_sorted.empty:
            return render_template('leaderboard.html', leaderboard=None)

        # Pass the sorted data to the template
        return render_template('leaderboard.html', leaderboard=week_data_sorted.to_dict(orient='records'))

    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500


@app.route('/reports')
def reports():
    try:
        data = pd.read_csv(CSV_FILE, header=None, names=['Timestamp', 'Start', 'End', 'Distance', 'Mode', 'Emissions'])
        data['Timestamp'] = pd.to_datetime(data['Timestamp'], errors='coerce')
        data = data.dropna(subset=['Timestamp'])
        last_20_data = data.tail(20)
        chart_labels = last_20_data['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
        chart_emissions = last_20_data['Emissions'].tolist()
        return render_template('reports.html', labels=chart_labels, emissions=chart_emissions)
    except Exception as e:
        return f"Error generating report: {e}"

# Initialize the geolocator
geolocator = Nominatim(user_agent="flask_app")

def is_sea(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), language='en', timeout=10)
        if location is None:
            return True  # Assume sea if no location found
        else:
            return False  # Land detected
    except Exception as e:
        print(f"Error in reverse geocoding: {e}")
        return False  # Default to land if geocoding fails
@app.route('/add_emission', methods=['POST'])
def add_emission():
    try:
        # Check if the content type is JSON (usually for AJAX or API requests)
        if request.is_json:
            data = request.get_json()  # Get JSON data from the request
        else:
            # If not JSON, fall back to form data (standard form submission)
            data = request.form

        # Extract and validate data from the request
        mode = data.get('mode')
        if not mode:
            return jsonify({"status": "error", "message": "Mode of transport is required."}), 400
        
        # Extract coordinates
        start_lat = float(data.get('start_lat'))
        start_lon = float(data.get('start_lon'))
        end_lat = float(data.get('end_lat'))
        end_lon = float(data.get('end_lon'))

        # Calculate distance
        distance = geodesic((start_lat, start_lon), (end_lat, end_lon)).kilometers
        
        # Calculate emissions based on transport mode
        emission_factor = {'car': 0.2, 'bus': 0.05, 'train': 0.03, 'bike': 0}.get(mode, 0.2)
        emissions = distance * emission_factor

        # Save data to CSV
        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([datetime.now(), (start_lat, start_lon), (end_lat, end_lon), distance, mode, emissions])

        return jsonify({
            "status": "success",
            "message": "Emission added successfully",
            "distance": round(distance, 2),
            "co2": round(emissions, 2)
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def test():
    return "Flask server is working!"

def favicon():
    return '', 204 
@app.route('/')
def home():
    return render_template('dashboard.html')

@app.route('/calculate_distance', methods=['GET'])
def calculate_distance():
    try:
        start_lat = float(request.args.get('start_lat'))
        start_lon = float(request.args.get('start_lon'))
        end_lat = float(request.args.get('end_lat'))
        end_lon = float(request.args.get('end_lon'))

        # Replace with actual distance calculation logic
        distance, _ = calculate_distance_and_directions([start_lat, start_lon], [end_lat, end_lon])
        
        return jsonify({"status": "success", "distance": distance})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/index')
def index():
    if 'user' in session:
        return render_template('index.html')  # Render index page
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'sb' and password == '123':
            session['user'] = username  # Set session data
            return redirect(url_for('index'))  # Redirect to the index route
        else:
           return render_template('login.html', error="Invalid credentials. Please try again.")  # Show error

    # Ensure GET request renders the login page
    return render_template('login.html')




import logging
logging.basicConfig(level=logging.DEBUG)
import logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/dashboard')
def dashboard():
    logging.debug(f"Session data: {session}")
    user = session.get('user')
    
    if user:
        logging.debug(f"User in session: {user}")
        return render_template('dashboard.html')
    else:
        logging.debug("No user in session")
        return redirect(url_for('login'))

from datetime import timedelta
app.permanent_session_lifetime = timedelta(minutes=30)  # Set session timeout

@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove user data from session
    return redirect(url_for('login'))

@app.route('/get_latest_data', methods=['GET'])
def get_latest_data():
    try:
        # Load the data from the CSV file
        data = pd.read_csv(CSV_FILE, names=['Timestamp', 'Start', 'End', 'Distance', 'Mode', 'Emissions'])

        # Ensure Timestamp column is in datetime format
        data['Timestamp'] = pd.to_datetime(data['Timestamp'], dayfirst=False, errors='coerce')

        # Check for any invalid timestamps
        if data['Timestamp'].isnull().any():
            print("Warning: Some timestamps could not be parsed and will be dropped.")
            data = data.dropna(subset=['Timestamp'])

        # Filter the last week's data
        current_week = datetime.now().isocalendar()[1]
        data['Week'] = data['Timestamp'].dt.isocalendar().week
        weekly_data = data[data['Week'] == current_week]

        if weekly_data.empty:
            return jsonify({"labels": [], "emissions": []})  # No data for the current week

        # Extract labels (timestamps) and emissions
        labels = weekly_data['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
        emissions = weekly_data['Emissions'].tolist()

        return jsonify({"labels": labels, "emissions": emissions})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)


