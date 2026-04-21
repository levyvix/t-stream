# t-stream

Stream torrents from your terminal with an interactive search flow.

![Demo](./eg.gif)

## Quick Install (main branch)

```bash
curl -fSsL https://raw.githubusercontent.com/levyvix/t-stream/main/setup.sh | bash
```

After install, restart your shell (or reload rc file), then run:

```bash
t-stream
```

You can also pass a search query directly:

```bash
t-stream "The Matrix"
```

## What The Installer Does

- Clones `levyvix/t-stream` into `~/.local/share/t-stream`
- Installs Node CLI dependencies: `peerflix`, `webtorrent-cli` (no `sudo npm`; falls back to `npm` prefix `~/.local`)
- Installs `uv` (via system `python3` if needed), then creates a Python virtual environment and syncs dependencies from `pyproject.toml`
- Installs a launcher at `~/.local/bin/t-stream`
- Adds `~/.local/bin` to `PATH` in `.bashrc` and `.zshrc` if needed

## Requirements

- `git`
- `bash`
- `python3`
- `npm` (Node.js)
- A player supported by your selected client (`mpv` or `vlc`)

## Configuration

Use the interactive config command:

```bash
t-stream config
```

For scripts/automation, use non-interactive mode:

```bash
t-stream config --non-interactive --client webtorrent --player mpv
```

You can also pass only one value and keep the other from current config:

```bash
t-stream config --non-interactive --player vlc
```

Or edit `config.json` manually:

```json
{
  "config": {
    "player": "mpv",
    "client": "webtorrent"
  }
}
```

Supported values:

- `player`: `mpv`, `vlc`
- `client`: `webtorrent`, `peerflix`

Default fallback is `webtorrent` + `mpv` when config is missing or invalid.

## Update

Re-run the same install command to pull the latest `main` and refresh dependencies.

## Manual Install

```bash
git clone https://github.com/levyvix/t-stream.git
cd t-stream
bash setup.sh
```

## Development Checks

Install and run pre-commit locally:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

The hooks include:

- `ruff lint` (`ruff check --fix`)
- `ruff format` (`ruff format`)
- `pyright`

GitHub Actions runs the same pre-commit hooks on every push and pull request.

## Uninstall

```bash
rm -rf ~/.local/share/t-stream ~/.local/bin/t-stream
```

If you want, remove this PATH line from your shell rc file:

```bash
export PATH="$HOME/.local/bin:$PATH"
```
