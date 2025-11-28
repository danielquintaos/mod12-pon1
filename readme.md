
````markdown
# Pico W Reaction Game on NixOS 🎮🐧

A tiny terminal-based reaction game written in Python that runs on **NixOS**, controlled by **four physical buttons** connected to a **Raspberry Pi Pico W**.

- The **Pico W** runs MicroPython and sends button presses over USB serial (`UP`, `DOWN`, `LEFT`, `RIGHT`) 🔁
- The **host machine (NixOS)** runs a single Python file (`pico_reaction_game.py`) that reads those events and runs a reaction game in the terminal 🖥️
- Arrow keys on the keyboard also work, so you can test even without the Pico ⌨️

---

## 📁 Project Layout

- `pico_reaction_game.py` – single-file terminal game for NixOS.
- `main.py` (on the Pico W) – MicroPython script that:
  - Configures 4 GPIO pins as inputs with pull-ups.
  - Detects button presses.
  - Sends `UP` / `DOWN` / `LEFT` / `RIGHT` over USB serial.

---

## ✅ Requirements

### 🔧 Hardware

- 1 × Raspberry Pi Pico W
- 4 × momentary push buttons
- Breadboard + jumper wires
- USB cable (Pico W ↔ NixOS machine)

### 💿 Software (NixOS host)

- NixOS with `nix-shell` available
- Python serial library:
  - Provided via `python3Packages.pyserial`
- (Optional) `pip` if you want extra tools like `mpremote`

### 🧠 Software (Pico W)

- MicroPython UF2 for **Raspberry Pi Pico W**  
  (e.g. `RPI_PICO_W-20250911-v1.26.1.uf2`)

---

## 1️⃣ Flash MicroPython to the Pico W 🔥

1. Download MicroPython UF2 for **Pico W** from the MicroPython site.
2. Unplug the Pico W.
3. Hold the **BOOTSEL** button.
4. While holding BOOTSEL, plug in the Pico W via USB.
5. Release BOOTSEL – a drive named **`RPI-RP2`** should appear.
6. Copy the UF2 file:

   ```bash
   cp ~/Downloads/RPI_PICO_W-*.uf2 /run/media/$USER/RPI-RP2/
````

The Pico will reboot automatically into MicroPython 🔁

---

## 2️⃣ Serial device & permissions on NixOS 🔐

Check that the Pico appears as a serial device:

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
# Example:
# /dev/ttyACM0
```

You may need to add your user to the group that owns `/dev/ttyACM0`
(often `uucp` or `dialout`). In `configuration.nix`:

```nix
{
  users.users.hegel = {
    isNormalUser = true;
    extraGroups = [ "wheel" "networkmanager" "uucp" "dialout" ];
  };
}
```

Then:

```bash
sudo nixos-rebuild switch
# Then log out / back in or reboot
sudo systemctl reboot
```

After that, you should be able to open `/dev/ttyACM0` as your normal user 👍

---

## 3️⃣ MicroPython REPL sanity check 🧪

Enter a shell with `pyserial`:

```bash
nix-shell -p python3Packages.pyserial
python3 -m serial.tools.miniterm /dev/ttyACM0 115200
```

You should see:

```text
--- Miniterm on /dev/ttyACM0  115200,8,N,1 ---
--- Quit: Ctrl+] | Menu: Ctrl+T | Help: Ctrl+T followed by Ctrl+H ---
```

Press **`Ctrl+D`** in miniterm to soft reboot MicroPython and you should get:

```text
MicroPython v1.26.1 on 2025-09-11; Raspberry Pi Pico W with RP2040
>>>
```

Now you know MicroPython is running ✅

---

## 4️⃣ MicroPython script (`main.py`) on the Pico W 🧾

On the MicroPython REPL (`>>>`), create `main.py` with:

```python
lines = [
"from machine import Pin",
"import time",
"import sys",
"",
"# Map names to GPIO pins",
"buttons = {",
'    \"UP\": Pin(2, Pin.IN, Pin.PULL_UP),',
'    \"DOWN\": Pin(3, Pin.IN, Pin.PULL_UP),',
'    \"LEFT\": Pin(4, Pin.IN, Pin.PULL_UP),',
'    \"RIGHT\": Pin(5, Pin.IN, Pin.PULL_UP),',
"}",
"",
"prev = {name: pin.value() for name, pin in buttons.items()}",
"",
"def send(line):",
"    # Write to USB serial as a line",
'    sys.stdout.write(line + \"\\n\")',
"",
"while True:",
"    for name, pin in buttons.items():",
"        val = pin.value()",
"        # Falling edge: HIGH -> LOW = button press",
"        if val == 0 and prev[name] == 1:",
"            send(name)",
"        prev[name] = val",
"    time.sleep(0.01)",
]

code = "\n".join(lines)
f = open("main.py", "w")
f.write(code)
f.close()
```

