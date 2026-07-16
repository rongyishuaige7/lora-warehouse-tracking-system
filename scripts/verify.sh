#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ANDROID_SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [[ -z "$ANDROID_SDK" ]]; then
  for candidate in "$HOME/Android/Sdk" "$HOME/Android/sdk" /opt/android-sdk /usr/lib/android-sdk; do
    if [[ -d "$candidate" ]]; then ANDROID_SDK="$candidate";break;fi
  done
fi
if [[ -z "$ANDROID_SDK" || ! -d "$ANDROID_SDK" ]]; then
  echo "Android SDK not found; set ANDROID_HOME or ANDROID_SDK_ROOT" >&2;exit 1
fi
export ANDROID_HOME="$ANDROID_SDK" ANDROID_SDK_ROOT="$ANDROID_SDK"
python3 "$ROOT/scripts/secret_scan.py" --root "$ROOT"
python3 "$ROOT/scripts/check_repo.py" --root "$ROOT"
WORK="$(mktemp -d)";PYCACHE="$(mktemp -d)";trap 'rm -rf -- "$WORK" "$PYCACHE"' EXIT
export PYTHONPYCACHEPREFIX="$PYCACHE"
mkdir -p "$WORK/repo"
tar -C "$ROOT" --exclude=.git --exclude=.pio --exclude=.gradle --exclude=build --exclude=.pytest_cache --exclude=__pycache__ --exclude=.venv --exclude=venv -cf - . | tar -C "$WORK/repo" -xf -
cp "$WORK/repo/esp32_tag/config.example.h" "$WORK/repo/esp32_tag/config.h"
cp "$WORK/repo/esp32_gateway/config.example.h" "$WORK/repo/esp32_gateway/config.h"
pio run -d "$WORK/repo" -e tag
pio run -d "$WORK/repo" -e gateway
python3 -m py_compile "$WORK/repo/server/"*.py "$WORK/repo/server/tests/"*.py
(cd "$WORK/repo/server" && python3 -m pytest tests -q)
(cd "$WORK/repo/android_app" && ./gradlew --no-daemon testDebugUnitTest assembleDebug)
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  [[ -z "$(git -C "$ROOT" status --short --untracked-files=no)" ]] || { echo "Tracked files changed during verification" >&2;git -C "$ROOT" status --short;exit 1; }
fi
echo "Verification: PASS"
