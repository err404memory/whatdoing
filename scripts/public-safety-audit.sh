#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/public-safety-audit.sh [--all|--staged]

Scans repo files for common private-path, machine-name, and secret-key leaks.

Modes:
  --all     Scan tracked and untracked non-ignored files (default)
  --staged  Scan only staged files, suitable for a pre-commit hook
EOF
}

mode="all"
case "${1:-}" in
  ""|--all) ;;
  --staged) mode="staged" ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    printf 'public-safety-audit: unknown argument: %s\n' "$1" >&2
    usage >&2
    exit 2
    ;;
esac

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if ! command -v rg >/dev/null 2>&1; then
  printf 'public-safety-audit: ripgrep (rg) is required.\n' >&2
  exit 1
fi

allowlist_file="$repo_root/.public-safety-allowlist"
local_patterns_file="$repo_root/.public-safety-local-patterns"

path_allowed() {
  local path="$1"
  local pattern
  [ -f "$allowlist_file" ] || return 1
  while IFS= read -r pattern; do
    [ -n "$pattern" ] || continue
    [[ "$pattern" == \#* ]] && continue
    if [[ "$path" == $pattern ]]; then
      return 0
    fi
  done < "$allowlist_file"
  return 1
}

collect_files() {
  if [ "$mode" = "staged" ]; then
    git diff --cached --name-only --diff-filter=ACMR
  else
    git ls-files -co --exclude-standard
  fi
}

mapfile -t raw_files < <(collect_files)

files=()
for file in "${raw_files[@]}"; do
  [ -f "$file" ] || continue
  [ "$file" = "scripts/public-safety-audit.sh" ] && continue
  path_allowed "$file" && continue
  files+=("$file")
done

if [ "${#files[@]}" -eq 0 ]; then
  printf 'public-safety-audit: no files to scan (%s mode)\n' "$mode"
  exit 0
fi

suspicious_names=()
for file in "${files[@]}"; do
  case "$file" in
    .directory|*.pem|*.p12|*.pfx|*.key|*.secret|*transcript*.txt|*claude*.txt)
      suspicious_names+=("$file")
      ;;
  esac
done

if [ "${#suspicious_names[@]}" -gt 0 ]; then
  printf 'public-safety-audit: suspicious filenames found:\n' >&2
  printf '  %s\n' "${suspicious_names[@]}" >&2
  printf '\nIgnore, rename, or move them before publishing.\n' >&2
  exit 1
fi

patterns=(
  '/home/[A-Za-z0-9._-]+'
  '/Users/[A-Za-z0-9._-]+'
  '(^|[[:space:]"'"'"'`])ssh[[:space:]]+[A-Za-z0-9._-]+@[A-Za-z0-9._-]+'
  '[A-Za-z0-9._-]+@[A-Za-z0-9._-]+:(/|~)'
  'BEGIN OPENSSH PRIVATE KEY'
  'BEGIN RSA PRIVATE KEY'
  'BEGIN EC PRIVATE KEY'
  'github_pat_'
  'ghp_'
)

rg_args=(-nIH --color never)
for pattern in "${patterns[@]}"; do
  rg_args+=(-e "$pattern")
done

if [ -f "$local_patterns_file" ]; then
  while IFS= read -r pattern; do
    [ -n "$pattern" ] || continue
    [[ "$pattern" == \#* ]] && continue
    rg_args+=(-e "$pattern")
  done < "$local_patterns_file"
fi

set +e
matches="$(rg "${rg_args[@]}" -- "${files[@]}")"
status=$?
set -e

if [ "$status" -eq 0 ]; then
  printf '%s\n' "$matches" >&2
  printf '\npublic-safety-audit: suspicious content found.\n' >&2
  printf 'Review the matches above or allowlist intentional cases in %s.\n' "$allowlist_file" >&2
  printf 'For extra machine-name or path checks, add custom local patterns in %s.\n' "$local_patterns_file" >&2
  exit 1
fi

if [ "$status" -gt 1 ]; then
  printf 'public-safety-audit: scan failed.\n' >&2
  exit "$status"
fi

printf 'public-safety-audit: passed (%s mode)\n' "$mode"
