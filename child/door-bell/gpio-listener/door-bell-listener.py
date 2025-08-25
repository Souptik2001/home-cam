from gpiozero import Button
import requests
from signal import pause

# Connect the input to GPIO pin 17.
# The `pull_up=True` means the pin will be HIGH when the button is not pressed
# and LOW when it is pressed.
button = Button(17, pull_up=True)

def action_on_door_bell_ring():
    api_url = "https://example.com"
    print("Door bell rang... Executing actions...")

    try:
        response = requests.get(api_url)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            print("API call successful!")
            # print("Response:", response.json())
        else:
            print(f"API call failed with status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

button.when_pressed = action_on_door_bell_ring

print("Listening for door bell signal...")

pause()
