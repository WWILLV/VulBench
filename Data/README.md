## How to create a new poc

1. Run `python bench.py -n <name>` to create a new poc with the given name.
2. Modify the `Data/poc/info.json` file to set the python_version, check_command, and other data for the poc.
3. Add the poc code in the `Data/poc/<name>/` directory.
3. Run `python bench.py -r <name>` to run the poc and generate the results.

## How to write a new poc code

All poc code is copied from the `Data/poc/sample/`. 
Our poc is run by subprocess, so you can use any Python code in the poc.
The flow of the poc code is as follows:
```
Main Process of VulBench -> Data/poc/<name>/run.py -> poc
```
All poc code is dependent on `InOut.py`.

To run the poc code, you must modify the `run.py` file in the poc directory first.

For example:
```python
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from InOut import InOut

poc_file = os.path.join(os.path.dirname(__file__), 'code', 'poc.py')


def main():
    poc = InOut(poc_file, poc_dependencies=['requests'])
    result = poc.run()
    if result is None:
        return False
    poc_output, poc_error, running_time = result
    expected_output = "some expected output"
    expected_error = "some expected error"
    expected_time = 10
    check_poc = poc.check_output(expected_output=expected_output, expected_error=expected_error, match_blur=True)
    if any(check_poc):
        logging.info("POC executed successfully.")
        logging.info(f"Output: \n{poc_output}")
        if poc_error:
            logging.info(f"Error: \n{poc_error}")
        logging.info(f"Running time: {running_time:.2f} seconds")


if __name__ == "__main__":
    # # Have not implemented the automatic installation of dependencies yet.
    # raise Exception("Unable to verify")
    main()
```

1. Ensure that the path to the poc file is correct.
2. Constructor of `InOut` has four parameters:
   - `poc_file`: Path to the PoC file.
   - `poc_input`: Input data for the PoC.
   - `poc_dependencies`: List of dependencies required for the PoC. 
     Will be installed via pip one by one; otherwise, it will be executed as a command if it starts with @.
   - `output_dependencies`: If True, output the dependencies installed. (Default is True)
3. The `run()` method can pass a `timeout` parameter. 
   If the PoC does not return within the specified time, it will be terminated.
   It returns a tuple of three values: running output, running error, running time.
4. The `check_output()` method checks the output of the PoC. It has six parameters:
   - `expected_output`: The expected output of the PoC.
   - `expected_error`: The expected error message of the PoC.
   - `expected_time`: The expected time for the PoC to run, used for DoS checks.
   - `match_blur`: If True, allows for some flexibility in matching the result.
   - `is_dos`: If True, indicates that the PoC is a DoS (Denial of Service) test.
   - `allow_empty_output`: If True, allows empty output to be considered a match.
   
   `check_output()` returns a tuple of three boolean values: match_out, match_error, overtime
5. In the sample code, we raise an exception if the PoC cannot be verified. 
   You should modify this part according to your needs.
6. The poc code should be placed in the `Data/poc/<name>/code/` directory.
   You can write any Python code in the poc, and you can also refer to the samples provided by us.
