import threading
import time

try:
    from pynput import keyboard, mouse
except ImportError:
    print("Missing dependency: pynput")
    print("Install it with: python -m pip install pynput")
    raise SystemExit(1)


CLICK_INTERVAL_SECONDS = 5

clicking = threading.Event()
shutdown = threading.Event()
mouse_controller = mouse.Controller()
pressed_keys = set()


def _is_ctrl_pressed() -> bool:
    return (
        keyboard.Key.ctrl in pressed_keys
        or keyboard.Key.ctrl_l in pressed_keys
        or keyboard.Key.ctrl_r in pressed_keys
    )


def _click_loop() -> None:
    while not shutdown.is_set():
        if clicking.is_set():
            mouse_controller.click(mouse.Button.left)
            time.sleep(CLICK_INTERVAL_SECONDS)
        else:
            time.sleep(0.05)


def _start_clicking() -> None:
    if not clicking.is_set():
        clicking.set()
        print(f"Autoclicking started: left click every {CLICK_INTERVAL_SECONDS} seconds.")


def _stop_clicking() -> None:
    if clicking.is_set():
        clicking.clear()
        print("Autoclicking stopped.")


def _on_press(key) -> None:
    pressed_keys.add(key)

    if not _is_ctrl_pressed():
        return

    if key == keyboard.Key.enter:
        _start_clicking()
    elif key == keyboard.Key.backspace:
        _stop_clicking()


def _on_release(key) -> None:
    pressed_keys.discard(key)


def main() -> int:
    worker = threading.Thread(target=_click_loop, daemon=True)
    worker.start()

    print("Ready.")
    print("Press Ctrl+Enter to start left-clicking every 5 seconds.")
    print("Press Ctrl+Backspace to stop.")
    print("Press Ctrl+C in this terminal to quit.")

    try:
        with keyboard.Listener(on_press=_on_press, on_release=_on_release) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\nQuitting.")
    finally:
        shutdown.set()
        clicking.clear()
        worker.join(timeout=1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
