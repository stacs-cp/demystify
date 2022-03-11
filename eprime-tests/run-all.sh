#!/usr/bin/env bash

set -uxo pipefail

rm -rf outputs-cascade outputs-cascade-pickle outputs-forqes
mkdir  outputs-cascade outputs-cascade-pickle outputs-forqes

./run-cascade.sh
./run-forqes.sh
./run-cascade-pickle.sh
git status .

git diff --exit-code .
