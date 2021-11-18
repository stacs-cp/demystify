#!/usr/bin/env bash

set -uxo pipefail

rm -rf outputs
mkdir outputs

./run-cascade.sh
./run-forqes.sh

git status .

git diff --exit-code .
