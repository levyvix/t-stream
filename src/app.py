#! /usr/bin/python
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from piratebay import pirate
from spinner import Spinner, add_cursor

SUPPORTED_PLAYERS = ["mpv", "vlc"]
SUPPORTED_CLIENTS = ["webtorrent", "peerflix"]
DEFAULT_CONFIG = ("webtorrent", "mpv")


def config_path():
    return Path(__file__).resolve().parent.parent / "config.json"


def write_table(movie_list):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", width=12)
    table.add_column("Title")
    table.add_column("Size", justify="right")
    table.add_column("Seeders", justify="right")
    table.add_column("Leeches", justify="right")

    for i, obj in enumerate(movie_list):
        table.add_row(
            str(i + 1),
            obj["title"],
            str(obj["size"]),
            str(obj["seeders"]),
            str(obj["leeches"]),
        )

    console.print(table)


def greet_bye():
    print("\nsee ya 👋")


def parse_config():
    path = config_path()
    if not path.is_file():
        return DEFAULT_CONFIG

    try:
        with open(path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        print("Invalid config file. Please check the file and try again. Using default config.")
        return DEFAULT_CONFIG

    cfg = config.get("config", {})
    player, client = cfg.get("player"), cfg.get("client")
    if player in SUPPORTED_PLAYERS and client in SUPPORTED_CLIENTS:
        return (client, player)
    return DEFAULT_CONFIG


def available_options(options):
    return [option for option in options if shutil.which(str(option))]


def save_config(client, player):
    payload = {"config": {"player": player, "client": client}}
    config_path().write_text(json.dumps(payload, indent=4) + "\n")


def stream_out_base_dir():
    configured = os.environ.get("T_STREAM_OUT_DIR")
    if configured:
        out_dir = Path(configured).expanduser()
    else:
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        cache_root = Path(xdg_cache_home).expanduser() if xdg_cache_home else Path.home() / ".cache"
        out_dir = cache_root / "t-stream" / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir)


def available_tools():
    clients = available_options(SUPPORTED_CLIENTS)
    players = available_options(SUPPORTED_PLAYERS)
    if not clients:
        print("No supported torrent clients found. Install one of: webtorrent, peerflix")
        return None
    if not players:
        print("No supported players found. Install one of: mpv, vlc")
        return None
    return clients, players


def run_config_ui():
    tools = available_tools()
    if not tools:
        return 1
    available_clients, available_players = tools

    current_client, current_player = parse_config()
    default_client = current_client if current_client in available_clients else available_clients[0]
    default_player = current_player if current_player in available_players else available_players[0]

    print("\nConfig mode\n")
    selected_client = Prompt.ask(
        "Select torrent client", choices=available_clients, default=default_client
    )
    selected_player = Prompt.ask(
        "Select media player", choices=available_players, default=default_player
    )

    save_config(selected_client, selected_player)
    print(f"Saved config: client={selected_client}, player={selected_player}")
    return 0


def config_usage():
    print("Usage:")
    print("  t-stream config")
    print("  t-stream config --non-interactive [--client CLIENT] [--player PLAYER]")


def parse_config_args(args):
    non_interactive = False
    client = None
    player = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--help", "-h"):
            return {"help": True}
        if arg in ("--non-interactive", "-n"):
            non_interactive = True
            i += 1
            continue
        if arg == "--client":
            if i + 1 >= len(args):
                print("Missing value for --client")
                return None
            client = args[i + 1]
            i += 2
            continue
        if arg == "--player":
            if i + 1 >= len(args):
                print("Missing value for --player")
                return None
            player = args[i + 1]
            i += 2
            continue
        print(f"Unknown option: {arg}")
        return None

    return {
        "help": False,
        "non_interactive": non_interactive,
        "client": client,
        "player": player,
    }


def run_config_non_interactive(selected_client=None, selected_player=None):
    tools = available_tools()
    if not tools:
        return 1
    available_clients, available_players = tools

    current_client, current_player = parse_config()

    if selected_client and selected_client not in SUPPORTED_CLIENTS:
        print(f"Unsupported client: {selected_client}. Supported: {', '.join(SUPPORTED_CLIENTS)}")
        return 1
    if selected_player and selected_player not in SUPPORTED_PLAYERS:
        print(f"Unsupported player: {selected_player}. Supported: {', '.join(SUPPORTED_PLAYERS)}")
        return 1

    client = selected_client or current_client
    player = selected_player or current_player

    if client not in available_clients:
        available_clients_text = ", ".join(available_clients)
        print(
            f"Client '{client}' not found in PATH. "
            f"Available on this machine: {available_clients_text}"
        )
        return 1
    if player not in available_players:
        available_players_text = ", ".join(available_players)
        print(
            f"Player '{player}' not found in PATH. "
            f"Available on this machine: {available_players_text}"
        )
        return 1

    save_config(client, player)
    print(f"Saved config: client={client}, player={player}")
    return 0


def handle_config_command(args):
    parsed = parse_config_args(args)
    if parsed is None:
        config_usage()
        return 1

    if parsed["help"]:
        config_usage()
        return 0

    if parsed["non_interactive"]:
        return run_config_non_interactive(parsed["client"], parsed["player"])

    if parsed["client"] or parsed["player"]:
        print("--client/--player require --non-interactive")
        config_usage()
        return 1

    return run_config_ui()


def stream(mag_url):
    client, player = parse_config()
    cmd = [client, mag_url, f"--{player}"]
    session_out_dir = None
    if client == "webtorrent":
        base_dir = stream_out_base_dir()
        session_out_dir = tempfile.mkdtemp(prefix="session-", dir=base_dir)
        cmd.extend(["--out", session_out_dir])

    try:
        subprocess.run(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return 1
    finally:
        if session_out_dir:
            shutil.rmtree(session_out_dir, ignore_errors=True)


console = Console()


def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() == "config":
        try:
            return handle_config_command(sys.argv[2:])
        except KeyboardInterrupt:
            add_cursor()
            greet_bye()
            return 1

    try:
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
        else:
            query = Prompt.ask("What you want to watch today ?")

        print("  Finding torrents", end="\r")

        with Spinner():
            movie_list = pirate(None if query == "1" else query)["movie_info"]

        if not movie_list:
            greet_bye()
            return 1

        write_table(movie_list)

        movie_ind = Prompt.ask("Select your fav", default="1")
        if not movie_ind.isdigit():
            print("Invalid input. Please enter a number.")
            greet_bye()
            return 1

        selected = int(movie_ind)
        if selected > len(movie_list) or selected < 1:
            print("Invalid input. Please enter a number within the range of the list.")
            greet_bye()
            return 1

        mag_url = movie_list[selected - 1]["magnet_url"]

    except KeyboardInterrupt:
        add_cursor()
        greet_bye()
        return 1

    print("Enjoy! Less seeds may take more time\nStreaming will start after 1% of downloading")
    stream(mag_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
