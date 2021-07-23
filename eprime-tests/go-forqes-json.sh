#!/usr/bin/env bash
set -euo pipefail

filename=outputs/$(basename $1)-$(basename $2)-forqes

python3 ../demystify --cores 1 --eprime ../eprime/$1 --eprimeparam ../eprime/$2 --forqes --json ${filename}.first-out.json > ${filename}.json.err 2>&1
python3 -m json.tool ${filename}.first-out.json > ${filename}.json
rm ${filename}.first-out.json