import os
from signal import pause

import requests
from gpiozero import Button

GPIO_PIN = 17


def action_on_door_bell_ring(api_url, api_token, camera_feed_url):
    print("Door bell rang... Executing actions...", flush=True)

    try:
        response = requests.post(
            api_url.rstrip("/") + "/home-cam",
            data=f"Someone is at the door. [Check here]({camera_feed_url}).",
            headers={
                "Tags": "bell,door",
                "Priority": "5",
                "Markdown": "yes",
                "Authorization": "Bearer " + api_token
            },
            timeout=10,
        )

        if response.status_code == 200:
            print("Notification sent successfully!", flush=True)
        else:
            print(f"NOTIFY call failed with status code: {response.status_code}", flush=True)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}", flush=True)


def main():
    api_url = os.getenv("NOTIFY_API_URL", "")
    api_token = os.getenv("NOTIFY_API_TOKEN", "")
    camera_feed_url = os.getenv("CAMERA_FEED_URL", "")

    if not api_url or not api_token:
        raise SystemExit("NOTIFY_API_URL and NOTIFY_API_TOKEN must be configured.")

    # Keep GPIO 17 LOW while idle and trigger when the input becomes HIGH.
    button = Button(GPIO_PIN, pull_up=False, bounce_time=0.1)
    button.when_pressed = lambda: action_on_door_bell_ring(
        api_url, api_token, camera_feed_url
    )

    print(f"Listening for a HIGH signal on GPIO {GPIO_PIN}...", flush=True)
    pause()


if __name__ == "__main__":
    main()
