# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import utils
import logging
import argparse

utils.setup_logging()
logging.info("VRBench initialized.")

parser = argparse.ArgumentParser(description="VRBench - A Benchmarking Tool for Vulnerability Repair")
parser.add_argument(
    "-n"
    "--new",
    type=str,
    default="poc",
    help="Add a new benchmark. Specify the benchmark type (e.g., 'poc'). Default is 'poc'."
)

