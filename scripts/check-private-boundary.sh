#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
#
# Verifies that the local only themes stay out of the public source tree and
# out of the public packages.
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$project_root/scripts/check_private_boundary.py"
