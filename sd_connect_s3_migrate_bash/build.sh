#!/usr/bin/env bash
set -euo pipefail

# Shamelessly done with Copilot due to laziness, altered where relevant

# ========= Config =========
APP_NAME="${APP_NAME:-sd-connect-migrate-project}"
SRC_SCRIPT="${SRC_SCRIPT:-migrate_project_bash_src/migrate_project.sh}"
OUT_NAME="${OUT_NAME:-${APP_NAME}}"

# Python major.minor to target
PYTHON_MAJMIN="${PYTHON_MAJMIN:-3.12}"

# Note: not 100 % sure how necessary the ARM support is, leaving it in place for now.
# ========= Detect architecture =========
UNAME_M="$(uname -m)"
case "$UNAME_M" in
  x86_64|amd64)
    ARCH="x86_64"
    NODE_ARCH="x64"
    JQ_ASSET="jq-linux-amd64"
    RCLONE_ARCH="amd64"
    PY_ARCH="x86_64"
    ;;
  aarch64|arm64)
    ARCH="aarch64"
    NODE_ARCH="arm64"
    JQ_ASSET="jq-linux-arm64"
    RCLONE_ARCH="arm64"
    PY_ARCH="aarch64"
    ;;
  *)
    echo "Unsupported architecture: $UNAME_M" >&2
    exit 1
    ;;
esac

# ========= Paths =========
ROOT="$(pwd)"
APPDIR="$ROOT/AppDir"
USR="$APPDIR/usr"
BIN="$USR/bin"
NODE_DIR="$USR/node"
NODEPKGS_DIR="$USR/nodepkgs"
PY_DIR="$USR/python"

mkdir -p "$BIN" "$NODE_DIR" "$NODEPKGS_DIR" "$PY_DIR" \
         "$APPDIR/icons/hicolor/128x128/apps"

# ========= Helper: require curl, tar, unzip =========
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1" >&2; exit 1; }; }
need curl
need tar
# unzip is needed for rclone .zip (some distros package rclone as .zip)
if ! command -v unzip >/dev/null 2>&1; then
  echo "Note: 'unzip' not found; attempting to use 'bsdtar' if available."
  command -v bsdtar >/dev/null 2>&1 || { echo "Install unzip or bsdtar" >&2; exit 1; }
  UNZIP="bsdtar -xf"
else
  UNZIP="unzip -q"
fi

# ========= Fetch Node.js 22.x =========
fetch_node() {
  echo "==> Fetching Node.js 22.x for $NODE_ARCH ..."
  local BASE="https://nodejs.org/dist/latest-v22.x"
  # Find the exact tarball name via SHASUMS list (portable, no need to hardcode version)
  local FILENAME
  FILENAME="$(curl -fsSL "$BASE/SHASUMS256.txt" | awk "/linux-${NODE_ARCH}\\.tar\\.xz/ {print \$2}" | sed 's/\*//')"
  [ -n "$FILENAME" ] || { echo "Could not resolve Node 22 tarball" >&2; exit 1; }
  curl -fsSL "$BASE/$FILENAME" | tar -xJ --strip-components=1 -C "$NODE_DIR"
  echo "Node: $("$NODE_DIR/bin/node" -v), npm: $("$NODE_DIR/bin/npm" -v)"
}

# ========= Fetch standalone Python via python-build-standalone =========
fetch_python() {
  echo "==> Fetching standalone Python $PYTHON_MAJMIN via GitHub API ..."

  API_URL="https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"

  # Fetch JSON metadata
  RELEASE_JSON="$(curl -fsSL "$API_URL")"

  # Construct regex for the asset filename
  # Matches: cpython-3.12.13+20260310-x86_64-unknown-linux-gnu-pgo+lto-full.tar.zst
  ASSET_REGEX="cpython-${PYTHON_MAJMIN}\.[0-9]+(\+[0-9]+)?-${PY_ARCH}-unknown-linux-gnu-pgo\\+lto-full\\.tar\\.zst"

  # Extract asset download URL
  ASSET_URL="$(echo "$RELEASE_JSON" \
      | jq -r --arg re "$ASSET_REGEX" \
          '.assets[] | select(.name | test($re)) | .browser_download_url' | head -n1)"

  if [ -z "$ASSET_URL" ]; then
      echo "ERROR: Could not find Python build matching: $ASSET_REGEX" >&2
      exit 1
  fi

  echo "Downloading Python from:"
  echo "  $ASSET_URL"

  curl -fsSL "$ASSET_URL" -o python.tar.zst
  tar --zstd -xf python.tar.zst -C "$PY_DIR" --strip-components=1
  rm python.tar.zst

  mkdir -p "$PY_DIR/bin"
  ln -frs "$PY_DIR/install/bin/python3.12" "$PY_DIR/bin/python3"
  ln -frs "$PY_DIR/install/bin/python3.12" "$PY_DIR/bin/python"
  ln -frs "$PY_DIR/install/bin/pip3" "$PY_DIR/bin/pip3"
  ln -frs "$PY_DIR/install/bin/pip" "$PY_DIR/bin/pip"

  echo "Python installed:"
  "$PY_DIR/bin/python3" -V
}

