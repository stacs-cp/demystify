#!/usr/bin/env bash

set -uxo pipefail

time (
(while read instance; do
    echo ./go-json.sh $instance
done < tests-cascade.txt) | parallel
)

echo "CASCADE TIME TAKEN"
