# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import argparse
from Invoke import Invoke


parser = argparse.ArgumentParser(description="VRBench - A Benchmarking Tool for Vulnerability Repair")
parser.add_argument(
    "-n",
    "--new",
    type=str,
    metavar="poc_name",
    help="Add a new POC."
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
    metavar="poc_name",
    help="Start a POC test. Specify the poc name to start it."
)

if not any(vars(parser.parse_args()).values()):
    print("Please provide arguments. Use -h/--help for more information.")
    exit(0)

try:
    vrbench = Invoke(parser.parse_args())
    vrbench.start()
except KeyboardInterrupt:
    print("[VRBench] Interrupted by user.")
    print("Have a nice day!")
except Exception as e:
    print(f"Top-level exception occurred: {e}")
