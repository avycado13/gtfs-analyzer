import os
import pandas as pd
import folium
from collections import Counter
from shapely.geometry import Point, LineString
from shapely.ops import unary_union

# Function to load GTFS files from a directory
def load_gtfs_from_directory(directory):
    # List of expected GTFS files
    required_files = ['trips.txt', 'stop_times.txt', 'routes.txt', 'stops.txt']
    
    files = {}
    for file_name in required_files:
        file_path = os.path.join(directory, file_name)
        if os.path.exists(file_path):
            try:
                files[file_name] = pd.read_csv(file_path, on_bad_lines='skip')
            except Exception as e:
                print(f"Error loading {file_name} in {directory}: {e}")
        else:
            print(f"Warning: {file_name} not found in {directory}")
    
    # Check if all required files are loaded
    if len(files) != len(required_files):
        print(f"Warning: Missing some GTFS files in {directory}")
    
    return files

# Function to extract and analyze trips and stops for segments
def extract_segments(gtfs_files):
    try:
        trips = gtfs_files['trips.txt']
        stop_times = gtfs_files['stop_times.txt']
        routes = gtfs_files['routes.txt']
    except KeyError as e:
        print(f"Error: Missing required file {e} in GTFS data")
        return Counter()

    # Merge trips and stop_times to find the sequence of stops
    trip_stop_times = pd.merge(stop_times, trips[['trip_id', 'route_id']], on='trip_id', how='left')
    trip_stop_times = trip_stop_times[['trip_id', 'stop_sequence', 'stop_id', 'route_id']].sort_values(by=['trip_id', 'stop_sequence'])
    
    # Create a dictionary of unique segments based on stops
    segments = Counter()
    for _, group in trip_stop_times.groupby('trip_id'):
        stops = tuple(group['stop_id'])
        segments[stops] += 1
    
    return segments

def plot_routes_on_map(gtfs_files):
    # Retrieve the stop locations (assuming 'stops.txt' contains 'stop_lat' and 'stop_lon')
    if 'stops.txt' not in gtfs_files:
        print("Error: 'stops.txt' not found in GTFS data")
        return None
    
    stops_df = gtfs_files['stops.txt']
    
    # Ensure 'stop_lat' and 'stop_lon' columns exist
    if 'stop_lat' not in stops_df or 'stop_lon' not in stops_df:
        print("Error: 'stop_lat' or 'stop_lon' missing in stops.txt")
        return None
    
    # Retrieve trip and stop_times information
    if 'trips.txt' not in gtfs_files or 'stop_times.txt' not in gtfs_files:
        print("Error: Missing 'trips.txt' or 'stop_times.txt'. Cannot plot routes.")
        return None
    
    trips_df = gtfs_files['trips.txt']
    stop_times_df = gtfs_files['stop_times.txt']
    
    # Merge stop_times with stops to get lat/lon and stop_sequence
    trip_stop_times = pd.merge(stop_times_df, stops_df[['stop_id', 'stop_lat', 'stop_lon']], on='stop_id', how='left')
    trip_stop_times = pd.merge(trip_stop_times, trips_df[['trip_id', 'route_id']], on='trip_id', how='left')
    
    # Sort by trip_id and stop_sequence to get the correct order of stops
    trip_stop_times = trip_stop_times[['trip_id', 'stop_sequence', 'stop_id', 'stop_lat', 'stop_lon', 'route_id']].sort_values(by=['trip_id', 'stop_sequence'])
    
    # Create a folium map centered on the average location of all stops
    map_center = [stops_df['stop_lat'].mean(), stops_df['stop_lon'].mean()]
    map_obj = folium.Map(location=map_center, zoom_start=12)
    
    # Plot each route based on the trips
    for trip_id, group in trip_stop_times.groupby('trip_id'):
        # Extract coordinates for each stop in this trip
        coordinates = group[['stop_lat', 'stop_lon']].dropna().values.tolist()
        
        # Skip trips with no valid coordinates
        if not coordinates:
            print(f"Skipping trip {trip_id}: No valid coordinates found.")
            continue
        
        # Add a polyline for this trip
        folium.PolyLine(locations=coordinates, color="blue", weight=2.5, opacity=0.8).add_to(map_obj)
    
    return map_obj




def analyze_gtfs_feeds(gtfs_directories):
    # Loop over each GTFS directory and plot all routes
    for directory in gtfs_directories:
        print(f"Processing GTFS feed in directory {directory}...")
        gtfs_data = load_gtfs_from_directory(directory)
        
        if not gtfs_data:  # Skip if the directory is missing required files
            print(f"Skipping {directory} due to missing files.")
            continue
        
        # Plot all routes for this GTFS feed
        map_obj = plot_routes_on_map(gtfs_data)
        
        if map_obj:
            # Save the map as HTML
            map_filename = f"routes_map_{os.path.basename(directory)}.html"
            map_obj.save(map_filename)
            print(f"Map saved as '{map_filename}'.")
        else:
            print(f"Failed to generate map for {directory}.")


# Example usage:
if __name__ == "__main__":
    gtfs_feeds = [
        'feeds/samtrans',  # Add paths to your unzipped GTFS directories
        'feeds/muni',
        'feeds/actransit',
        'feeds/vta',
    ]
    
    analyze_gtfs_feeds(gtfs_feeds)
