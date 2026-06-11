# Door Bell GPIO Listener

This service watches GPIO 17 and sends an ntfy notification when the input
changes from LOW to HIGH. It runs directly under systemd, so Docker is not
required.

The service uses the `pigpio` pin factory. The `pigpiod` daemon must be
installed and running on the Raspberry Pi.

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
sudoedit /etc/home-cam-door-bell.env

sudo install -m 0644 home-cam-door-bell.service /etc/systemd/system/home-cam-door-bell.service
sudo systemctl enable --now pigpiod.service
sudo systemctl daemon-reload
sudo systemctl enable --now home-cam-door-bell.service
```

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
