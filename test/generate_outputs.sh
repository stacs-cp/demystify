#!/bin/bash
for test in *.py; do
    python3 $test >$test.html 2>$test.log &
done

wait
