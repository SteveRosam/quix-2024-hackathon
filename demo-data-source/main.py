from csv_source import CsvSource
from quixstreams import Application
import os
import time
import random
import json

# import the dotenv module to load environment variables from a file
from dotenv import load_dotenv

load_dotenv(override=False)

# Create an Application.
app = Application()

# Define the topic using the "output" environment variable
topic_name = os.getenv("output", "wind")
if topic_name == "":
    raise ValueError("The 'output' environment variable is required. This is the output topic that data will be published to.")

# Define 5 different coastal locations in the southeast of England
locations = [
    {"name": "Dover", "latitude": 51.1290, "longitude": 1.3080},
    {"name": "Hastings", "latitude": 50.8543, "longitude": 0.5730},
    {"name": "Folkestone", "latitude": 51.0800, "longitude": 1.1784},
    {"name": "Margate", "latitude": 51.3813, "longitude": 1.3862},
    {"name": "Eastbourne", "latitude": 50.7680, "longitude": 0.2905}
]

# Initialize the wind speed and forecast for each location
weather_data = [
    {"current_speed": random.uniform(5, 15), "forecast": random.uniform(5, 15)}
    for _ in locations
]

def fluctuate(value, min_value=0, max_value=30):
    """Fluctuate the value within ±3 knots, ensuring it stays within specified bounds."""
    fluctuation = random.uniform(-3, 3)
    new_value = value + fluctuation
    return max(min_value, min(max_value, new_value))

def generate_weather_data():
    location_weather_data = []

    for index, location in enumerate(locations):
        current_speed = weather_data[index]["current_speed"]
        forecast = weather_data[index]["forecast"]

        # Update current speed and forecast
        new_current_speed = fluctuate(current_speed)
        new_forecast = fluctuate(forecast)

        weather_data[index]["current_speed"] = new_current_speed
        weather_data[index]["forecast"] = new_forecast

        location_weather_data.append({
            "name": location["name"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current_speed": new_current_speed,
            "forecast": new_forecast
        })

        print(f"Location: {location['name']}")
        print(f"Coordinates: ({location['latitude']}, {location['longitude']})")
        print(f"Current Wind Speed: {new_current_speed:.2f} knots")
        print(f"Wind Forecast for Next Hour: {new_forecast:.2f} knots")
        print("-" * 40)

    return location_weather_data



output_topic = app.topic(topic_name)

def main():
    while True:
        with app.get_producer() as p:
            data = generate_weather_data()
            json_data = json.dumps(data)
            print(json_data)
            timestamp_nanos = int(time.time() * 1e9)  # Convert current time to nanoseconds
            p.produce(topic_name, value=json_data, key='wind', timestamp=timestamp_nanos)
            time.sleep(5)


if __name__ == "__main__": 
    main()