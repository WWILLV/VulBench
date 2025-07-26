# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import argparse
from Invoke import Invoke


parser = argparse.ArgumentParser(description="VulBench - A Benchmarking Tool for Vulnerability Repair")
parser.add_argument(
    "-n",
    "--new",
    type=str,
    metavar="poc_name",
    help="Add a new PoC."
)
parser.add_argument(
    "-c",
    "--clean",
    type=str,
    metavar="all,log,docker,workspace",
    help="Clean VulBench. Specify 'all' to clean all, or provide a specific type (log,docker,workspace)."
)
parser.add_argument(
    "-r",
    "--run",
    type=str,
    metavar="poc_name",
    help="Run a PoC test. Specify the poc name to run it."
)
parser.add_argument(
    "-p",
    "--patch",
    type=str,
    metavar="path_to_patch",
    help="Apply a patch to target application. Provide the path to the patch file or directory."
)

if not any(vars(parser.parse_args()).values()):
    print("Please provide arguments. Use -h/--help for more information.")
    exit(0)

try:
    vbench = Invoke(parser.parse_args())
    vbench.start()
except KeyboardInterrupt:
    print("[VulBench] Interrupted by user.")
except Exception as e:
    print(f"[Error] Top-level exception occurred: {e}")

print("Have a nice day!")
