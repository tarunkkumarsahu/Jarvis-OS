import argparse

from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="JARVIS OS")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the terminal interface instead of the desktop app.",
    )
    startup = parser.add_mutually_exclusive_group()
    startup.add_argument("--enable-autostart", action="store_true", help="Opt in to launching JARVIS when you sign in to Windows.")
    startup.add_argument("--disable-autostart", action="store_true", help="Remove this installation\'s Windows sign-in entry.")
    startup.add_argument("--autostart-status", action="store_true", help="Show whether Windows sign-in startup is enabled.")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.enable_autostart or args.disable_autostart or args.autostart_status:
        from pathlib import Path
        from interface.windows_startup import (
            disable_autostart, enable_autostart, startup_status,
        )

        root = Path(__file__).resolve().parent
        try:
            if args.enable_autostart:
                message = enable_autostart(root)
            elif args.disable_autostart:
                message = disable_autostart(root)
            else:
                message = startup_status(root)
        except (OSError, RuntimeError) as error:
            print(f"JARVIS startup: {error}")
            return 1
        print(message)
        return 0

    if args.cli:
        from core.jarvis import Jarvis

        Jarvis().start()
        return

    from interface.operating_app import run_app

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
