# My DIY Home Camera System 🏡🎥

## Pre-requirements

- A powerful Raspberry PI for your mothership - preferably Raspberry PI 4 or 5.
- "n" number of child nodes. A Raspberry Pi 3B+ or Raspberry Pi Zero 2 W is enough for the optimized child stream. For the camera, Raspberry Pi Camera Module 3 or a compatible IMX219 module such as Waveshare IMX219-120 works.

## Optional Tailscale setup

Tailscale is useful when the mothership and child nodes are on different networks. It is not required when all devices communicate directly over the same trusted LAN, which avoids sending continuous RTSP traffic through the tailnet.

If you need it on the mothership and children:

- Install Tailscale - `curl -fsSL https://tailscale.com/install.sh | sh`
- Generate a short-lived or reusable auth key from the Tailscale admin settings as appropriate.
- Join the node - `sudo tailscale up --authkey <YOUR_AUTH_KEY>`
- Never commit the auth key.

## Mothership setup

💡 For mothership go with a stronger PI, like PI 4 or 5.

So! You got your fresh PI?!

Let's set it up as the mothership.

- Flash the Raspberry PI OS using Raspberry PI imager (or whatever method you prefer).
  - 💡 Just a quick note on this, that if you are comfortable then go with the Lite version! Trying to keep things as much light as possible, else its fine to use the GUI one also.
- Now that's done? - your PI is now ready.
- Now connect to your PI. Use monitor and all or a simple SSH your wish. My way? -
  - I just connect my PI to my laptop using USB to power up the PI.
  - Then connect to the same internet my PI is connected to.
    - 💡 For this setup just remember two things during setting up the OS -
      - Note the hostname of the PI. For example I set it to - `home.local`.
      - Be sure to check the `Enable SSH` checkbox.
  - ⏳ Now go ahead and give the PI some time to boot up and connect to the internet.
  - And then SSH into it like - `ssh admin@home.local`.
- Do a quick system update - `sudo apt update` & `sudo apt upgrade`.
- Install git - `sudo apt install git`.
- Setup Docker 🐳
  - Run `curl -sSL https://get.docker.com | sh` to install Docker.
  - Run `sudo usermod -aG docker admin`, to add your user to the `docker` user group, so that you don't have to run the commands using `sudo` every time.
  - Reboot your PI - `sudo reboot`
- Ok now you have Docker installed!
- Clone this repository - `git clone https://github.com/Souptik2001/home-cam.git`.
- Enter the mothership directory and create the local environment file:
  - `cd home-cam/mothership`
  - `cp .env.example .env`
- Set `FRIGATE_CAM1_RTSP_HOST` and `FRIGATE_CAM2_RTSP_HOST` to the cameras' LAN or Tailscale addresses. Set `FRIGATE_BIND_IP` to the mothership's reserved LAN address for LAN access, or keep `127.0.0.1` when only a local tunnel/reverse proxy should reach it. If binding to a LAN address, reserve that address in DHCP first; Docker cannot bind to an address the host no longer owns.
- Validate and start it:
  - `docker compose config --quiet`
  - `docker compose up -d`
  - `docker compose ps`
- The pinned deployment uses Frigate `0.17.1`, low streams at 640×360 for processing, high streams for recording, object detection disabled, and three-day motion retention.

Your authenticated camera UI is available at `https://<FRIGATE_BIND_IP>:<FRIGATE_PORT>` (port `8971` by default). Frigate uses a self-signed certificate unless you provide your own, so a browser warning is expected on a fresh LAN deployment. Complete Frigate's first-user setup before relying on LAN access. Port `5000` is intentionally not published to the host because it is Frigate's unauthenticated internal endpoint.

### Optional Cloudflare Access endpoint

The Compose file includes a `cloudflared` profile, but it is deliberately off by default. First create a Cloudflare Access application and policy for the hostname; never publish an unauthenticated Frigate origin directly to the Internet. Then save the tunnel token at `mothership/secrets/cloudflared-token` with mode `0600` and run:

```bash
docker compose --profile cloudflare up -d
```

The token, `.env`, database, and recordings are ignored by Git and must never be committed.

## Child nodes setup

Same steps for each of the child nodes (automatic steps below this section) -

