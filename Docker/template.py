# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging
import os
import utils


def get_dockerfile(py_version="", file_path="", dependencies=None, other_commands=None, environment="", cmd=None):
    """
    Generate the Dockerfile content.
    :param py_version: Python version to use in the Dockerfile.
    :param file_path: Path to the files to be copied into the Docker image.
    :param dependencies: Dependencies to be installed in the Docker image.
    :param other_commands: Other commands to be executed in the Docker image.
    :param environment: Environment variables to be set in the Docker image.
    :param cmd: Command to be executed when the Docker container starts.
    :return: Dockerfile content as a string.
    """

    py_version = py_version if py_version else "3.10"
    file_path = file_path if file_path else "/path/to/files/"
    dependencies = ' '.join(dep.strip() for dep in dependencies) if dependencies is not None and len(
        dependencies) > 0 else "patch git"
    other_commands = other_commands if other_commands is not None and len(other_commands) > 0 else [
        "pip install --no-cache-dir -r requirements.txt"
    ]
    ocs = "\n"
    for oc in other_commands:
        ocs += f"RUN {oc.strip()}\n"
    environment = environment if environment else ""
    cmd = cmd if cmd is not None and len(cmd) > 0 else ["/bin/bash"]

    # if not os.path.exists(file_path):
    #     logging.error(f"Path {file_path} does not exist.")
    #     raise FileNotFoundError(f"Path {file_path} does not exist.")
    if os.path.isdir(file_path):
        if not file_path.endswith('/'):
            file_path += '/'

    base_dockerfile = f"""
FROM python:{py_version}

USER root

RUN mkdir /vrbench

WORKDIR /vrbench

COPY {file_path}/ /vrbench/

RUN apt-get update \\
    && apt-get install -y --no-install-recommends build-essential libssl-dev libffi-dev {dependencies} \\
    && apt-get clean

# Initialize the environment
RUN pip install --upgrade pip
{ocs}

{environment}

CMD {str(cmd).replace("'", '"')}
    """

    return base_dockerfile