# ========= Create venv and install Python deps =========
install_python_deps() {
  echo "==> Installing Python dependencies ..."
  # upgrade pip/setuptools/wheel inside site packages
  "$PY_DIR/bin/pip" install --no-cache-dir --upgrade pip setuptools wheel

  # install dependencies
  "$PY_DIR/bin/pip" install --no-cache-dir --upgrade \
      "git+https://github.com/CSCfi/sd-lock-util.git" \
      "python-openstackclient" \
      "gnureadline"

  # Override incorrectly resolved pip shebangs in executables
  sed -i "1s/.*/#!\/bin\/env python/" "$PY_DIR/install/bin/sd-lock-util"
  sed -i "1s/.*/#!\/bin\/env python/" "$PY_DIR/install/bin/openstack"
}

# ========= Install npm transliteration =========
install_npm_deps() {
  echo "==> Installing npm 'transliteration' ..."
  # Install into a dedicated prefix; binaries will appear in node_modules/.bin
  "$NODE_DIR/bin/npm" install --no-audit --no-fund --loglevel=error \
      --prefix "$NODEPKGS_DIR" transliteration@latest
  # Sanity check
  if [ ! -x "$NODEPKGS_DIR/node_modules/.bin/slugify" ] && \
     [ ! -x "$NODEPKGS_DIR/node_modules/.bin/transliterate" ]; then
    echo "Warning: could not find transliteration CLI in node_modules/.bin (will still set PATH)" >&2
  fi

  # Clean up the node-breaking duplicate shebang by yanking first line
  if [[ $(grep "#!/usr/bin/env node" < $NODEPKGS_DIR/node_modules/.bin/slugify | wc -l) -gt 1 ]]; then
    echo "==> Yanking first line in slugify to prevent crashing node with bash shebang..."
    sed -i 1d "$NODEPKGS_DIR/node_modules/.bin/slugify"
  fi
  if [[ $(grep "#!/usr/bin/env node" < $NODEPKGS_DIR/node_modules/.bin/transliterate | wc -l) -gt 1 ]]; then
    echo "==> Yanking first line in transliterate to prevent crashing node with bash shebang..."
    sed -i 1d "$NODEPKGS_DIR/node_modules/.bin/transliterate"
  fi
}

# ========= Fetch jq (static) =========
fetch_jq() {
  echo "==> Fetching jq ..."
  local URL="https://github.com/jqlang/jq/releases/latest/download/${JQ_ASSET}"
  curl -fsSL "$URL" -o "$BIN/jq"
  chmod +x "$BIN/jq"
  echo "jq: $("$BIN/jq" --version)"
}

# ========= Fetch rclone =========
fetch_rclone() {
  echo "==> Fetching rclone ..."
  local URL="https://downloads.rclone.org/rclone-current-linux-${RCLONE_ARCH}.zip"
  rm -rf .rclone-tmp && mkdir -p .rclone-tmp
  curl -fsSL "$URL" -o .rclone-tmp/rclone.zip
  (cd .rclone-tmp && $UNZIP rclone.zip >/dev/null)
  # the zip contains a directory like rclone-*-linux-amd64/rclone
  local RCLONE_BIN
  RCLONE_BIN="$(find .rclone-tmp -type f -name rclone -perm -u+x | head -n1)"
  [ -n "$RCLONE_BIN" ] || { echo "Could not locate rclone binary in archive" >&2; exit 1; }
  cp "$RCLONE_BIN" "$BIN/rclone"
  chmod +x "$BIN/rclone"
  rm -rf .rclone-tmp
  echo "rclone: $("$BIN/rclone" version | head -n1)"
}

