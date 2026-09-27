# Paddlesmith

**Program the back paddles and extra buttons of a Flydigi Vader 5 Pro on a
Mac, with no Windows needed.**

Flydigi's configuration software, Space Station, only runs on Windows.
Paddlesmith is a free, unofficial Mac app that does the most useful part of
its job:

- Remap the back paddles **M1–M4**, the extra bumpers **M5/M6** and the
  **C/Z** buttons to any button.
- Set turbo (rapid fire) per button.
- Record macros.
- Manage the controller's **four onboard profiles**.
- Turn hardware features on or off, such as the Turbo button, fast profile
  swap and the sleep timer.
- Back up and restore everything.

Settings are saved **on the controller itself**, so they work in every game,
on every computer, with nothing running in the background.

> Unofficial and not affiliated with Flydigi. Flydigi, Vader and Space
> Station are trademarks of their owner and are used only to say what this is
> compatible with.

## Install

1. Download `Paddlesmith-x.y.z.zip` from the
   [Releases](../../releases) page and double-click it to unzip.
2. Drag **Paddlesmith** into your **Applications** folder.
3. Open it. The app isn't notarised by Apple, so the first time macOS blocks
   it:
   - **macOS 15 and later:** open **System Settings → Privacy & Security**,
     scroll down and click **Open Anyway** next to the Paddlesmith message.
   - **macOS 14 and earlier:** right-click the app, choose **Open**, then
     click **Open**.
4. On first launch it downloads its components, which takes about a minute.
   If your Mac asks to install **Command Line Tools**, click **Install**,
   wait for it to finish, then open Paddlesmith again.

## Use

1. Set the switch on the back of the controller to the **USB-stick
   position** and connect it with the USB cable or the 2.4 GHz dongle.
   Bluetooth mode can't be configured.
2. **Test** page: press a paddle to see its name (M1, M2…).
3. **Profiles** page: click a button on the picture, choose what it
   **Emits**, then click **Write to controller**. Click **Make active** to
   switch the controller to that profile.
4. **Test** page again: pressing the paddle shows e.g. `M1 → A`.

A step-by-step beginner's guide is in [docs/GUIDE.md](docs/GUIDE.md).

## Command line

Everything is also available from Terminal:

```sh
APP="/Applications/Paddlesmith.app/Contents/Resources/app"
"$APP/flydigi-cli" info          # model, battery, firmware
"$APP/flydigi-cli" backup        # do this before your first change
"$APP/flydigi-cli" remap M1 A    # make paddle M1 press A
"$APP/flydigi-cli" remap M1 --clear
"$APP/flydigi-cli" --help
```

Backups are saved in `~/Library/Application Support/Paddlesmith/backups`.

## Compatibility

| | |
|---|---|
| Controller | Flydigi Vader 5 Pro. Other Flydigi models are untested. |
| Firmware | Tested on 7.1.5.0 and 7.1.5.4. If a future firmware changes the settings format, the app refuses to write rather than guess. |
| macOS | 11 or later, Apple silicon or Intel. |
| Connection | USB cable or the 2.4 GHz dongle. Not Bluetooth. |

**Firmware updates are deliberately not supported.** A failed flash is the
one thing that can make a controller unusable, so do those from the Windows
app.

## Troubleshooting

- **"No Flydigi controller found"**, or a message that a **Switch Pro
  Controller** or **Xbox controller** is connected: the switch on the back of
  the controller is in the wrong position. Slide it all the way **left** (the
  USB-stick picture), connect the cable or dongle, and press the Flydigi logo
  button. Paddlesmith connects on its own within a couple of seconds.
- **"macOS refused access"**: go to **System Settings → Privacy & Security →
  Input Monitoring**, turn on Paddlesmith, then reopen it.
- **Something went wrong after a change**: restore your backup with
  `flydigi-cli restore <backup folder>`.

Please report problems in [Issues](../../issues). Include your macOS
version, your firmware version (`flydigi-cli info`) and the output of the
failing command run with `--trace`.

## How it works

The controller has a vendor-defined USB HID interface (usage page `0xFFA0`)
that accepts small command frames. The protocol was documented by the
[flydigi-vader-pro-5-ctl](https://github.com/rR6kULhc5xgS/flydigi-vader-pro-5-ctl)
project for Linux. Paddlesmith is a port of that project: it adds a macOS
transport built on IOKit (`flydigi/iokit.py`, using ctypes with no extra
dependencies), Mac packaging and small UI fixes. See [CLAUDE.md](CLAUDE.md)
and `docs/protocol-*.md` for the protocol details.

Build the app yourself:

```sh
python3 -m venv .venv && .venv/bin/pip install PyQt5
scripts/build-app.sh 0.1.0      # -> dist/Paddlesmith.app and a zip
```

## Credits and licence

MIT licence. Based on
[flydigi-vader-pro-5-ctl](https://github.com/rR6kULhc5xgS/flydigi-vader-pro-5-ctl)
by rR6kULhc5xgS (MIT). Its original README is kept in
[docs/UPSTREAM-README.md](docs/UPSTREAM-README.md).

Provided as is, with no warranty. It writes to your controller's memory. It
backs up and verifies what it writes, but you use it at your own risk.
