#!/usr/bin/env bash

set -euxo pipefail

(while read instance; do
    echo ./go.sh $instance
done < tests.txt) | parallel

(while read instance; do
    echo ./go-json.sh $instance
done < tests.txt) | parallel
