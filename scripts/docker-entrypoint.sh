#!/bin/sh
set -eu

if [ -z "${DISPLAY:-}" ]; then
  export DISPLAY=:99
  Xvfb "$DISPLAY" -screen 0 "${XVFB_WHD:-1440x1100x24}" -nolisten tcp >/tmp/xvfb.log 2>&1 &
fi

exec "$@"