Then soft reboot:

```text
Ctrl+D
```

`main.py` will now auto-run on boot and send a line (`UP`/`DOWN`/`LEFT`/`RIGHT`) each time the corresponding button is pressed 📨

---

## 5️⃣ Wiring 🧵

The script uses GPIO pins **GP2, GP3, GP4, GP5** with pull-ups:

```python
"UP":    Pin(2, Pin.IN, Pin.PULL_UP),
"DOWN":  Pin(3, Pin.IN, Pin.PULL_UP),
"LEFT":  Pin(4, Pin.IN, Pin.PULL_UP),
"RIGHT": Pin(5, Pin.IN, Pin.PULL_UP),
```

With the Pico held **USB at the top**, left side:

* Pin 1: GP0
* Pin 2: GP1
* Pin 3: GND
* Pin 4: **GP2** (UP) ⬆️
* Pin 5: **GP3** (DOWN) ⬇️
* Pin 6: **GP4** (LEFT) ⬅️
* Pin 7: **GP5** (RIGHT) ➡️
* Pin 8: GND

Wire each button:

* One leg → GP2 / GP3 / GP4 / GP5
* Other leg → GND

So:

* UP   button: `GP2 ─ button ─ GND`
* DOWN button: `GP3 ─ button ─ GND`
* LEFT button: `GP4 ─ button ─ GND`
* RIGHT button: `GP5 ─ button ─ GND`

Use the Pico’s internal pull-ups — **no external resistors needed** 🙌

To test: with `miniterm` open and `main.py` running, press a button; you should see `UP`, `DOWN`, etc. printed.

---

## 6️⃣ Host game (`pico_reaction_game.py`) on NixOS 🕹️

Save the game script as `pico_reaction_game.py` in your home directory.

Start a shell with Python + pyserial:

```bash
nix-shell -p python3 python3Packages.pyserial
```

Run the game:

```bash
python3 pico_reaction_game.py --port /dev/ttyACM0
```

### 🎛 Controls

* **Pico buttons**:

  * GP2 → UP ⬆️
  * GP3 → DOWN ⬇️
  * GP4 → LEFT ⬅️
  * GP5 → RIGHT ➡️
* **Keyboard**:

  * Arrow keys for input ⌨️
  * `q` to quit ❌

### 🎯 Gameplay

* The game shows a random direction (`UP/DOWN/LEFT/RIGHT`) and a timer.
* Press the matching button before the timer runs out ⏱️
* You start with 3 lives ❤️❤️❤️
* Wrong or late input costs a life 💔
* Your score increments for each correct, timely response 🏆

---

## 7️⃣ Troubleshooting 🩺

### 🚫 Permission denied for `/dev/ttyACM0`

* Make sure your user is in `uucp` / `dialout` in `configuration.nix`.
* Reboot after changing groups.
* As a **temporary test** (not a permanent fix), you can run:

  ```bash
  sudo chmod a+rw /dev/ttyACM0
  ```

### ❓ No MicroPython prompt

* Check you flashed the **Pico W** MicroPython UF2 (not regular Pico).
* Re-enter BOOTSEL mode and re-flash if needed.

### 🔇 Buttons don’t register

* Check `miniterm` while pressing buttons; you should see `UP/DOWN/LEFT/RIGHT`.
* Make sure each button connects **the correct GPIO** to **GND**.
* Ensure the button orientation is correct on the breadboard (opposite legs, not same side).

---

## 8️⃣ Extending the project 🚀

Some ideas:

* Add score persistence (high scores saved to a file on the host) 📈
* Add more buttons or combo moves 🎛️
* Use LEDs on the Pico to flash on success / failure 💡
* Port the terminal UI to a simple graphical frontend (e.g. pygame), still keeping the Pico as an input device 🖼️

---

Happy hacking! 🎮🕹️🐍

```
```

