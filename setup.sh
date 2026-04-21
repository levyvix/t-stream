#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="levyvix"
REPO_NAME="t-stream"
REPO_BRANCH="main"
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
INSTALL_ROOT="${HOME}/.local/share/${REPO_NAME}"
VENV_DIR="${INSTALL_ROOT}/.venv"
BIN_DIR="${HOME}/.local/bin"
BIN_PATH="${BIN_DIR}/t-stream"

info() {
  printf '[t-stream] %s\n' "$1"
}

err() {
  printf '[t-stream] ERROR: %s\n' "$1" >&2
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Missing required command: $1"
    exit 1
  fi
}

append_path_hint() {
  local rc_file="$1"
  local line='export PATH="$HOME/.local/bin:$PATH"'

  if [ ! -f "$rc_file" ]; then
    return
  fi

  if ! grep -Fq "$line" "$rc_file"; then
    printf '\n# t-stream\n%s\n' "$line" >> "$rc_file"
    info "Added ~/.local/bin to PATH in ${rc_file}"
  fi
}

install_node_tools() {
  need_cmd npm

  info "Installing Node.js dependencies (peerflix, webtorrent-cli)"
  if npm install -g peerflix webtorrent-cli >/dev/null 2>&1; then
    return
  fi

  info "No writable npm global prefix detected, switching npm prefix to ~/.local"
  npm config set prefix "$HOME/.local"

  if npm install -g peerflix webtorrent-cli >/dev/null 2>&1; then
    return
  fi

  err "npm install still failed. Check your npm setup and try again."
  exit 1
}

install_python_deps() {
  need_cmd python3

  info "Creating virtual environment"
  python3 -m venv "$VENV_DIR"

  info "Installing Python dependencies"
  "$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
  "$VENV_DIR/bin/pip" install -r "$INSTALL_ROOT/requirements.txt" >/dev/null
}

install_repo() {
  need_cmd git

  mkdir -p "$(dirname "$INSTALL_ROOT")"

  if [ -d "$INSTALL_ROOT/.git" ]; then
    info "Updating existing installation"
    git -C "$INSTALL_ROOT" fetch origin "$REPO_BRANCH" --depth 1
    git -C "$INSTALL_ROOT" checkout -q "$REPO_BRANCH"
    git -C "$INSTALL_ROOT" reset -q --hard "origin/$REPO_BRANCH"
  else
    info "Cloning repository"
    rm -rf "$INSTALL_ROOT"
    git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_ROOT"
  fi
}

install_launcher() {
  mkdir -p "$BIN_DIR"

  cat > "$BIN_PATH" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail
exec "$VENV_DIR/bin/python" "$INSTALL_ROOT/src/app.py" "\$@"
LAUNCHER

  chmod +x "$BIN_PATH"
  info "Installed launcher at $BIN_PATH"
}

main() {
  need_cmd bash
  install_repo
  install_node_tools
  install_python_deps
  install_launcher

  append_path_hint "$HOME/.bashrc"
  append_path_hint "$HOME/.zshrc"

  info "Installation complete"
  info "Run: t-stream"
  info "If command is not found, open a new shell or run: export PATH=\"$HOME/.local/bin:\$PATH\""
}

main "$@"
