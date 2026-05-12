#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 noexp|exp|arm-b" >&2
  exit 1
fi

case "$1" in
  noexp)
    src=/tmp/locomo_results_normalized.json
    dst=/tmp/locomo_results_conv26_noexp.json
    ;;
  exp)
    src=/tmp/locomo_results_query_expansion.json
    dst=/tmp/locomo_results_conv26_exp.json
    ;;
  arm-b)
    src=/tmp/locomo_results_no_expansion.json
    dst=/tmp/locomo_results_conv26_no_expansion.json
    ;;
  *) echo "usage: $0 noexp|exp|arm-b" >&2; exit 1 ;;
esac

if [[ ! -f "$src" ]]; then
  echo "missing $src" >&2
  exit 1
fi

mv "$src" "$dst"
echo "archived $src -> $dst"
