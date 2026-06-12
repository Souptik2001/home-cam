import os
from signal import pause

import requests
from gpiozero import Button

GPIO_PIN = 17


def action_on_door_bell_ring(
    home_assistant_url,
    home_assistant_token,
    notify_service,
    camera_feed_url,
):
    print("Door bell rang... Executing actions...", flush=True)

    notify_service = notify_service.removeprefix("notify.")
    notification_data = {
        "ttl": 0,
        "priority": "high",
        "channel": "alarm_stream",
        "push": {
            "sound": {
                "name": "alarm.caf",
                "critical": 1,
                "volume": 1.0,
            }
        },
    }

    if camera_feed_url:
        notification_data["url"] = camera_feed_url
        notification_data["clickAction"] = camera_feed_url

    try:
        response = requests.post(
            (
                home_assistant_url.rstrip("/")
                + f"/api/services/notify/{notify_service}"
            ),
            json={
                "title": "Door bell",
                "message": "Someone is at the door.",
                "data": notification_data,
            },
            headers={
                "Authorization": "Bearer " + home_assistant_token,
                "Content-Type": "application/json",
            },
            timeout=10,
        )

        if response.status_code in (200, 201):
            print("Notification sent successfully!", flush=True)
        else:
            print(
                "Home Assistant notification failed with status code "
                f"{response.status_code}: {response.text}",
                flush=True,
            )

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}", flush=True)


def main():
    home_assistant_url = os.getenv("HOME_ASSISTANT_URL", "")
    home_assistant_token = os.getenv("HOME_ASSISTANT_TOKEN", "")
    notify_service = os.getenv("HOME_ASSISTANT_NOTIFY_SERVICE", "")
    camera_feed_url = os.getenv("CAMERA_FEED_URL", "")

    if not home_assistant_url or not home_assistant_token or not notify_service:
        raise SystemExit(
            "HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN, and "
            "HOME_ASSISTANT_NOTIFY_SERVICE must be configured."
        )

    # From Souptik: uncomment this block to send one test notification and exit.
    # The return prevents the GPIO listener below from being registered.
    # action_on_door_bell_ring(home_assistant_url, home_assistant_token, notify_service, camera_feed_url)
    # return

    # Keep GPIO 17 HIGH while idle and trigger when the input becomes LOW.
    button = Button(GPIO_PIN, pull_up=True, bounce_time=0.1)
    button.when_pressed = lambda: action_on_door_bell_ring(
        home_assistant_url,
        home_assistant_token,
        notify_service,
        camera_feed_url,
    )

    print(f"Listening for a LOW signal on GPIO {GPIO_PIN}...", flush=True)
    pause()


if __name__ == "__main__":
    main()
