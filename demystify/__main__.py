#!/usr/bin/env python3

import sys
import argparse
import os
import logging
import json
import time

# Let me import demystify
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import demystify
import demystify.explain

parser = argparse.ArgumentParser(description="Demystify")

parser.add_argument(
    "--puzzle", type=str, help="File containing JSON description of puzzle"
)

parser.add_argument("--eprimeparam", type=str, help="savilerow param file")

parser.add_argument("--eprime", type=str, help="savilerow eprime file")

parser.add_argument(
    "--debuginfo", action="store_true", help="Print (lots) of debugging info"
)

parser.add_argument(
    "--info", action="store_true", help="Print (some) debugging info"
)

parser.add_argument(
    "--repeats",
    type=int,
    default=5,
    help="Number of times to try generating each MUS",
)

parser.add_argument(
    "--multiple",
    action="store_true",
    help="Look (harder) for multiple choices at each step -- this biases the algorithm, but is not absolute"
)

parser.add_argument(
    "--cores", type=int, default=4, help="Number of CPU cores to use"
)

parser.add_argument(
    "--skip", type=int, default=0, help="Skip displaying MUSes of <= this size"
)

parser.add_argument(
    "--merge", type=int, default=1, help="Merge MUSes of <= this size"
)

parser.add_argument(
    "--incomplete",
    action="store_true",
    help="allow problems with multiple solutions",
)

parser.add_argument(
    "--steps", type=int, default=float("inf"), help="How many steps to perform"
)

parser.add_argument(
    "--nodomains",
    action="store_true",
    help="Only assign variables, do not remove domain values",
)

parser.add_argument(
    "--force",
    type=str,
    action="append",
    default=None,
    help="choose first non-trivial variable to be assigned",
)

parser.add_argument(
    "--json",
    type=str,
    action="append",
    default=None,
    help="optional JSON file output",
)

parser.add_argument(
    "--forqes",
    action="store_true",
    default=None,
    help="Use the FORQES algorithm for MUS finding",
)

args = parser.parse_args()

if args.puzzle is None and args.eprime is None:
    print("Must give a --puzzle or --eprime")
    sys.exit(1)

if args.puzzle is not None and args.eprime is not None:
    print("Can only give one of --puzzle or --eprime")
    sys.exit(1)

if args.eprime is not None and args.eprimeparam is None:
    print("--eprime requires --eprimeparam")
    sys.exit(1)

if args.info:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(pathname)s:%(lineno)d:%(name)s:%(message)s",
    )

if args.debuginfo:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s:%(pathname)s:%(lineno)d:%(name)s:%(message)s",
    )

demystify.config.LoadConfigFromDict(
    {"repeats": args.repeats, "cores": args.cores, "earlyExit": not args.multiple}
)

if args.forqes:
    mus_finder = "forqes"
else:
    mus_finder = "cascade"

explainer = demystify.explain.Explainer(mus_finder, skip=args.skip)

if args.puzzle is not None:
    name = os.path.basename(args.puzzle)
    explainer.init_from_json(args.puzzle)
else:
    name = os.path.basename(args.eprime)
    explainer.init_from_essence(args.eprime, args.eprimeparam)

if args.json is not None:
    output_path = args.json[0]
else:
    output_path = "./output" + str(int(time.time())) + ".json"

f = open(output_path, "w")

output = explainer.explain_steps()

f.write(json.dumps(output))

f.close()
