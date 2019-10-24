#!/usr/bin/env python3

# run e.g.
# python3 -m cProfile -o msynth.prof scripts/run_microsynth.py "City of London" OA

import pstats

file = "./msynth.prof"

p = pstats.Stats(file)

p.strip_dirs().sort_stats("cumulative").print_stats("microsynthesis.py")
