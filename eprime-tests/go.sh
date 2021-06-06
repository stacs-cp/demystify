#!/usr/bin/env bash
set -euo pipefail

filename=outputs/$(basename $1)-$(basename $2)
python3 ../demystify --cores 1 --eprime ../eprime/$1 --eprimeparam ../eprime/$2 > ${filename}.out  2> ${filename}.err
