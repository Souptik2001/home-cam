# Home Camera Network Watchdog

This watchdog checks whether the Raspberry Pi can still reach the local
network. If the check fails repeatedly, it first restarts the network service
and only reboots the Pi after another failure.

The default target is the home router at `192.168.29.1`. This checks LAN/Wi-Fi
health, not public internet reachability. That is intentional: the camera only
needs local network access to stream to Frigate.

## Files

- `home-cam-network-watchdog.sh`: network check and recovery script.
- `home-cam-network-watchdog.service`: systemd unit that runs one check.
- `home-cam-network-watchdog.timer`: systemd timer that runs the check every 2 minutes.

## Install

From this directory on the Raspberry Pi:

```bash
sudo install -m 0755 home-cam-network-watchdog.sh /usr/local/bin/home-cam-network-watchdog.sh
sudo install -m 0644 home-cam-network-watchdog.service /etc/systemd/system/home-cam-network-watchdog.service
sudo install -m 0644 home-cam-network-watchdog.timer /etc/systemd/system/home-cam-network-watchdog.timer
sudo systemctl daemon-reload
sudo systemctl enable --now home-cam-network-watchdog.timer
```

## Check Status

```bash
systemctl status home-cam-network-watchdog.timer
journalctl -u home-cam-network-watchdog.service -n 50 --no-pager
```

## Change The Network Target

Edit `/usr/local/bin/home-cam-network-watchdog.sh` and change:

```bash
TARGET="192.168.29.1"
```

Good targets are the router IP or the Frigate/Kubernetes node IP. Avoid public
internet targets like `8.8.8.8`; an ISP outage should not cause the Pi to reboot.

## Disable

```bash
sudo systemctl disable --now home-cam-network-watchdog.timer
```
