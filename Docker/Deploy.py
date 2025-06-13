import logging
import os
from typing import Any

import git
import requests
import zipfile
import tarfile
import subprocess

from Docker.template import get_dockerfile
from Docker.DockerHandle import DockerHandle
from utils import get_workspace


class Deploy:
    def __init__(self):
        """
        Deploy class for managing deployment tasks such as downloading files,
        """
        self.space_path = get_workspace()
        self.docker_handle = DockerHandle()

    def download(self, url: str, path='') -> None:
        """
        Downloads a file from the given URL to the specified path.
        :param url: The URL of the file to download.
        :param path: The local path where the file should be saved.
        """
        if path == '':
            path = os.path.join(self.space_path, url.split('/')[-1])
        response = requests.get(url)
        logging.info(f"Downloading {url} to {path}")
        try:
            with open(path, 'wb') as file:
                file.write(response.content)
        except Exception as e:
            logging.error(f"Failed to download {url} to {path}: {e}")

    def clone(self, repo_url: str, path='') -> str:
        """
        Clones a Git repository to the specified local path.
        :param repo_url: The URL of the Git repository to clone.
        :param path: The local path where the repository should be cloned.
        :return: The local path where the repository was cloned.
        """
        if path == '':
            path = os.path.join(self.space_path, repo_url.split('/')[-1].removesuffix('.git'))
        logging.info(f"Cloning repository {repo_url} to {path}")
        try:
            git.Repo.clone_from(repo_url, path)
        except Exception as e:
            logging.error(f"Failed to clone repository {repo_url}: {e}")
        return path

    @staticmethod
    def checkout(repo_path: str, commit: str) -> None:
        """
        Checks out a specific commit in a Git repository.
        :param repo_path: The local path to the Git repository.
        :param commit: The commit hash to check out.
        """
        try:
            repo = git.Repo(repo_path)
            logging.info(f"Checking out commit {commit} in repository {repo_path}")
            repo.git.checkout(commit)
            logging.info(f"Checked out commit {commit} successfully.")
        except Exception as e:
            logging.error(f"Failed to check out commit {commit} in repository {repo_path}: {e}")

    def unzip(self, file_path: str, extract_to='') -> None:
        """
        Unzips or tars a file based on its extension.
        :param file_path: The path to the zip or tar file.
        :param extract_to: The directory where the contents should be extracted.
        """
        if not os.path.exists(file_path):
            logging.error(f"File {file_path} does not exist.")
            return
        if extract_to == '':
            extract_to = os.path.join(self.space_path,
                                      os.path.basename(file_path).removesuffix('.zip').removesuffix('.tar'))
        try:
            if file_path.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                    logging.info(f"Extracted {file_path} to {extract_to}")
            elif file_path.endswith('.tar'):
                with tarfile.open(file_path, 'r') as tar_ref:
                    tar_ref.extractall(extract_to)
                    logging.info(f"Extracted {file_path} to {extract_to}")
            else:
                logging.error(f"Unsupported file type for {file_path}. Only .zip and .tar files are supported.")
        except Exception as e:
            logging.error(f"Failed to extract {file_path}: {e}")

    def eval(self, command: str) -> str:
        """
        Evaluates the given command string.
        WARNING: This method executes system commands and should be used with caution.
        :param command: The system command to evaluate.
        :return: Re
        """
        whitelist = ['wget', 'curl', 'git']
        checked_command = command.split()[0].lower()
        if checked_command not in whitelist:
            logging.error(f"Tried to execute a command not in whitelist: {checked_command}")
            raise ValueError(f"Command '{checked_command}' is not allowed. Only {whitelist} are permitted.")
        logging.warning(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, check=True, cwd=self.space_path, capture_output=True)
        logging.warning(f"Command '{command}' executed successfully with return code {result.returncode}")
        result_str = result.stdout.decode('utf-8') if result.stdout else ''
        logging.warning(f"Command output: {result_str}")
        if result.returncode != 0:
            logging.error(f"Command '{command}' failed with return code {result.returncode}")
        return result_str

    @staticmethod
    def get_parent_commit(github_repo=None, repo_path=None, current_commit='') -> str | None:
        """
        Gets the parent commit of the current commit in a GitHub repository or local Git repo path.
        :param github_repo: GitHub repository
        :param repo_path: Local path to the Git repository
        :param current_commit: Current commit hash
        :return: Parent commit hash or None if not found
        """
        try:
            if repo_path is not None:
                repo = git.Repo(repo_path)
                commit = repo.commit(current_commit)
                parent_commit = commit.parents[0] if commit.parents else None
                logging.info(f"Parent commit for {current_commit} is {parent_commit.hexsha if parent_commit else None}")
                return parent_commit.hexsha if parent_commit else None
            else:
                if github_repo is None:
                    raise ValueError("Either 'github_repo' or 'repo_path' must be provided.")
                if github_repo.startswith('http'):
                    github_repo = github_repo.split('github.com/')[-1].removesuffix('.git')
                github_api_url = f"https://api.github.com/repos/{github_repo}/commits/{current_commit}"
                response = requests.get(github_api_url)
                if response.status_code == 200:
                    commit_data = response.json()
                    parent_commit = commit_data.get('parents', [{}])[0].get('sha')
                    logging.info(f"Parent commit for {current_commit} is {parent_commit}")
                    return parent_commit
                else:
                    logging.error(f"Failed to fetch commit data from GitHub API: {response.status_code}")
                    return None
        except Exception as e:
            logging.error(f"Error getting parent commit: {e}")
            return None

    def dockerfile_deploy(self, py_version="3.7.9", file_path="", dependencies=None, other_commands=None,
                          environment="", cmd=None, commit='') -> tuple[str, Any]:
        if file_path == '':
            logging.error(f"File path cannot be empty.")
            raise ValueError("File path cannot be empty.")
        if not os.path.exists(file_path):
            new_file_path = os.path.join(self.space_path, file_path)
            logging.warning(f"File path {file_path} does not exist, trying to use {new_file_path} instead.")
            if not os.path.exists(new_file_path):
                logging.error(f"File path {new_file_path} does not exist.")
                raise FileNotFoundError(f"File path {new_file_path} does not exist.")
            else:
                file_path_true = new_file_path
        else:
            file_path_true = file_path

        # Dockerfile path must be within the workspace directory
        if not file_path_true.startswith(self.space_path):
            logging.error(f"File path {file_path_true} is not in the workspace directory {self.space_path}.")
            raise ValueError(f"File path {file_path_true} is not in the workspace directory {self.space_path}.")
        file_path = os.path.relpath(file_path_true, self.space_path)

        if dependencies is None:
            dependencies = ["vim", "curl", "patch", "git"]
        if other_commands is None:
            other_commands = []
            for root, dirs, files in os.walk(os.path.dirname(file_path_true)):
                if 'setup.py' in files:
                    other_commands.append("python setup.py install")
                    break
                if 'requirements.txt' in files:
                    other_commands.append("pip install -r requirements.txt")
                    break
        if environment == "":
            environment = "ENV PATH=$PATH:/vrbench"
        if cmd is None:
            cmd = ["/bin/bash"]

        dockerfile_content = get_dockerfile(
            py_version=py_version,
            file_path=file_path,
            dependencies=dependencies,
            other_commands=other_commands,
            environment=environment,
            cmd=cmd
        )

        dockerfile_path = os.path.join(self.space_path, f"vrbench_{os.path.basename(file_path)}.dockerfile")
        with open(dockerfile_path, 'w') as dockerfile:
            dockerfile.write(dockerfile_content)
            logging.info(f"Dockerfile written to {dockerfile_path}")

        if commit != '':
            if len(commit) > 7:
                commit = commit[:7]
            commit = '_' + commit

        image_name = f"vrbench_{os.path.basename(file_path)}{commit}"
        container = self.docker_handle.run_by_dockerfile(dockerfile_path=dockerfile_path, image_name=image_name)
        logging.info(f"Container {container.id} created from image {image_name}")

        return dockerfile_path, container


