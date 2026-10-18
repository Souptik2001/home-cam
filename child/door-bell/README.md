# Door Bell GPIO Listener

This service watches GPIO 17 and submits a signed doorbell event to Amader Home Assistant when the input changes from HIGH to LOW. It runs directly under systemd on **Pi Cam 1**; Pi Cam 2 remains a camera-only node.

The listener uses gpiozero's local `RPi.GPIO` pin factory backed by `rpi-lgpio`, so it does not need a separate GPIO daemon.

## Event flow

```text
GPIO17 connected to GND
  → Pi Cam 1 listener
  → signed HTTPS POST /api/v1/ingest/doorbell
  → durable event history
  → notification delivery to registered devices
  → notification tap opens https://camera.souptik.dev
```

The Pi and server share a doorbell-specific HMAC secret. The secret is never sent across the network. Each request includes a timestamp, unique nonce, compact JSON body, and SHA-256 HMAC signature. Retries reuse the same signed event, allowing the server's nonce-based idempotency protection to prevent duplicates.

## Configuration

Store configuration outside Git in `/etc/home-cam-door-bell.env`:

```ini
AMADER_HOME_ASSISTANT_URL=https://amader-home-assistant.souptik.dev
AMADER_DOORBELL_SOURCE=front-door
AMADER_DOORBELL_HMAC_SECRET=replace-with-the-matching-random-hmac-secret
AMADER_REQUEST_ATTEMPTS=3
AMADER_REQUEST_TIMEOUT_SECONDS=10
```

`AMADER_DOORBELL_HMAC_SECRET` must match the `front-door` entry in the server's `DOORBELL_HMAC_SECRETS` configuration. Keep the environment file root-owned and mode `0600`.

## Test without touching GPIO

Load the installed environment and call the deployed sender directly:

```sh
sudo sh -c 'set -a
. /etc/home-cam-door-bell.env
set +a
exec /opt/home-cam-door-bell/.venv/bin/python - <<"PY"
import importlib.util
import os

path = "/opt/home-cam-door-bell/door-bell-listener.py"
spec = importlib.util.spec_from_file_location("door_bell_listener", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ok = module.send_doorbell_event(
    os.environ["AMADER_HOME_ASSISTANT_URL"],
    os.environ["AMADER_DOORBELL_SOURCE"],
    os.environ["AMADER_DOORBELL_HMAC_SECRET"],
    attempts=int(os.environ.get("AMADER_REQUEST_ATTEMPTS", "3")),
    timeout=float(os.environ.get("AMADER_REQUEST_TIMEOUT_SECONDS", "10")),
)
raise SystemExit(0 if ok else 1)
PY'
```

A successful request prints `Doorbell event delivered successfully!`, creates a history entry, and sends notifications to enabled registered devices. HTTP `401` means the source, timestamp, or signature was rejected. HTTP `422` means the event body was invalid.

## Install on Pi Cam 1

The commands assume the Raspberry Pi user is `admin`:

```sh
sudo install -d -o admin -g admin /opt/home-cam-door-bell
sudo install -o admin -g admin -m 0644 gpio-listener/door-bell-listener.py /opt/home-cam-door-bell/door-bell-listener.py
sudo install -o admin -g admin -m 0644 gpio-listener/requirements.txt /opt/home-cam-door-bell/requirements.txt

sudo apt update
sudo apt install swig python3-dev liblgpio-dev

sudo -u admin python3 -m venv /opt/home-cam-door-bell/.venv
sudo -u admin /opt/home-cam-door-bell/.venv/bin/pip install -r /opt/home-cam-door-bell/requirements.txt

sudo install -m 0600 home-cam-door-bell.env.example /etc/home-cam-door-bell.env
sudo vim /etc/home-cam-door-bell.env

sudo install -m 0644 home-cam-door-bell.service /etc/systemd/system/home-cam-door-bell.service
sudo systemctl daemon-reload
sudo systemctl enable --now home-cam-door-bell.service
```

`swig`, the Python development headers, and the native `lgpio` development library are required when pip needs to build the `lgpio` Python package locally.

## Check status and logs

```sh
systemctl is-enabled home-cam-door-bell.service
systemctl is-active home-cam-door-bell.service
systemctl --no-pager --full status home-cam-door-bell.service
journalctl -u home-cam-door-bell.service -n 50 --no-pager
```

To follow logs during a physical button test:

```sh
journalctl -u home-cam-door-bell.service -f
```

## Update

```sh
sudo install -o admin -g admin -m 0644 gpio-listener/door-bell-listener.py /opt/home-cam-door-bell/door-bell-listener.py
sudo systemctl restart home-cam-door-bell.service
```

## Disable

```sh
sudo systemctl disable --now home-cam-door-bell.service
```
