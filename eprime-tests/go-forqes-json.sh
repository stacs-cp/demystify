#!/usr/bin/env bash
set -euo pipefail

filename=outputs/$(basename $1)-$(basename $2)

python3 ../demystify --cores 1 --eprime ../eprime/$1 --eprimeparam ../eprime/$2 --forqes --json ${filename}-forqes.first-out > ${filename}-forqes.json.err 2>&1
python3 -m json.tool ${filename}-forqes.first-out.json > ${filename}-forqes.json
rm ${filename}-forqes.first-out.json