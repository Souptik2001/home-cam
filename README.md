# My DIY Home Camera System 🏡🎥

## Pre-requirements

- A powerful Raspberry PI for your mothership - preferably Raspberry PI 4 or 5.
- "n" number of [Raspberry PI Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) and [Raspberry PI camera module 2](https://www.raspberrypi.com/products/camera-module-v2/) - the number depends on how many child nodes you want.
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
- Now `cd` into the `mothership` folder, and just run the docker compose - `docker compose up -d`.
- And volah! It's done! 🎉

If you have opted for public URL then your camera web UI is accessible on - `xyz.yourdomain.com` (the name you setup on Cloudflare tunnel).

If you have not opted for public URL then your camera web UI is accessible on - `home.local:8765` (the hostname you have set for your PI) - considering you are connected to the same internet your PI is connected to.

🚨⚠️ Be sure to change the admin and user credentials for the motioneye service. Because its exposed to internet and without proper credentials anyone can.. literally spy on you! 🚨

### NTFY setup

This is kind of a sub-step inside mothership setup. Once you are done with all above things -

- Run `docker exec -it ntfy sh`.
- With this you hop on to a shell inside your ntfy container.
- Now run - `ntfy user add --role=user <any_user_name>`
  - It will prompt for password, enter the password.
- Now run - `ntfy access home home rw` - so with this we are setting our user `home` to only access the topic `home`, to which our door bell script will send notifications.
- Now run - `ntfy token add <user_name_you_created_above>` - note this token, this will be required in "door bell child node" setup.
- Now get your phone and download `ntfy` app from PlayStore or AppleStore.
  - Click on "subscribe to topic" (i.e the plus icon on the bottom).
  - Add the topic name as `home`.
  - And check "use another server".
  - Enter your ntfy server URL.
  - Now once you press "subscribe", it will prompt you for username and password.
  - So, enter `home` and the password you created and click done!
- Do the same with any other phone you want to get notifications on.
- And done! You will now get notifications on your phone! 🎉

## Child nodes setup

Same steps for each of the child nodes -

- Connect your Camera module 2 to the `CSI-2 camera connector` port of your PI.
- Do all the same steps as you have done above for mothership till cloning this repository.
- Next just go ahead and `cd` into the mothership folder and run `docker compose up -d`.
- And volah! It's done! 🎉

🚨⚠️ Be sure to change the admin and user credentials for the motioneye service. Although this is not exposed to internet as mothership, but anyone connected to your local network (i.e basically the same network your PI is connected to), can visit `camera-1.local:8765` and see the feed. 🚨

### Special door bell child node setup

For the special door bell child node, everything else remains the same, plus just two extra steps -

Hardware step -

We need to make some GPIO pins connection for this. [Here is the GPIO pins layout](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio) for Raspberry PI.

💡 It is same for all Raspberry PI models, but if you want specifically for any model you can just Google it. For this node we will use Raspberry PI zero 2 W.

Ok now so let's start with the steps -

- So, our main target is to somehow give a quick one touch connection between one of the GPIO pin (in our case we will be using 17) and a ground pin of the PI.
- So, here is how I did it. You can do it in some other way if you want.
- Connect two jumper wires to the GPIO 17 and a ground PIN on the PI side.
- The other end of the jumper wires will be connected to a relay. The relay will be connected to the door bell directly.
- So, you see? The relay acts as the separation between the door bell circuit and the raspberry PI, so that we don't have to care about stepping down door bell voltage and all.
- So, whenever the door bell is rang, it powers up the relay, which causes one quick contact in relay, exactly what we want.
- So, the GPIO and the ground pin joins for one causing low voltage in the GPIO pin, exactly what we want.
- This is then detected by the script which you will run below and it fires up the notification! Done with electrical setup! ⚡️

💡 If before directly connecting to the door bell, relay, etc. you want to give a quick test, then connect two jumper wires in GPIO and ground pin respectively. And then just touch the other end (male side) of the jumpers, just once quickly, to emulate the relay contact behaviour and trigger the notification.

Software step -

- Install `pigpio` library - `sudo apt install pigpio` (just FYI, this is required as we are running this script in docker).
- Start the `pigpio` daemon - `sudo systemctl start pigpiod` and enable it for auto-starting on system boot - `sudo systemctl enable pigpiod`.
- Go to `child/door-bell`.
- Open `docker-compose.yml` file and change the following things -
  - `<NOTIFY_API_URL>` - the NTFY URL (with no trailing slash)
  - `<NOTIFY_API_TOKEN>` - the NTFY API Token for the user your generated above.
  - `<CAMERA_FEED_URL>` - your camera feed URL.
- And just run `docker compose up -d`.
- This will start the script to listen for the door bell ring signal, and it's done!

### Adding into child nodes to your mothership's motioneye dashboard

- Go to your mothership motion eye dashboard.
- Login.
- Click on add camera.
- Select Camera type as "Remote motionEye Camera".
- Then in URL provide the child camera local URL. So, if your child camera hostname is `camera-1.local`, then in that field provide `http://camera-1.local:8081` (`8081` is the proxy port).
- Then provide username and password for that child node you have set.
- And the last camera field should be automatically selected.
- Now just go ahead and click "OK".
- And now you should see the child node's camera feed here! 🎉

## Battle-tested?

Will be in few months! 😉
