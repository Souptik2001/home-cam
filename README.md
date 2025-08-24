# Home Camera System

## Pre-requirements

- A domain you own.
- Cloudflare account (you can create a free one, you just need to add a payment option, but it will not be charged for what we will use it for).

💡 These two things are needed if you want to access your cameras from anywhere, i.e outside your home network. If you don't want that, then these two are not required.

## Cloudflare Tunnel setup

💡 If you are not going with the public URL approach, then skip this step.

Assuming you have already setup your cloudflare account and linked your domain to it, here are the next steps -

- Go to Cloudflare tunnel.
- Add a new tunnel.
- 📝 Note the token, will be used in mothership setup.
- Go to `Public Hostnames`.
- We will need to add two -
  - First will be for camera.
    - Name the Hostname to whatever you want. `xyz.yourdomain.com`.
    - And for the service, use type as `http` and URL as `motioneye:8765`.
  - Second one will be for NTFY srevice.
    - Again name the hostname to whatever you want. `pqr.yourdomain.com`.
    - And for the service, use type as `http` and URL as `ntfy:80`.

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
  - If you are using public URL approach -
    - In the `ntfy` service, go ahead and modify the `<THIS_SERVICE_PUBLIC_URL>`, with this service's public URL, so suppose you get it on `mynotify.dev`, then `http://mynotify.dev`.
    - In the `cloudflared` service, go ahead and modify the `<TOKEN>` with your Cloudflare tunnel token.
  - If you are not going for the public URL approach -
    - Comment out or remove the whole `cloudflared` service.
    - Uncomment the two lines mentioned mentioned in the file.
    - Comment out the line which contains - `<THIS_SERVICE_PUBLIC_URL>`.
- Now just run the docker compose - `docker compose up`.
- And volah! It's done! 🎉

If you have opted for public URL then your camera web UI is accessible on - `xyz.yourdomain.com` (the name you setup on Cloudflare tunnel).
If you have not opted for public URL then your camera web UI is accessible on - `home.local:8765` (the hostname you have set for your PI) - considering you are connected to the same internet your PI is connected to.

### NTFY setup

This is kind of a sub-step inside mothership setup. Once you are done with all above things -

- Run `docker exec -it ntfy sh`.
- With this you hop on to a shell inside your ntfy container.
- Now run - `ntfy user add --role=<admin_or_user> <any_user_name>`.
- It will prompt for password, enter the password.
- And done! Your user is now created! 🎉

## Child setup

On its way.. 👀