- Connect your camera module to the `CSI-2 camera connector` port of your PI. For Raspberry Pi 3B+, use a normal 15-pin CSI camera cable.
- Do all the same steps as you have done above for mothership till cloning this repository.
- Install the camera and streaming tools - `sudo apt update`, then `sudo apt install rpicam-apps ffmpeg`.
- For third-party IMX219 modules like Waveshare IMX219-120, explicitly enable the sensor overlay:
  - Edit `/boot/firmware/config.txt`.
  - Under `[all]`, add `dtoverlay=imx219`.
  - Reboot the Pi - `sudo reboot`.
- Confirm that the camera is detected - `rpicam-vid --list-cameras`.
  - For Waveshare IMX219-120, you should see `imx219` and modes such as `1640x1232`, `1920x1080`, and `3280x2464`.
- Install the child publisher using the pinned, checksum-verified installer:
  - `cd home-cam`
  - Waveshare/IMX219: `chmod +x child/install-child.sh && ./child/install-child.sh imx219`
  - Camera Module 3/IMX708: `chmod +x child/install-child.sh && ./child/install-child.sh imx708`
- The installer selects `arm64` or `armv7` from `uname -m`, installs MediaMTX `1.18.2`, verifies the release archive SHA-256, installs the shared script/service, and creates `/etc/default/pi-camera-stream` only when it does not already exist.
- Do not substitute a floating “latest” MediaMTX download during provisioning. Upgrades should be deliberate repository changes followed by regression tests.
- Streams are then available at:
  - High/record stream - `rtsp://<pi-address>:8554/high`
  - Low/detect stream - `rtsp://<pi-address>:8554/low`
- Add the child's address to `mothership/.env`, then run `cd mothership && docker compose up -d`. A full `docker compose down` is unnecessary.

MediaMTX permits publishing only from the child's loopback interface, so another LAN client cannot replace the camera stream. Anonymous reading is limited to loopback, RFC1918 private networks, and the Tailscale address range. RTSP must never be port-forwarded or exposed publicly. On an untrusted LAN, further restrict TCP port `8554` to the mothership with the Pi firewall, or enforce the equivalent Tailscale ACL.

The per-node environment defaults to the detected sensor mode, 30 FPS, a 30-frame keyframe interval, and a 4 Mbps high-stream bitrate. Sensor-specific values stay in `/etc/default/pi-camera-stream`; the shared service and stream script remain identical across nodes.

Do not generate timestamps from wall-clock arrival time for the raw H.264 pipe. The camera can deliver frames in bursts; wall-clock arrival timestamps can therefore become duplicated or non-monotonic. `pi-camera-stream.sh` declares the raw input frame rate deterministically instead.

After installation, validate both streams before adding the child to Frigate:

```bash
ffprobe -v error -rtsp_transport tcp \
  -show_entries stream=codec_name,width,height,r_frame_rate,avg_frame_rate \
  -of default=noprint_wrappers=1 rtsp://127.0.0.1:8554/high

ffprobe -v error -rtsp_transport tcp \
  -show_entries stream=codec_name,width,height,r_frame_rate,avg_frame_rate \
  -of default=noprint_wrappers=1 rtsp://127.0.0.1:8554/low

timeout 35 ffmpeg -v error -xerror -rtsp_transport tcp \
  -i rtsp://127.0.0.1:8554/high -t 30 -map 0:v:0 -f null -

timeout 35 ffmpeg -v error -xerror -rtsp_transport tcp \
  -i rtsp://127.0.0.1:8554/low -t 30 -map 0:v:0 -f null -

vcgencmd get_throttled
```

Both decode commands must exit successfully without corrupt-frame or timestamp errors. `vcgencmd get_throttled` should report `throttled=0x0`; undervoltage or throttling can corrupt/stall the camera pipeline and must be fixed at the PSU/cable rather than hidden in software.

If you have multiple networks in your home, then set all of them up through - `nmtui` - its a Terminal User Interface to manage networks.

If you have your frigate server within your home-network -

- If your Frigate server is within your home-network, then you can use the PI's local IP instead of tailscale IP.
- By default the local IP of the PI will change everytime you refresh the PI.
- To fix that you can use something called reserved IPs in your router. In maximum of the routers you have a section to reserve a particular IP for a mac address. So, you can reserve a particular IP for your PI's mac address.

Network watchdog -

- One more problem you might have is, when your PI get's disconnected from the internet, it does not automatically reconnect.
- Therefore there is a watchdog service, which runs on your PI every 2 minutes.
- It checks if your connectivity to the Frigate server is up. If not, then it first reloads your network manager, and then if still not, then reboots the PI.

## Battle-tested?

Will be in few months! 😉
