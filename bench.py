# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import utils
import logging
import argparse
from Invoke import Invoke


parser = argparse.ArgumentParser(description="VRBench - A Benchmarking Tool for Vulnerability Repair")
parser.add_argument(
    "-n",
    "--new",
    type=str,
    help="Add a new benchmark."
)
parser.add_argument(
    "-c",
    "--clean",
    type=str,
    help="Clean VRBench. Specify 'all' to clean all, or provide a specific type (log,docker,workspace)."
)
parser.add_argument(
    "-s",
    "--start",
    type=str,
    help="Start a benchmark. Specify the benchmark name to start it."
)

vrbench = Invoke(parser.parse_args())
vrbench.start()
