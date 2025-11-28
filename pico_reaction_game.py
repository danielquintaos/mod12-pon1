#!/usr/bin/env python3
import argparse
import curses
import queue
import random
import threading
import time
import sys

try:
    import serial  # pyserial
except ImportError:
    serial = None


# ---------------------- Serial reader thread ---------------------- #

def serial_reader(port, baudrate, event_queue, stop_event):
    if serial is None:
        return

    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=0)
    except Exception as e:
        # Put an error message in the queue and bail out
        event_queue.put(("ERROR", f"Failed to open serial port {port}: {e}"))
        return

    buf = b""
    valid = {"UP", "DOWN", "LEFT", "RIGHT"}

    while not stop_event.is_set():
        try:
            data = ser.read(32)
        except Exception as e:
            event_queue.put(("ERROR", f"Serial read error: {e}"))
            break

        if data:
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                text = line.strip().decode(errors="ignore").upper()
                if text in valid:
                    event_queue.put(("BTN", text))
        else:
            time.sleep(0.01)

    try:
        ser.close()
    except Exception:
        pass


# ---------------------- Game logic ---------------------- #

def run_game(stdscr, args):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    height, width = stdscr.getmaxyx()

    # Serial event queue
    event_queue = queue.Queue()
    stop_event = threading.Event()
    serial_thread = None
    serial_enabled = False
    serial_error_msg = None

    if args.port and serial is not None:
        serial_thread = threading.Thread(
            target=serial_reader,
            args=(args.port, args.baudrate, event_queue, stop_event),
            daemon=True,
        )
        serial_thread.start()
        serial_enabled = True
    elif args.port and serial is None:
        serial_error_msg = "pyserial not installed; running with keyboard only."

    directions = ["UP", "DOWN", "LEFT", "RIGHT"]
    score = 0
    lives = 3
    round_no = 0
    target = None
    prompt_time = 0.0
    max_reaction = args.reaction_time
    last_info_msg = ""
    last_error_msg = serial_error_msg or ""

    while True:
        now = time.time()

        # Start a new round if needed
        if target is None and lives > 0:
            target = random.choice(directions)
            prompt_time = now
            round_no += 1
            last_info_msg = f"Round {round_no}! Press {target}!"

        # Check time-out
        if target is not None and (now - prompt_time) > max_reaction:
            lives -= 1
            last_info_msg = f"Too slow! It was {target}."
            target = None

        # Draw UI
        stdscr.erase()

        title = "Pico Reaction Game"
        stdscr.addstr(1, max(0, (width - len(title)) // 2), title, curses.A_BOLD)

        # Status line
        status = f"Score: {score}   Lives: {lives}   Reaction window: {max_reaction:.1f}s"
        stdscr.addstr(3, max(0, (width - len(status)) // 2), status)

        # Target prompt
        if target is not None:
            big = f">>> {target} <<<"
        else:
            big = "Get ready..."
        stdscr.addstr(height // 2, max(0, (width - len(big)) // 2), big, curses.A_STANDOUT)

        # Info / error lines
        if last_info_msg:
            stdscr.addstr(height - 4, 2, last_info_msg[:width - 4])
        if last_error_msg:
            stdscr.addstr(height - 3, 2, ("Error: " + last_error_msg)[:width - 4])

        # Help line
        help_line = "Controls: 4 Pico buttons (UP/DOWN/LEFT/RIGHT) or arrow keys. Press 'q' to quit."
        stdscr.addstr(height - 2, max(0, (width - len(help_line)) // 2), help_line[:width - 2])

        stdscr.refresh()

        # Game over?
        if lives <= 0:
            msg = f"Game over! Final score: {score}. Press 'q' to quit."
            stdscr.addstr(height // 2 + 2, max(0, (width - len(msg)) // 2), msg)
            stdscr.refresh()
            # Wait for q
            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                break
            time.sleep(0.05)
            continue

        # -------- Handle inputs -------- #
        action = None

        # 1) Consume all queued serial events
        try:
            while True:
                etype, payload = event_queue.get_nowait()
                if etype == "BTN":
                    action = payload  # last one wins
                elif etype == "ERROR":
                    last_error_msg = payload
        except queue.Empty:
            pass

        # 2) Keyboard input
        key = stdscr.getch()
        if key != -1:
            if key in (ord("q"), ord("Q")):
                break
            elif key == curses.KEY_UP:
                action = "UP"
            elif key == curses.KEY_DOWN:
                action = "DOWN"
            elif key == curses.KEY_LEFT:
                action = "LEFT"
            elif key == curses.KEY_RIGHT:
                action = "RIGHT"

        # 3) Apply action
        if action is not None and target is not None:
            if (now - prompt_time) <= max_reaction:
                if action == target:
                    score += 1
                    last_info_msg = f"Nice! {action} was correct."
                else:
                    lives -= 1
                    last_info_msg = f"Oops! You pressed {action}, it was {target}."
            else:
                lives -= 1
                last_info_msg = f"Too late! You pressed {action}, but the timer ran out."

            target = None

        time.sleep(0.02)

    # Cleanup serial
    stop_event.set()
    if serial_thread is not None:
        serial_thread.join(timeout=1)


# ---------------------- CLI entry point ---------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Single-file Pico W reaction game for NixOS."
    )
    parser.add_argument(
        "--port",
        help="Serial port of Pico W (e.g. /dev/ttyACM0). If omitted, keyboard-only mode.",
        default=None,
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="Serial baudrate (default: 115200)",
    )
    parser.add_argument(
        "--reaction-time",
        type=float,
        default=1.5,
        help="Reaction window in seconds (default: 1.5)",
    )

    args = parser.parse_args()

    if args.port and serial is None:
        print("WARNING: pyserial is not installed. Install it or omit --port.", file=sys.stderr)

    curses.wrapper(run_game, args)


if __name__ == "__main__":
    main()

