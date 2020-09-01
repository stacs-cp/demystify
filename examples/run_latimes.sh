#!/usr/bin/env bash
mkdir latimes-results

for i in 3 2 1 0; do
    for solver in 
            '{}'
            '{"prechopMUSes12": True }'
            '{"prechopMUSes12": True, "baseSizeMUS": 10000 }'
            '{"prechopMUSes12": True, "useUnsatCores": False }'
            '{"tryManyChopMUS": True}'
            '{"minPrecheckMUS": True}'
            '{"gallopingMUSes": True}'
            '{"gallopingMUSes": True, "baseSizeMUS": 10000}'
            '{"minPrecheckStepsMUS": True}'
            '{"gallopingMUSes": True, "minPrecheckMUS": True}'
    
    ; do
        (time ./latimes.py $i "$solver") > "latimes-results/$i-$solver.html" 2> "latimes-results/$i-$solver.log" &
    done
    wait
done