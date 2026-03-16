#!/usr/bin/env bash
# Run mpas-analysis for the ocean BGC test case.
# Activates the mpas-py311 conda environment and injects $HOME/pyhooks via
# PYTHONPATH so that sitecustomize.py can intercept xarray's time decoding and
# prevent crashes on 'months since ...' time units in MPAS files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Conda activation hooks may reference this variable with nounset enabled.
export GEOMETRIC_DATA_DIR="${GEOMETRIC_DATA_DIR:-}"

# ── Activate conda environment ───────────────────────────────────────────────
# shellcheck source=/dev/null
source "/Applications/anaconda3/etc/profile.d/conda.sh"
conda activate mpas-py311

# ── Python hook for 'months since' fix ──────────────────────────────────────
export PYTHONPATH="$HOME/pyhooks:${PYTHONPATH:-}"

# ── Run mpas-analysis ────────────────────────────────────────────────────────
mpas_analysis "${SCRIPT_DIR}/ocean_bgc_test.cfg" "$@"
