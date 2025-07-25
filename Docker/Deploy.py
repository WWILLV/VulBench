# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging
import os
from typing import Any
import git
import requests
import zipfile
import tarfile
import subprocess
import json
import shutil
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

    def download(self, url: str, path='') -> str:
        """
        Downloads a file from the given URL to the specified path.
        :param url: The URL of the file to download.
        :param path: The local path where the file should be saved.
        :return: The local path where the file was saved, otherwise an empty string if the download failed.
        """
        if path == '':
            path = os.path.join(self.space_path, url.split('/')[-1])
        response = requests.get(url)
        logging.info(f"Downloading {url} to {path}")
        try:
            with open(path, 'wb') as file:
                file.write(response.content)
            return path
        except Exception as e:
            logging.error(f"Failed to download {url} to {path}: {e}")
            return ''

    @staticmethod
    def move_file(src: str, dst: str) -> None:
        """
        Moves a file from the source path to the destination path.
        :param src: The source file path.
        :param dst: The destination file path.
        """
        if not os.path.exists(src):
            logging.error(f"Source file {src} does not exist.")
            return
        try:
            os.rename(src, dst)
            logging.info(f"Moved file from {src} to {dst}")
        except Exception as e:
            logging.error(f"Failed to move file from {src} to {dst}: {e}")

    @staticmethod
    def copy_file(src: str, dst: str) -> None:
        """
        Copies a file from the source path to the destination path.
        :param src: The source file path.
        :param dst: The destination file path.
        """
        if not os.path.exists(src):
            logging.error(f"Source file {src} does not exist.")
            return
        try:
            shutil.copy(src, dst)
            logging.info(f"Copied file from {src} to {dst}")
        except Exception as e:
            logging.error(f"Failed to copy file from {src} to {dst}: {e}")

    @staticmethod
    def copy_dir(src: str, dst: str) -> None:
        """
        Copies a directory from the source path to the destination path.
        :param src: The source directory path.
        :param dst: The destination directory path.
        """
        if not os.path.exists(src):
            logging.error(f"Source directory {src} does not exist.")
            return
        try:
            shutil.copytree(src, dst)
            logging.info(f"Copied directory from {src} to {dst}")
        except Exception as e:
            logging.error(f"Failed to copy directory from {src} to {dst}: {e}")

    @staticmethod
    def tar_dir(src: str, dst: str) -> None:
        """
        Creates a tar archive of the specified directory.
        :param src: The source directory path to be archived.
        :param dst: The destination path for the tar archive.
        """
        if not os.path.exists(src):
            logging.error(f"Source directory {src} does not exist.")
            return
        try:
            with tarfile.open(dst, 'w') as tar:
                tar.add(src, arcname=os.path.basename(src))
            logging.info(f"Created tar archive {dst} from directory {src}")
        except Exception as e:
            logging.error(f"Failed to create tar archive {dst} from directory {src}: {e}")

    def clone(self, repo_url: str, path='') -> str:
        """
        Clones a Git repository to the specified local path.
        :param repo_url: The URL of the Git repository to clone.
        :param path: The local path where the repository should be cloned.
        :return: The local path where the repository was cloned.
        """
        if path == '':
            path = os.path.join(self.space_path, repo_url.split('/')[-1].removesuffix('.git'))
        if not repo_url.startswith("http"):
            repo_url = "https://github.com/" + repo_url.lstrip('/')
        logging.info(f"Cloning repository {repo_url} to {path}")
        if os.path.exists(path):
            logging.warning(f"Path {path} already exists. Skipping clone.")
            return path
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

    def package_install_cmd(self, package_dir: str, package_name: str = '') -> list:
        """
        Gets the installation commands for a package based on its directory contents.
        :param package_dir: The directory containing the package files.
        :param package_name: The name of the package to be installed.
        :return: A list of installation commands.
        """
        workspace = self.space_path
        pkg_installed_info = []
        pkg_installed_info_path = os.path.join(workspace, 'pkg_installed_info.json')
        pkg_name = package_name if package_name else os.path.dirname(package_dir).split(os.sep)[-1]
        if os.path.exists(pkg_installed_info_path):
            with open(pkg_installed_info_path, 'r') as f:
                pkg_installed_info = json.load(f)

        install_commands = []
        for file in os.listdir(package_dir):
            file_full_path = os.path.join(package_dir, file)
            if not os.path.isfile(file_full_path):
                continue
            file = file.lower()
            if file == 'pyproject.toml':
                try:
                    with open(file_full_path, 'r') as f:
                        content = f.read()
                except Exception as e:
                    logging.error(f"Failed to read {file_full_path}: {e}")
                    continue
                if '[tool.poetry]' in content or 'poetry.core.masonry.api' in content:
                    install_commands.append("pip install poetry")
                    install_commands.append("poetry config virtualenvs.create false")
                    install_commands.append("poetry install --no-interaction --no-ansi --no-root")
                    pkg_installed_info.append(
                        {"name": pkg_name, "path": file_full_path, "type": "poetry", "cmd": install_commands})
                elif '[tool.hatch' in content or 'hatchling.build' in content:
                    install_commands.append("pip install hatch")
                    install_commands.append("hatch env create")
                    pkg_installed_info.append(
                        {"name": pkg_name, "path": file_full_path, "type": "hatch", "cmd": install_commands})
                elif '[tool.towncrier]' in content:
                    install_commands.append("pip install towncrier")
                    install_commands.append("towncrier build")
                    install_commands.append("pip install .")
                    pkg_installed_info.append(
                        {"name": pkg_name, "path": file_full_path, "type": "towncrier", "cmd": install_commands})
                elif '[build-system]' in content and 'setuptools.build_meta' in content:
                    install_commands.append("pip install build")
                    install_commands.append("python -m build")
                    install_commands.append("pip install .")
                    pkg_installed_info.append(
                        {"name": pkg_name, "path": file_full_path, "type": "build", "cmd": install_commands})
                # elif '[tool.uv]' in content or 'uv.core.masonry.api' in content:
                #     install_commands.append("pip install uv")
                #     install_commands.append("uv install --no-interaction --no-ansi --no-root")
                #     pkg_installed_info.append(
                #         {"name": pkg_name, "path": file_full_path, "type": "uv", "cmd": install_commands})
                else:
                    logging.warning(f"Unsupported pyproject.toml format in {file_full_path}.")
                    logging.warning(f"Will check for other installation methods.")
                    continue
                    # install_commands.append("pip install -e .")
                    # pkg_installed_info.append(
                    #     {"name": pkg_name, "path": file_full_path, "type": "pip", "cmd": install_commands})
                break
            if file == 'setup.py':
                install_commands.append("python setup.py install")
                install_commands.append("pip install .")
                pkg_installed_info.append(
                    {"name": pkg_name, "path": file_full_path, "type": "setup", "cmd": install_commands})
                break
            if file == 'requirements.txt':
                install_commands.append("pip install -r requirements.txt")
                pkg_installed_info.append(
                    {"name": pkg_name, "path": file_full_path, "type": "requirements", "cmd": install_commands})
                break

        # If no specific installation commands were found, default to pip install -e .
        if len(install_commands) == 0:
            install_commands.append("pip install -e .")
            pkg_installed_info.append(
                {"name": pkg_name, "path": package_dir, "type": "pip", "cmd": install_commands})

        with open(pkg_installed_info_path, 'w') as f:
            json.dump(pkg_installed_info, f, indent=4)
        return install_commands

    def get_package_installed_info(self, package_name='', package_dir='') -> list:
        """
        Gets the installed package information based on the package name or directory.
        :param package_name: The name of the package to get information for.
        :param package_dir: The directory containing the package files.
        :return: List of installed package information.
        """
        workspace = self.space_path
        pkg_installed_info = []
        pkg_installed_info_path = os.path.join(workspace, 'pkg_installed_info.json')
        if not os.path.exists(pkg_installed_info_path):
            with open(pkg_installed_info_path, 'w') as f:
                json.dump([], f, indent=4)
            return []
        if os.path.exists(pkg_installed_info_path):
            with open(pkg_installed_info_path, 'r') as f:
                pkg_installed_info = json.load(f)
        if package_name:
            return [pkg for pkg in pkg_installed_info if pkg['name'] == package_name]
        elif package_dir:
            return [pkg for pkg in pkg_installed_info if pkg['path'] == package_dir]
        else:
            return pkg_installed_info

    def package_uninstall_cmd(self, package_dir: str = '', package_name: str = '') -> list:
        """
        Gets the uninstallation commands for a package based on its directory contents.
        :param package_dir: The directory containing the package files.
        :return: A list of uninstallation commands.
        """
        pkg_installed_info = self.get_package_installed_info(package_name=package_name, package_dir=package_dir)
        if len(pkg_installed_info) == 0:
            logging.warning(f"No installed package information found for {package_name} or {package_dir}.")
            return []
        uninstall_commands = []
        for pkg in pkg_installed_info:
            if pkg['type'] == 'poetry':
                uninstall_commands.extend(["poetry remove " + pkg['name']])
                logging.warning(f"Uninstalling {pkg['name']} using poetry.")
            elif pkg['type'] == 'hatch':
                uninstall_commands.extend(["hatch env remove " + pkg['name']])
                logging.warning(f"Uninstalling {pkg['name']} using hatch.")
            elif pkg['type'] == 'setup':
                uninstall_commands.extend(["pip uninstall -y " + pkg['name']])
                logging.warning(f"Uninstalling {pkg['name']} using setup.py.")
            elif pkg['type'] == 'requirements':
                uninstall_commands.extend(["pip uninstall -r " + pkg['path']])
                logging.warning(f"Uninstalling {pkg['name']} using requirements.txt.")
        return uninstall_commands

    def dockerfile_deploy(self, py_version="3.7.9", file_path="", dependencies=None, other_commands=None,
                          environment="", cmd=None, commit='', package_name='', patch='', lazy_deploy=False,
                          run_kwargs=None) -> tuple[
        str, Any]:
        """
        Deploys a Docker container using a Dockerfile generated from the specified file path.
        :param py_version: python version to use in the Dockerfile.
        :param file_path: The workspace path to the file or directory to be used in the Dockerfile.
        :param dependencies: List of dependencies to be installed in the Docker container.
        :param other_commands: List of other commands to be executed in the Docker container.
        :param environment: Environment variables to be set in the Docker container.
        :param cmd: Command to run in the Docker container.
        :param commit: Commit hash to be used in the image name.
        :param package_name: Name of the package to be installed.
        :param patch: Path of the patch file to be copied into the Docker container.
        :param lazy_deploy: If True, the deployment will be lazy, meaning it will not execute the commands immediately.
        :param run_kwargs: Additional keyword arguments to pass to the Docker run command.
        :return: Dockerfile path and the created container object.
        """
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
            # for root, dirs, files in os.walk(os.path.dirname(file_path_true)):
            #     if 'setup.py' in files:
            #         other_commands.append("python setup.py install")
            #         break
            #     if 'requirements.txt' in files:
            #         other_commands.append("pip install -r requirements.txt")
            #         break
            other_commands.extend(self.package_install_cmd(file_path_true, package_name=package_name))
            # for file in os.listdir(file_path_true):
            #     file_full_path = os.path.join(file_path_true, file)
            #     if not os.path.isfile(file_full_path):
            #         continue
            #     file = file.lower()
            #     if file == 'pyproject.toml':
            #         with open(file_full_path, 'r') as f:
            #             content = f.read()
            #         if '[tool.poetry]' in content or 'poetry.core.masonry.api' in content:
            #             other_commands.append("pip install poetry")
            #             other_commands.append("poetry config virtualenvs.create false")
            #             other_commands.append("poetry install --no-interaction --no-ansi --no-root")
            #         elif '[tool.hatch' in content or 'hatchling.build' in content:
            #             other_commands.append("pip install hatch")
            #             other_commands.append("hatch env create")
            #         else:
            #             logging.warning(f"Unsupported pyproject.toml format in {file_full_path}.")
            #             other_commands.append("pip install -e .")
            #         break
            #     if file == 'setup.py':
            #         other_commands.append("python setup.py install")
            #         break
            #     if file == 'requirements.txt':
            #         other_commands.append("pip install -r requirements.txt")
            #         break
            if len(other_commands) == 0:
                logging.warning(f"No installation commands found in {file_path_true}. ")

        if lazy_deploy:
            # Not executing the commands immediately, but adding them to the deployment script for later execution.
            logging.info(
                "Lazy deploy is enabled. Other commands will be added to the `/vulbench/vb_deploy.sh` but not executed.")
            new_commands = []

            def shell_quote_single(s: str) -> str:
                return "'" + s.replace("'", "'\"'\"'") + "'"

            for oc in other_commands:
                oc = oc.strip()
                quoted_oc = shell_quote_single(oc)
                new_commands.extend([f"echo {quoted_oc} >> /vulbench/vb_deploy.sh"])

            other_commands = new_commands

            other_commands.extend(['chmod +x /vulbench/vb_deploy.sh'])

        if environment == "":
            environment = "ENV PATH=$PATH:/vulbench"
        if cmd is None:
            cmd = ["/bin/bash"]

        dockerfile_content = get_dockerfile(
            py_version=py_version,
            file_path=file_path,
            dependencies=dependencies,
            other_commands=other_commands,
            environment=environment,
            cmd=cmd,
            patch=patch
        )

        dockerfile_path = os.path.join(self.space_path, f"vulbench_{os.path.basename(file_path)}.dockerfile".lower())
        with open(dockerfile_path, 'w') as dockerfile:
            dockerfile.write(dockerfile_content)
            logging.info(f"Dockerfile written to {dockerfile_path}")

        if commit != '':
            if len(commit) > 7:
                commit = commit[:7]
            commit = '_' + commit

        image_name = f"vulbench_{os.path.basename(file_path)}{commit}".lower()
        container = self.docker_handle.run_by_dockerfile(dockerfile_path=dockerfile_path, image_name=image_name, run_kwargs=run_kwargs)
        if container is None:
            logging.error(f"Failed to create container from Dockerfile {dockerfile_path}.")
            raise RuntimeError(f"Failed to create container from Dockerfile {dockerfile_path}.")
        logging.info(f"Container {container.id} created from image {image_name}")

        return dockerfile_path, container
