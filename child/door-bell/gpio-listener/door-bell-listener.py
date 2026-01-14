import os
from gpiozero import Button
import requests
from signal import pause

# Connect the input to GPIO pin 17.
# The `pull_up=True` means the pin will be HIGH when the button is not pressed
# and LOW when it is pressed.
button = Button(17, pull_up=True, bounce_time=0.1)

def action_on_door_bell_ring():
    api_url = os.getenv("NOTIFY_API_URL", "")
    api_token = os.getenv("NOTIFY_API_TOKEN", "")
    camera_feed_url = os.getenv("CAMERA_FEED_URL", "")

    if not api_url or not api_token:
        print("Configs not defined properly. Exiting...", flush=True)
        return

    print("Door bell rang... Executing actions...", flush=True)

    try:
        response = requests.post(api_url + "/home-cam",
            data=f"Someone is at the door. [Check here]({camera_feed_url}).",
            headers={
                "Tags": "bell,door",
                "Priority": "5",
                "Markdown": "yes",
                "Authorization": "Bearer " + api_token
            })

        if response.status_code == 200:
            print("Notification send successfully call successful!", flush=True)
        else:
            print(f"NOTIFY call failed with status code: {response.status_code}", flush=True)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}", flush=True)

button.when_pressed = action_on_door_bell_ring

print("Listening for door bell signal...", flush=True)

pause()
