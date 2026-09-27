# Beginner's guide: remapping your Vader 5 Pro on a Mac

**What "remapping" means:** you choose what a button does. For example, you
can make a back paddle act as the **A** button, so you can jump without taking
your thumb off the right stick. The settings are saved inside the controller,
so they keep working in every game and on every computer, even when
Paddlesmith is closed.

**Your extra buttons:**

- **M1–M4:** the paddles on the back.
- **M5 and M6:** the extra bumpers on the top edge.
- **C and Z:** the two small buttons next to A and B on the front.

## Before you start

1. **Plug the controller in** with its USB cable. This is more reliable than
   the wireless dongle while you're setting things up.
2. **Check the switch on the back** is on the left position, with the
   USB-stick picture. Bluetooth mode won't work for setting up.
3. **Press the Flydigi logo button** in the middle to wake the controller.

## Step 1: Open Paddlesmith

- Open **Launchpad** or your **Applications** folder and click
  **Paddlesmith**.
- On the **Device** page you should see "Vader 5 Pro" and a battery level.
- If the bottom of the window says **"No Flydigi controller found"**, unplug
  the cable, plug it back in, press the logo button, then quit and reopen the
  app.

## Step 2: Make a safety copy (once)

This saves your current settings so you can always go back to how things
were.

1. Open **Terminal**: press ⌘ + Space, type *Terminal*, and press Return.
2. Copy and paste this line, then press Return:

   ```sh
   "/Applications/Paddlesmith.app/Contents/Resources/app/flydigi-cli" backup
   ```

3. You should see "Backed up 4 profiles". Close Terminal.

## Step 3: Find out which paddle is which

1. Click **Test** in the left-hand menu, then **Start testing**.
2. Squeeze one paddle. The **Pressed** line shows its name, for example
   **M1**.
3. Try each one and note which is which, then click **Stop testing**.

## Step 4: Choose what each button does

1. Click **Profiles**.
2. Under **Onboard profile**, choose a profile. The controller holds four
   separate set-ups. For your first try, pick **Profile 1**.
3. In the controller picture, **click the button you want to change**, for
   example **M1**. It turns **blue**.
4. Under **Select a button**, open **Emits** and choose what it should act
   as, for example **A**.
5. The button turns **amber**, which means "changed". Repeat for any other
   buttons.
6. Click the green **Write to controller** button. When "unsaved changes"
   disappears, it's saved.
7. Click **Make active** so the controller uses this profile. Saving doesn't
   switch profiles on its own.

**Optional: Turbo.** With a button selected, set **Turbo** to a number. The
button then fires that many times per second while held. Leave it on **off**
if you don't want this.

## Step 5: Check it works

1. Go to **Test**, click **Start testing** and press the paddle.
2. You'll see something like **M1 → A**, which means it's working.
3. Click **Stop testing**, open a game and try it.

## Undoing a change

- **One button:** in **Profiles**, click it, set **Emits** to **default
  (itself)**, then click **Write to controller**.
- **Everything:** in Terminal, run the same line as in Step 2 but with
  `restore` and the backup folder instead of `backup`. The folder name was
  printed when you made the backup.

## Nice extras (optional)

These are in **Settings** in the app:

- **Fast swap config** lets you switch profiles without the app. Hold
  **Fn** (the small ○ button on the back) and press **A/B/X/Y** for profiles
  1–4.
- **Turbo function** lets you remap on the controller itself. Hold the
  **Turbo** button on the back plus a paddle for 1.5 seconds, press the
  button it should copy, then press **Turbo** again.

## If something goes wrong

- **The app can't see the controller**, or says a **Switch Pro Controller**
  or **Xbox controller** is connected: the switch on the back is in the wrong
  position. Slide it all the way **left** (the USB-stick picture) and press the
  Flydigi logo button. The app finds it on its own within a couple of seconds.
- **macOS says the app isn't allowed:** open **System Settings → Privacy &
  Security → Input Monitoring**, turn on **Paddlesmith**, then reopen it.
- **A warning mentions the firmware:** the app has stopped itself from writing
  anything, so nothing has been changed. Please open an issue on GitHub.
