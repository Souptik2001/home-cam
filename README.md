# My DIY Home Camera System 🏡🎥

## Pre-requirements

- A powerful Raspberry PI for your mothership - preferably Raspberry PI 4 or 5.
- "n" number of child nodes. A Raspberry Pi 3B+ or Raspberry Pi Zero 2 W is enough for the optimized child stream. For the camera, Raspberry Pi Camera Module 3 or a compatible IMX219 module such as Waveshare IMX219-120 works.

## Tailscale setup for both mothership and children

We need to setup tailscale in both mothership and the children, because they all will be communicating through tailnet.

- Install tailscale - `curl -fsSL https://tailscale.com/install.sh | sh`
- Generate a auth key from tailscale admin settings.
- Done - `sudo tailscale up --authkey <YOUR_AUTH_KEY>`

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
- Now go ahead and clone this repository - `git clone https://github.com/Souptik2001/home-cam.git`.
- Now go ahead and open `mothership/docker-compose.yml`, using any editor you want and make the following changes -
  - Change the `password` of the Frigate service.
- Now `cd` into the `mothership` folder, and just run the docker compose - `docker compose up -d`.
- And volah! It's done! 🎉

Your camera web UI is accessible on - `home.local:5000` (the hostname you have set for your PI) - considering you are connected to the same internet your PI is connected to.

🚨⚠️ Be sure to change the admin and user credentials for the motioneye service. Because its exposed to internet and without proper credentials anyone can.. literally spy on you! 🚨

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
- Install the repository-pinned MediaMTX release. Do not substitute an untested "newest" version during provisioning. This setup is currently validated with `v1.18.2`.
  - Choose the archive matching the Pi OS architecture (`linux_arm64` for 64-bit Raspberry Pi OS, `linux_armv7` for 32-bit).
  - Download the archive and its published checksum from the [`v1.18.2` release](https://github.com/bluenviron/mediamtx/releases/tag/v1.18.2), then verify the archive before extraction.
- Extract it into `/home/<user>/mediamtx` and install this repository's `child/mediamtx.yml` as `/home/<user>/mediamtx/mediamtx.yml`.
- Record the selected architecture and verified archive hash in the node's provisioning log. Upgrades should be deliberate repository changes followed by stream regression tests, not an implicit latest-version download.
- Important next thing is much easier to do through systemctl service which I have explained in next-to-next step.
- I suggest doing the next steps in tmux, so here's a quick walkthrough for tmux -
  - Install tmux - `sudo apt install tmux`.
  - Open a new tmux session - `tmux new -s services`.
  - Run the mediamtx binary - `./mediamtx`.
  - Now open a new terminal using - "Ctrl+B" and then release both keys and press - "c".
  - Now you are in a new terminal/window.
  - Then run the command from `child/pi-camera-stream.sh` to publish `/high` and `/low`.
  - You can switch between windows using "ctrl+B" and then the window number you want to go to.
  - You can detach from tmux using "ctrl+B" and then "d", your both commands are still running even if you now detach from SSH.
  - `tmux ls` to check tmux sessions.
  - `tmux a -t services` to go inside the services session in which our commands are running.
- Now your RTSP streams are available at:
  - High/record stream - `rtsp://<pi-tailscale-ip>:8554/high`
  - Low/detect stream - `rtsp://<pi-tailscale-ip>:8554/low`
- In your mothership config you have already added this camera. Everytime you add a new camera like this, just add a new camera config block over there and restart the server `docker compose down && docker compose up -d`.

But if you see the two commands you have to run above (mediamtx and ffmpeg) are manual. So, if your PI goes off and reboots you have to again run it, to make it automatic you have to register a systemctl service.

- Install the stream script - `sudo install -m 0755 child/pi-camera-stream.sh /usr/local/bin/pi-camera-stream.sh`
- Install the systemd service - `sudo install -m 0644 child/pi-camera-stream.service /etc/systemd/system/pi-camera-stream.service`
- If your Raspberry Pi user is not `admin`, edit `/etc/systemd/system/pi-camera-stream.service` and update `User=` and `WorkingDirectory=`.
- Run `sudo systemctl daemon-reload`, then `sudo systemctl enable --now pi-camera-stream.service`.
- Check status - `systemctl status pi-camera-stream.service`.

The stream script defaults to `CAMERA_MODE=1640:1232`, which matches the full-width IMX219 mode seen on Waveshare IMX219-120. For Camera Module 3 Wide, set `Environment=CAMERA_MODE=2304:1296` in the service. The service also pins the camera output to 30 FPS, a 30-frame keyframe interval, and a 4 Mbps high-stream bitrate. Keep these values explicit so every child produces the same Frigate-compatible stream.

Do not generate timestamps from wall-clock arrival time for the raw H.264 pipe. The camera can deliver frames in small bursts, especially while under load; wall-clock timestamps then become duplicated or non-monotonic. `pi-camera-stream.sh` tells FFmpeg that the raw input is a deterministic 30 FPS stream instead.

After installation, validate both streams before adding the child to Frigate:

```bash
ffprobe -v error -rtsp_transport tcp \
  -show_entries stream=codec_name,width,height,r_frame_rate,avg_frame_rate \
  -of default=noprint_wrappers=1 rtsp://127.0.0.1:8554/high

timeout 35 ffmpeg -v error -xerror -rtsp_transport tcp \
  -i rtsp://127.0.0.1:8554/high -t 30 -map 0:v:0 -f null -

vcgencmd get_throttled
```

The decode command must exit successfully without corrupt-frame or timestamp errors. `vcgencmd get_throttled` should report `throttled=0x0`; undervoltage or throttling can corrupt/stall the camera pipeline and must be fixed at the PSU/cable rather than hidden in software.

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
