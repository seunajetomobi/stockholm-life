#!/usr/bin/env bash
# Serve the game locally (browsers block loading the data files straight from disk)
# and open it in the system browser. VS Code's built-in browser tab has no WebGL on some
# setups (e.g. the Snap build of VS Code), so the 3D city would not be drawn there.
cd "$(dirname "$0")"
URL=http://localhost:8000

open_browser() {
  # Drop the library paths a Snap-packaged VS Code terminal leaks, so the browser
  # starts with the system's own graphics drivers.
  env -u GTK_PATH -u GTK_EXE_PREFIX -u GTK_IM_MODULE_FILE -u GDK_PIXBUF_MODULE_FILE \
      -u GDK_PIXBUF_MODULEDIR -u GIO_MODULE_DIR -u GSETTINGS_SCHEMA_DIR -u LOCPATH \
      -u GTK_MODULES -u GIO_LAUNCHED_DESKTOP_FILE -u GIO_LAUNCHED_DESKTOP_FILE_PID \
      ${XDG_DATA_DIRS_VSCODE_SNAP_ORIG:+XDG_DATA_DIRS="$XDG_DATA_DIRS_VSCODE_SNAP_ORIG"} \
      xdg-open "$URL" >/dev/null 2>&1 &
}

if [ "$TERM_PROGRAM" = vscode ] && [ -z "$SNAP" ]; then
  # A non-Snap VS Code has WebGL: play in its own browser tab.
  OPEN=:
  MSG="In VS Code: Ctrl+Shift+P > \"Simple Browser: Show\" > $URL"
else
  OPEN=open_browser
  MSG="Opening $URL in your browser."
  [ -n "$SNAP" ] && MSG="$MSG (This Snap VS Code has no WebGL; to play inside VS Code, start it with code-gpu.)"
fi

if curl -s -o /dev/null "$URL" 2>/dev/null; then
  echo "Stockholm Life is already being served at $URL. $MSG"
  $OPEN
  exit 0
fi

echo "Stockholm Life: $MSG (Ctrl+C to stop the server)"
(sleep 1; $OPEN) &
python3 -m http.server 8000