# ========= Copy your script as the entrypoint =========
install_entry_script() {
  echo "==> Installing entry script as $APP_NAME ..."
  [ -f "$SRC_SCRIPT" ] || { echo "Missing source script: $SRC_SCRIPT" >&2; exit 1; }
  install -m 0755 "$SRC_SCRIPT" "$BIN/$APP_NAME"
}

# ========= Optional icon placeholder =========
ensure_icon() {
  if [ ! -f "$APPDIR/icons/hicolor/128x128/apps/${APP_NAME}.png" ]; then
    # Create a minimal 128x128 placeholder icon using ASCII (requires no external tools)
    # This produces a tiny valid PNG (base64-encoded) — purely optional.
    cat > "$APPDIR/icons/hicolor/128x128/apps/${APP_NAME}.png" <<'EOF'
\x89PNG\r\n\x1a
EOF
    : # TODO: replace with a real PNG later
  fi
  # Update .desktop Icon= value expects a basename (no extension)
  sed -i "s|^Icon=.*|Icon=${APP_NAME}|g" "$APPDIR/${APP_NAME}.desktop" 2>/dev/null || true
}

# ========= Make desktop file and AppRun consistent =========
finalize_metadata() {
  # Rename desktop file to match APP_NAME if needed
  if [ "$(basename "$APPDIR"/*.desktop)" != "${APP_NAME}.desktop" ]; then
    mv "$APPDIR/"*.desktop "$APPDIR/${APP_NAME}.desktop"
  fi
  # Update Exec and Name fields
  sed -i "s|^Exec=.*|Exec=${APP_NAME} %F|g" "$APPDIR/${APP_NAME}.desktop"
  sed -i "s|^Name=.*|Name=${APP_NAME}|g" "$APPDIR/${APP_NAME}.desktop"

  # Ensure AppRun points to correct entrypoint name
  sed -i "s|^ENTRYPOINT=.*|ENTRYPOINT=\"${APP_NAME}\"|g" "$APPDIR/AppRun"
  chmod +x "$APPDIR/AppRun"
}

# ========= Fetch appimagetool & build =========
package_appimage() {
  echo "==> Fetching appimagetool (continuous) via GitHub API ..."

  API_URL="https://api.github.com/repos/AppImage/appimagetool/releases/tags/continuous"

  RELEASE_JSON="$(curl -fsSL "$API_URL")"

  case "$ARCH" in
    x86_64)   APPIMAGE_ARCH="x86_64" ;;
    aarch64)  APPIMAGE_ARCH="aarch64" ;;
    armhf)    APPIMAGE_ARCH="armhf" ;; # Just in case
    *)
      echo "Unsupported architecture for appimagetool: $ARCH" >&2
      exit 1
      ;;
  esac

  # Filename pattern e.g. appimagetool-x86_64.AppImage
  FILE_RE="appimagetool-${APPIMAGE_ARCH}\\.AppImage"

  ASSET_URL="$(
    echo "$RELEASE_JSON" \
      | jq -r --arg re "$FILE_RE" \
        '.assets[] | select(.name | test($re)) | .browser_download_url' \
      | head -n1
  )"

  if [ -z "$ASSET_URL" ] || [ "$ASSET_URL" = "null" ]; then
    echo "ERROR: Could not find appimagetool asset matching ${FILE_RE}" >&2
    exit 1
  fi

  echo "Downloading appimagetool from:"
  echo "  $ASSET_URL"

  curl -fsSL "$ASSET_URL" -o appimagetool
  chmod +x appimagetool

  echo "appimagetool fetched successfully."

  echo "==> Building AppImage..."

  # AppImage naming convention: <name>-<arch>.AppImage
  local OUT="${OUT_NAME}-${ARCH}.AppImage"

  # Some environments lack FUSE; use extract-and-run
  export APPIMAGE_EXTRACT_AND_RUN=1
  ./appimagetool "$APPDIR" "$OUT"

  echo "==> AppImage created: $OUT"
  echo "Run it via: ./${OUT} --help"
}

main() {
  fetch_node
  fetch_python
  install_python_deps
  install_npm_deps
  fetch_jq
  fetch_rclone
  install_entry_script
  ensure_icon
  finalize_metadata
  package_appimage
}

main "$@"