if __name__ == "__main__":
    deployer = Deploy()
    path = deployer.clone("https://github.com/django/django")
    current_commit = "55519d6cf8998fe4c8f5c8abffc2b10a7c3d14"
    pc = deployer.get_parent_commit(repo_path=path, current_commit=current_commit)
    deployer.checkout(path, pc)
    dp, container = deployer.dockerfile_deploy(py_version="3.9", file_path=path, commit=pc)
    # path = deployer.clone("https://github.com/twangboy/salt")
    # pc = deployer.get_parent_commit(github_repo="https://github.com/twangboy/salt", current_commit="e6dd6a482a76e2c82fcc6eeb6df9030e453837")
    # deployer.checkout(path, pc)
    # dp, container = deployer.dockerfile_deploy(file_path=path)
    # dp, container = deployer.dockerfile_deploy(file_path="attic")
    logging.info(f"Container ID: {container.id}")
    patch = f"https://github.com/django/django/commit/{current_commit}.patch"
    deployer.download(patch, os.path.join(deployer.space_path, f"django_{current_commit}.patch"))
    deployer.docker_handle.container_copy(container_id=container.id,
                                       src_path=os.path.join(deployer.space_path, f"django_{current_commit}.patch"),
                                       dest_path="/vrbench/django.patch")
    check_command = 'awk "NR>=78 && NR<=84" django/contrib/humanize/templatetags/humanize.py'
    output = deployer.docker_handle.container_exec(container_id=container.id, command=check_command)
    logging.info(f"Output before patching: {output}")
    output = deployer.docker_handle.container_exec(container_id=container.id, command="git apply /vrbench/django.patch")
    logging.info(f"Output of patching: {output}")
    output = deployer.docker_handle.container_exec(container_id=container.id, command=check_command)
    logging.info(f"Output after patching: {output}")
