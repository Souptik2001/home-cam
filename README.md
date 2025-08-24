# Home Camera System

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
- Now go ahead and clone this repository - `git clone git@github.com:Souptik2001/home-cam.git`.
- Now go ahead and open `mothership/docker-compose.yml`, using any editor you want and make the following changes -
  - In the `cloudflared` service, go ahead and modify the `<TOKEN>` with your Cloudflare tunnel token.
- Now just run the docker compose - `docker compose up`.
- And volah! It's done!

## Child setup

On its way.. 👀
