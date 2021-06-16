#!/usr/bin/env bash

set -euxo pipefail

rm outputs/*

(while read instance; do
    echo ./go.sh $instance
done < tests.txt) | parallel

(while read instance; do
    echo ./go-json.sh $instance
done < tests.txt) | parallel

(while read instance; do
    echo ./go-forqes-json.sh $instance
done < tests.txt) | parallel

git diff --exit-code .
