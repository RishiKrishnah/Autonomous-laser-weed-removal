"""
Interactive console for the pan/tilt laser Arduino.

Use it to check wiring and calibrate servo angles before running detection:

    python scripts/serial_console.py --port /dev/cu.usbmodem14101

Then type firmware commands, e.g.  MOVE 90 70   STATUS   LASER ON   LASER OFF
A PING is sent in the background so the firmware watchdog does not trip
while you type; the laser still stops after the firmware max on-time.
"""

from __future__ import annotations

import argparse
import threading
import time

import serial


def main():
    parser = argparse.ArgumentParser(description="Pan/tilt laser serial console")
    parser.add_argument("--port", required=True)
    parser.add_argument("--baudrate", type=int, default=115200)
    args = parser.parse_args()

    ser = serial.Serial(args.port, baudrate=args.baudrate, timeout=0.1)
    lock = threading.Lock()
    running = True

    # Opening the port resets an Uno/Nano.
    time.sleep(2.0)

    def send(command: str) -> None:
        with lock:
            ser.write((command.strip() + "\n").encode("ascii"))

    def reader():
        while running:
            line = ser.readline().decode("ascii", errors="replace").strip()
            if line and line != "PONG":
                print(f"< {line}")

    def heartbeat():
        while running:
            send("PING")
            time.sleep(0.2)

    threading.Thread(target=reader, daemon=True).start()
    threading.Thread(target=heartbeat, daemon=True).start()

    print("Connected. Type commands, Ctrl+C or 'quit' to exit.")

    try:
        while True:
            command = input("> ").strip()
            if command.lower() in {"quit", "exit"}:
                break
            if command:
                send(command.upper())
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        running = False
        send("LASER OFF")
        time.sleep(0.1)
        ser.close()


if __name__ == "__main__":
    main()
