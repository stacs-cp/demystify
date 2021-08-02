#!/usr/bin/env bash

set -uxo pipefail

time (
(while read instance; do
    echo ./go-forqes-json.sh $instance
done < tests-forqes.txt) | parallel
)

echo "FORQES TIME TAKEN"