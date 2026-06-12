# Door Bell GPIO Listener

This service watches GPIO 17 and sends a critical Home Assistant mobile
notification when the input changes from HIGH to LOW. It runs directly under
systemd, so Docker is not required.

The service uses gpiozero's local `RPi.GPIO` pin factory backed by
`rpi-lgpio`, so it does not need a separate GPIO daemon.

The notification requests the strongest supported alert behavior:

- Android: immediate high-priority delivery using the alarm audio stream.
- iOS: a critical alert using the default sound at full volume.

The phone and operating system must permit these behaviors. In particular,
Android notification-channel settings control whether Do Not Disturb is
overridden, and iOS must allow critical alerts for the Home Assistant app.

## Home Assistant Setup

1. Install and connect the Home Assistant Companion app on the target phone.
2. In Home Assistant, open your profile and create a long-lived access token.
3. Find the phone's notification action in **Developer Tools > Actions**. It
   normally looks like `notify.mobile_app_your_phone`.
4. Put the URL, token, and action name in
   `/etc/home-cam-door-bell.env`. The `notify.` prefix is optional.

The Raspberry Pi must be able to reach `HOME_ASSISTANT_URL`.

## Test The Notification Manually

Before installing the listener, test the Home Assistant credentials and
notification group directly. Run the following on the Raspberry Pi, replacing
the URL and service if needed:

```bash
export HOME_ASSISTANT_URL="https://home-assistant.example.com"
export HOME_ASSISTANT_NOTIFY_SERVICE="notify.doorbell_devices"
read -rsp "Home Assistant token: " HOME_ASSISTANT_TOKEN
echo

curl --fail-with-body \
  -X POST \
  -H "Authorization: Bearer ${HOME_ASSISTANT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Door bell test",
    "message": "The door bell notification is working.",
    "data": {
      "ttl": 0,
      "priority": "high",
      "channel": "alarm_stream",
      "push": {
        "sound": {
          "name": "alarm.caf",
          "critical": 1,
          "volume": 1.0
        }
      }
    }
  }' \
  "${HOME_ASSISTANT_URL%/}/api/services/notify/${HOME_ASSISTANT_NOTIFY_SERVICE#notify.}"

unset HOME_ASSISTANT_TOKEN
```

A successful request returns a JSON response and sends the alert to every
device in `notify.doorbell_devices`. An HTTP `401` response means the token is
invalid, while an HTTP `404` response usually means the notification service
name or Home Assistant URL is incorrect.

### Test Using The Python Listener

To test the actual Python notification function without registering the GPIO
listener:

1. Open `gpio-listener/door-bell-listener.py`.
2. Uncomment the test block marked `From Souptik`, including its `return`.
3. Export the configuration and run the script:

```bash
export HOME_ASSISTANT_URL="https://home-assistant.example.com"
export HOME_ASSISTANT_NOTIFY_SERVICE="notify.doorbell_devices"
export CAMERA_FEED_URL="https://camera.example.com"
read -rsp "Home Assistant token: " HOME_ASSISTANT_TOKEN
echo

python3 gpio-listener/door-bell-listener.py

unset HOME_ASSISTANT_TOKEN
```

The required Python packages must already be installed. If the service virtual
environment and `/etc/home-cam-door-bell.env` have been created, load that
root-only environment file and run the installed copy with:

```bash
sudo sh -c 'set -a
. /etc/home-cam-door-bell.env
set +a
exec /opt/home-cam-door-bell/.venv/bin/python /opt/home-cam-door-bell/door-bell-listener.py'
```

The `.` command is the portable equivalent of `source`; `source` is not
available in every shell.

After testing, comment the `From Souptik` block again so normal execution
registers the GPIO listener.

## Install

The commands below assume the Raspberry Pi user is `admin`. If yours is
different, update `User=` in `home-cam-door-bell.service` and the commands
below.

From this directory on the Raspberry Pi:

```bash
sudo install -d -o admin -g admin /opt/home-cam-door-bell
sudo install -o admin -g admin -m 0644 gpio-listener/door-bell-listener.py /opt/home-cam-door-bell/door-bell-listener.py
sudo install -o admin -g admin -m 0644 gpio-listener/requirements.txt /opt/home-cam-door-bell/requirements.txt

sudo -u admin python3 -m venv /opt/home-cam-door-bell/.venv
sudo -u admin /opt/home-cam-door-bell/.venv/bin/pip install -r /opt/home-cam-door-bell/requirements.txt

sudo install -m 0600 home-cam-door-bell.env.example /etc/home-cam-door-bell.env
sudo vim /etc/home-cam-door-bell.env

sudo install -m 0644 home-cam-door-bell.service /etc/systemd/system/home-cam-door-bell.service
sudo systemctl daemon-reload
sudo systemctl enable --now home-cam-door-bell.service
```

Example configuration:

```bash
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=replace-with-a-long-lived-access-token
HOME_ASSISTANT_NOTIFY_SERVICE=notify.mobile_app_your_phone
CAMERA_FEED_URL=https://camera.example.com
```

`CAMERA_FEED_URL` is optional. When provided, tapping the notification opens
that URL.

## Check Status And Logs

```bash
systemctl status home-cam-door-bell.service
journalctl -u home-cam-door-bell.service -n 50 --no-pager
```

To follow logs while testing the GPIO input:

```bash
journalctl -u home-cam-door-bell.service -f
```

## Update

After changing the listener:

```bash
sudo install -o admin -g admin -m 0644 gpio-listener/door-bell-listener.py /opt/home-cam-door-bell/door-bell-listener.py
sudo systemctl restart home-cam-door-bell.service
```

## Disable

```bash
sudo systemctl disable --now home-cam-door-bell.service
```
