#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
hook_path="$repo_root/.git/hooks/pre-commit"
audit_script="$repo_root/scripts/public-safety-audit.sh"

if [ ! -f "$audit_script" ]; then
  printf 'install-public-safety-hook: missing %s\n' "$audit_script" >&2
  exit 1
fi

printf '%s\n' \
'#!/usr/bin/env bash' \
'set -euo pipefail' \
"exec \"$audit_script\" --staged" \
> "$hook_path"

chmod +x "$hook_path"
printf 'Installed pre-commit hook at %s\n' "$hook_path"
