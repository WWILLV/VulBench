import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from InOut import InOut

poc_file = os.path.join(os.path.dirname(__file__), 'code', 'poc.py')


def main():
    """
    Main function to run and verify the POC.
    """
    poc = InOut(poc_file)
    result = poc.run()

    # If the run returns no result, exit early
    if result is None:
        return False

    poc_output, poc_error, running_time = result

    expected_output = ""
    expected_error = ""

    # Check if the output matches the expectation (supports fuzzy matching)
    check_poc = poc.check_output(expected_output=expected_output, expected_error=expected_error, match_blur=True)

    # If the check passes, log the success message
    if any(check_poc):
        logging.info("POC executed successfully.")
        logging.info("Output: \n{}".format(poc_output))
        if poc_error:
            logging.info("Error: \n{}".format(poc_error))
        logging.info("Running time: {:.2f} seconds".format(running_time))


if __name__ == "__main__":
    # Automatic installation of dependencies has not been implemented yet.
    raise Exception("Unable to verify")
    # main()
