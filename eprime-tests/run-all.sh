#!/usr/bin/env bash

set -uxo pipefail

rm outputs/*

time (
(while read instance; do
    echo ./go-json.sh $instance
done < tests.txt) | parallel
)

echo "CASCADE TIME TAKEN"

time (
(while read instance; do
    echo ./go-forqes-json.sh $instance
done < tests.txt) | parallel
)

echo "FORQES TIME TAKEN"

git status .

git diff --exit-code .
