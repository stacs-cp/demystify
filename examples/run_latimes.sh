#!/usr/bin/env bash
mkdir latimes-results

for i in 3 2 1 0; do
    for solver in  \
            '{}' \
            '{"baseSizeMUS": 100000}' \
            '{"useUnsatCores": false}' \
            '{"baseSizeMUS": 100000, "useUnsatCores": false}' \
            '{"prechopMUSes12": true }' \
            '{"prechopMUSes12": true, "baseSizeMUS": 100000 }' \
            '{"prechopMUSes12": true, "useUnsatCores": false }' \
            '{"prechopMUSes12": true, "useUnsatCores": false, "baseSizeMUS": 100000 }' \
            '{"tryManyChopMUS": true }' \
            '{"tryManyChopMUS": true, "useUnsatCores": false }' \
            '{"minPrecheckMUS": true }' \
            '{"minPrecheckMUS": true, "useUnsatCores": false }' \
            '{"gallopingMUSes": true }' \
            '{"gallopingMUSes": true, "baseSizeMUS": 100000}' \
            '{"minPrecheckStepsMUS": true}' \
    
    do
        (time ./latimes.py $i "$solver") > "latimes-results/$i-$solver.html" 2> "latimes-results/$i-$solver.log" &
    done
    wait
done