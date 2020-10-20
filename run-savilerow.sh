#!/usr/bin/env bash

set -eux

savilerow -in-eprime $1 -sat -direct-sat-map -sat-family lingeling -in-param $2 -S0 -O0 -reduce-domains -aggregate

python3 demystify --eprime $1 --eprimedimacs $2.dimacs 