import argparse
import ctypes.util
import logging
import os
import sys
from pathlib import Path

from photo_organizer.cli.prompts import confirm_move
from photo_organizer.config.settings import Settings
from photo_organizer.core.organizer import Organizer
from photo_organizer.models.result import ProcessResult

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="photo-organizer", description="Organize photos into date-based folders")
    parser.add_argument("--config", type=Path, default=Path(".env"), help="Settings file (default: .env)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create or update settings interactively")
    commands.add_parser("status", help="Show current settings")
    commands.add_parser("gui", help="Launch the graphical interface")
    run = commands.add_parser("run", help="Run using the configured default mode")
    copy = commands.add_parser("copy", help="Copy photos")
    move = commands.add_parser("move", help="Move photos after confirmation")
    for command in (run, copy, move):
        command.add_argument("--source", type=Path, help="Override source directory")
        command.add_argument("--destination", type=Path, help="Override destination directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = Settings.load(args.config)
        if args.command == "init":
            return _init(settings)
        if args.command == "status":
            _show_settings(settings)
            return 0
        if args.command == "gui":
            _check_gui_dependencies()
            from photo_organizer.gui.main_window import launch

            return launch(settings)
        mode = settings.default_mode if args.command == "run" else args.command
        source = args.source or settings.source_path
        destination = args.destination or settings.destination_path
        if not source or not destination:
            raise ValueError("Set SOURCE_PATH and DESTINATION_PATH with 'photo-organizer init'")
        if mode == "move" and settings.move_warning and not confirm_move():
            print("Operation cancelled.")
            return 0
        result = Organizer(settings).run(source, destination, mode)
        _print_result(result)
        return 1 if result.errors else 0
    except (OSError, ValueError) as error:
        logger.error("%s", error)
        return 2


def _init(settings: Settings) -> int:
    source = input(f"Source path [{settings.source_path or ''}]: ").strip()
    destination = input(f"Destination path [{settings.destination_path or ''}]: ").strip()
    mode = input(f"Default mode (copy/move) [{settings.default_mode}]: ").strip().lower()
    settings.source_path = Path(source).expanduser() if source else settings.source_path
    settings.destination_path = Path(destination).expanduser() if destination else settings.destination_path
    if mode:
        settings.default_mode = mode
    settings.__post_init__()
    settings.save()
    print(f"Settings saved to {settings.env_path}")
    return 0


def _check_gui_dependencies() -> None:
    if (
        sys.platform.startswith("linux")
        and os.environ.get("QT_QPA_PLATFORM", "xcb") == "xcb"
        and ctypes.util.find_library("xcb-cursor") is None
    ):
        raise ValueError("GUI requires libxcb-cursor0. On Ubuntu, install it with: sudo apt-get install libxcb-cursor0")


def _show_settings(settings: Settings) -> None:
    print(f"Source: {settings.source_path or '(not set)'}")
    print(f"Destination: {settings.destination_path or '(not set)'}")
    print(f"Default mode: {settings.default_mode}")
    print(f"Move warning: {settings.move_warning}")
    print(f"Create date folders: {settings.create_date_folder}")
    print(f"Supported extensions: {', '.join(settings.supported_extensions)}")


def _print_result(result: ProcessResult) -> None:
    print("Photo Organizer Result")
    print(f"Processed : {result.processed}")
    print(f"Copied    : {result.copied}")
    print(f"Moved     : {result.moved}")
    print(f"Skipped   : {result.skipped}")
    print(f"Error     : {result.errors}")
    for message in result.error_messages:
        print(f"  {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
