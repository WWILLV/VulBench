# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import os
import subprocess
import logging
import time
import json
import base64


class InOut:

    def __init__(self, poc_file=None, poc_input=None, poc_dependencies=None, output_dependencies=True):
        """
        Input and Output class for handling PoC (Proof of Concept) files.
        :param poc_file: Path to the POC file.
        :param poc_input: Input data for the PoC.
        :param poc_dependencies: List of dependencies required for the PoC.
        Will be installed via pip one by one; otherwise, it will be executed as a command if it starts with @.
        :param output_dependencies: If True, output the dependencies installed.
        """
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s\t%(name)s\t%(levelname)s\t[%(filename)s:%(lineno)d]\t%(message)s')
        if poc_file is None:
            raise ValueError('poc file must be provided')
        if not os.path.exists(poc_file):
            raise FileNotFoundError('Poc file {} does not exist'.format(poc_file))
        self.poc_file = poc_file
        self.poc_input = poc_input
        self.poc_output = ''
        self.poc_error = ''
        self.poc_dependencies = poc_dependencies if poc_dependencies is not None else []
        self.start_time = time.time()
        self.end_time = time.time()
        self.env_init(output=output_dependencies)

    def env_init(self, output=True):
        """
        Initialize the environment by installing required dependencies.
        :param output: If True, output the dependencies installed.
        :return: If dependencies are installed successfully, return True; otherwise, return False.
        """
        if type(self.poc_dependencies) is not list:
            raise TypeError('poc_dependencies must be a list')
        if len(self.poc_dependencies) == 0:
            return True

        for dependency in self.poc_dependencies:
            dependency = dependency.strip()
            if dependency == '':
                continue
            try:
                if dependency.startswith('@'):
                    logging.warning("Installing dependency by cmd directly: {}".format(dependency))
                    result = subprocess.run(dependency[1:], shell=True, check=True, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, universal_newlines=True)
                    if output:
                        logging.warning('Command output: {}'.format(result.stdout))
                    if result.returncode == 0:
                        logging.info('Successfully executed command: {}'.format(dependency))
                    else:
                        logging.error('Command failed with error: {}'.format(result.stderr))
                    continue
                pip_cmd = "pip install {}".format(dependency) if not dependency.startswith('pip') else dependency
                logging.info('Installing dependency via pip: {}'.format(dependency))
                subprocess.run(pip_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, )
                logging.info('Successfully installed dependency: {}'.format(dependency))
                continue
            except Exception as e:
                logging.error('Failed to install dependency {}: {}'.format(dependency, e))
                continue

    def run(self, timeout=None):
        """
        Run the POC with the provided input and capture the output.
        :param timeout: Timeout for the POC execution in seconds, default is None (no timeout).
        :return: Returns the output of the POC execution, error message if any, and the running time.
        """
        logging.info('Starting POC execution: {}'.format(self.poc_file))
        self.start_time = time.time()
        try:
            if self.poc_input is None:
                self.poc_input = ''
            if self.poc_input.strip() == '':
                logging.warning('POC input is empty, running without input.')
            else:
                logging.warning('Running POC with input: {}'.format(self.poc_input))

            # Set up the environment variables for the POC execution
            env = os.environ.copy()
            project_root = os.path.abspath(os.path.join(os.path.dirname(self.poc_file), '/vulbench/'))
            env_pythonpath = env.get('PYTHONPATH', '')
            if project_root not in env_pythonpath:
                env['PYTHONPATH'] = project_root + (':' + env_pythonpath if env_pythonpath else '')

            try:
                result = subprocess.run(['python', self.poc_file, self.poc_input], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, universal_newlines=True, env=env, timeout=timeout)
            except subprocess.TimeoutExpired as e:
                logging.error('POC execution timed out after {} seconds: {}'.format(timeout, e))
                with open('vb_poc_result.json', 'w') as f:
                    json.dump({
                        'poc': self.poc_file,
                        'input': self.poc_input,
                        'output': base64.b64encode(self.poc_output.encode()).decode(),
                        'error': base64.b64encode(str(e).encode()).decode(),
                        'running_time': timeout
                    }, f, indent=4, ensure_ascii=False)
                return '', str(e), 0
            self.end_time = time.time()
            running_time = self.end_time - self.start_time
            logging.warning('POC executed in {:.2f} seconds'.format(running_time))
            logging.warning('POC output: \n{}'.format(result.stdout))
            self.poc_output = result.stdout.strip()
            if result.returncode != 0:
                logging.warning("POC crashed with code {}".format(result.returncode))
                logging.warning("stderr:\n{}".format(result.stderr))
                if not result.stderr:
                    self.poc_error = ErrorCode(result.returncode).message()
            if result.stderr:
                logging.error('POC error: \n{}'.format(result.stderr))
                self.poc_error = result.stderr.strip()
            with open('vb_poc_result.json', 'w') as f:
                json.dump({
                    'poc': self.poc_file,
                    'input': self.poc_input,
                    'output': base64.b64encode(self.poc_output.encode()).decode(),
                    'error': base64.b64encode(self.poc_error.encode()).decode(),
                    'running_time': running_time
                }, f, indent=4, ensure_ascii=False)
            return result.stdout, result.stderr, running_time
        except Exception as e:
            logging.error('Error running POC: {}'.format(e))
            return '', str(e), 0

    def check_output(self, expected_output='', expected_error='', expected_time=5, match_blur=False, is_dos=False,
                     allow_empty_output=True):
        """
        Check if the output matches the expected output.
        :param expected_output: The expected output to check.
        :param expected_error: The expected error message, if any.
        :param expected_time: The expected time for the POC to run, used for DoS checks.
        :param match_blur: If True, allows for some flexibility in matching the result.
        :param is_dos: If True, indicates that the POC is a DoS (Denial of Service) test.
        :param allow_empty_output: If True, allows empty output to be considered a match.
        :return: Matches the output, error, and whether it ran overtime.
        """

        overtime = False
        match_error = True
        match_out = True

        if is_dos:
            logging.info('DoS test detected. Please check the running time.')
            if expected_time is None:
                expected_time = 5  # Default expected time for DoS
            running_time = self.end_time - self.start_time
            overtime = running_time > expected_time
            if overtime:
                logging.info(
                    'POC executed in {:.2f} seconds, which is longer than expected {} seconds.'.format(running_time,
                                                                                                       expected_time))

        if expected_error != '':
            logging.info('Expected error: \n{}'.format(expected_error))
            if match_blur:
                match_error = expected_error.strip() in self.poc_error.strip()
            else:
                match_error = self.poc_error.strip() == expected_error.strip()
            if not match_error:
                logging.error('Error does not match expected error.')
            else:
                logging.info('Error matches expected error.')

        if match_blur:
            match_out = expected_output.strip() in self.poc_output.strip()
        else:
            match_out = self.poc_output.strip() == expected_output.strip()
        if not allow_empty_output:
            match_out = match_out and expected_output.strip() != ''
        logging.info('Expected output: \n{}'.format(expected_output))
        if not match_out:
            logging.error('Output does not match expected output.')
        else:
            logging.info('Output matches expected output.')
        return match_out, match_error, overtime


class ErrorCode:
    """
    For situation where the POC execution fails without an error message.
    """

    def __init__(self, code):
        """
        Initialize an error code with a specific code.
        :param code: The error code.
        """
        self.code = str(code)

    def __str__(self):
        return self.message()

    def message(self):
        return "POC execution failed with no error message. Return code: " + self.code
