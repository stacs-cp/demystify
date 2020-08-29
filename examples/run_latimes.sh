#!/usr/bin/env bash
mkdir latimes-results

for i in 3 2 1 0; do
    for solver in "{}" '{"gallopingMUSes": true}' '{"prechopMUSes": true }' '{"quarterChopMUS": true}' '{"minPrecheckMUS": true}' '{"minPrecheckStepsMUS": true}'; do
        (time ./latimes.py $i "$solver") > "latimes-results/$i-$solver.html" 2> "latimes-results/$i-$solver.log" &
    done
    wait
done