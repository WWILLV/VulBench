# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import argparse
from Invoke import Invoke


parser = argparse.ArgumentParser(description="VRBench - A Benchmarking Tool for Vulnerability Repair")
parser.add_argument(
    "-n",
    "--new",
    type=str,
    metavar="benchmark_name",
    help="Add a new benchmark."
)
parser.add_argument(
    "-c",
    "--clean",
    type=str,
    metavar="all,log,docker,workspace",
    help="Clean VRBench. Specify 'all' to clean all, or provide a specific type (log,docker,workspace)."
)
parser.add_argument(
    "-s",
    "--start",
    type=str,
    metavar="benchmark_name",
    help="Start a benchmark. Specify the benchmark name to start it."
)

if not any(vars(parser.parse_args()).values()):
    print("Please provide arguments. Use -h/--help for more information.")
    exit(0)

vrbench = Invoke(parser.parse_args())
vrbench.start()
