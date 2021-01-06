#!/usr/bin/env bash

script=$1

shift

eprime=$1

shift

while (( "$#" )); do
    echo $script $eprime $1
    shift
done