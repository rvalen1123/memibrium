#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 noexp|exp" >&2
  exit 1
fi

src=/tmp/locomo_results_normalized.json
case "$1" in
  noexp) dst=/tmp/locomo_results_conv26_noexp.json ;;
  exp) dst=/tmp/locomo_results_conv26_exp.json ;;
  *) echo "usage: $0 noexp|exp" >&2; exit 1 ;;
esac

if [[ ! -f "$src" ]]; then
  echo "missing $src" >&2
  exit 1
fi

mv "$src" "$dst"
echo "archived $src -> $dst"
