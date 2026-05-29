# My DIY Home Camera System 🏡🎥

## Pre-requirements

- A powerful Raspberry PI for your mothership - preferably Raspberry PI 4 or 5.
- "n" number of [Raspberry PI Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) and [Raspberry PI camera module 2](https://www.raspberrypi.com/products/camera-module-v2/) - the number depends on how many child nodes you want.

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

Same steps for each of the child nodes -

- Connect your Camera module 2 to the `CSI-2 camera connector` port of your PI.
- Do all the same steps as you have done above for mothership till cloning this repository.
- Get `mediamtx` - `wget https://github.com/bluenviron/mediamtx/releases/download/v1.17.1/mediamtx_v1.17.1_linux_armv7.tar.gz` (please replace the version with newest version URL)
- Extract it - `mkdir mediamtx && tar -xvzf mediamtx_linux_armv7.tar.gz -C ./mediamtx` (Again change the file name as required)
- Replace the existing `mediamtx.yml` (inside the extracted directory) with the one I provided here, under the child directory.
- Important next thing is much easier to do through systemctl service which I have explained in next-to-next step.
- I suggest doing the next steps in tmux, so here's a quick walkthrough for tmux -
  - Install tmux - `sudo apt install tmux`.
  - Open a new tmux session - `tmux new -s services`.
  - Run the mediamtx binary - `./mediamtx`.
  - Now open a new terminal using - "Ctrl+B" and then release both keys and press - "c".
  - Now you are in a new terminal/window.
  - Install ffmpeg - `sudo apt install ffmpeg`.
  - Then run - `rpicam-vid -t 0 --inline --codec h264 --width 1280 --height 720 --framerate 30 -o - | \
ffmpeg -fflags nobuffer -flags low_delay -f h264 -r 30 -i - -c:v copy \
-f rtsp -rtsp_transport tcp rtsp://localhost:8554/cam`
  - You can switch between windows using "ctrl+B" and then the window number you want to go to.
  - You can detach from tmux using "ctrl+B" and then "d", your both commands are still running even if you now detach from SSH.
  - `tmux ls` to check tmux sessions.
  - `tmux a -t services` to go inside the services session in which our commands are running.
- Now your RTSP stream is available at - `rtsp://<pi-tailscale-ip>:8554/cam`.
- In your mothership config you have already added this camera. Everytime you add a new camera like this, just add a new camera config block over there and restart the server `docker compose down && docker compose up -d`.

But if you see the two commands you have to run above (mediamtx and the ffmppeg) are manual. So, if your PI goes off and reboots you have to again run it, to make it automatic you have to register a systemctl service.

- Create a file `/usr/local/bin/pi-camera-stream.sh` and add the content in `child/pi-camera-stream.sh`, in that file.
- Make it executable - `sudo chmod +x /usr/local/bin/pi-camera-stream.sh`
- Create a systemd service - `/etc/systemd/system/pi-camera-stream.service` and add the content of `child/pi-camera-stream.service` in that.
- Read and delete the comment on line number 8 on the service file.
- Run `sudo systemctl daemon-reload`, `sudo systemctl enable pi-camera-stream.service`, `sudo systemctl start pi-camera-stream.service`

If you have multiple networks in your home, then I recommend you to setup RaspAP (also in general you can set this up) -

- Follow this guide for easy setup - <https://docs.raspap.com/get-started/simple-setup/>
- Change RaspAP's default username and password (defaults are - `admin` and `secret`).
- Connect to all your home networks from the `Wifi Client` tab.
- Configure the Hotspot from `Hotspot` tab.
  - This will be useful when the PI is not connected to any network, then you can connect your system to that network and access the PI.
  - Most of the default settings are good, just change the SSID and password. (This hotspot will only be visible when the PI is not connected to any of the networks).

## Battle-tested?

Will be in few months! 😉
