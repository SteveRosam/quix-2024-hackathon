import os
from quixstreams import Application, State
from geopy.distance import geodesic
from datetime import datetime, timedelta
import requests

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application(consumer_group="transformation-v1", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"])
telegram_output_topic = app.topic(os.environ["telegram_output"])
slack_output_topic = app.topic(os.environ["slack_output"])

sdf = app.dataframe(input_topic)

# put transformation logic here
# see docs for what you can do
# https://quix.io/docs/get-started/quixtour/process-threshold.html

# user config would be loaded from a DB or another topic or MQ so that updates to user prefs gets updated here
user_config = [
    {
        "user_name": "Steve",
        "min_wind_speed": 13,
        "home_location": { "lng": "50.1", "lat": "0" },
        "preferred_locations":["Folkestone", "Dover"],
        "notification_settings":{
            "slack": "true",
            "telegram": "true",
            "pigeon": "false"
        }
     },
     {
        "user_name": "Tun",
        "min_wind_speed": 9,
        "home_location": { "lng": "55.1", "lat": "10" },
        "preferred_locations":["Margate", "Dover"],
        "notification_settings":{
            "slack": "true",
            "telegram": "false",
            "pigeon": "false"
        }
     }
]


def send_slack_notification(user_name, location_name, distance, current_speed, forecast_speed):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Slack webhook URL not set.")
        return

    message = {
        "text": f"User: {user_name}, Location: {location_name}, Distance: {distance:.2f} km, "
                f"Current Wind Speed: {current_speed:.2f} knots, Forecast Wind Speed: {forecast_speed:.2f} knots"
    }

    response = requests.post(webhook_url, json=message)
    if response.status_code != 200:
        print(f"Failed to send Slack notification: {response.status_code}, {response.text}")

slack_topic_producer = None
def get_slack_topic_producer() :

    if slack_topic_producer is None:
        slack_topic_producer = app.get_producer()

    return slack_topic_producer       


telegram_topic_producer = None
def get_telegram_topic_producer() :

    if telegram_topic_producer is None:
        telegram_topic_producer = app.get_producer()

    return telegram_topic_producer       


def handle_data(data: dict, state: State):
    # print(data)

    location_name = data["name"]
    current_speed = data["current_speed"]
    forecast_speed = data["forecast"]

    for user in user_config:
        print(user)
        if location_name in user["preferred_locations"] and current_speed > user["min_wind_speed"]:
            user_home = (user["home_location"]["lat"], user["home_location"]["lng"])
            location_coords = (data["latitude"], data["longitude"])
            distance = geodesic(user_home, location_coords).kilometers

            # sink to influx

            # send notification messages

            user_name = user['user_name']
            last_user_notification = state.get(user_name + "last_notification", datetime.now())
            
            current_time = datetime.now()
            if current_time - last_user_notification > timedelta(minutes=1):
                state.set(user_name + "_last_notification", current_time)
                print(f"User: {user['user_name']}, Location: {location_name}, Distance: {distance:.2f} km, "
                      f"Current Wind Speed: {current_speed:.2f} knots, Forecast Wind Speed: {forecast_speed:.2f} knots")
                

                message_payload={
                    "user": user['user_name'],
                    "message": f"A favourable forecast has been found. Wind speed: {forecast_speed:.2f} knots, Location: {location_name}, Distance: {distance:.2f} km"
                }
                message_key=f"{user['user_name']}_{location_name}"
            
                # Send Slack notification if settings permit
                if user["notification_settings"].get("slack") == "true":
                    # publish message to slack topic, this will be handled by a slack sender
                    get_slack_topic_producer().produce(topic=slack_output_topic.name, value=message_payload, key=message_key)

                # Send telegram notification if settings permit
                if user["notification_settings"].get("telegram") == "true":
                    # publish message to telegram topic, this will be handled by a telegram sender
                    get_telegram_topic_producer().produce(topic=telegram_output_topic.name, value=message_payload, key=message_key)
            else:
                print(f"User: {user['user_name']} was notified recently. Skipping this one.")

sdf = sdf.apply(handle_data, stateful=True)

if __name__ == "__main__":
    app.run(sdf)