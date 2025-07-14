# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import json
import os
import logging
from Docker.Deploy import Deploy
from Docker.DockerHandle import DockerHandle


class Manage:
    def __init__(self):
        self.local_poc_path = os.path.join(os.path.dirname(__file__), "Data", "poc")

    def get_info(self, name: str) -> tuple:
        """
        Get the information of a specific POC.
        :param name: The name of the POC.
        :return: A dictionary containing the POC information, and a dictionary with necessary parameters
                 for running the benchmark.
        """
        poc_path = os.path.join(self.local_poc_path, name)
        if not os.path.exists(poc_path):
            logging.error(f"POC {name} does not exist.")
            return {}, {}

        info_file = os.path.join(self.local_poc_path, "info.json")
        if not os.path.exists(info_file):
            logging.error(f"Info file for POC {name} does not exist.")
            return {}, {}

        with open(info_file, 'r') as f:
            info = json.load(f)

        for item in info:
            security_issues = item.get("security_issues", [])
            for security_issue in security_issues:
                public_id = security_issue.get("public_id", "")
                if public_id.strip().upper() == name.strip().upper():

                    # Check if the POC exists and is available, if not, prompt the user
                    poc = security_issue.get("poc", {})
                    if not poc.get("exists", False):
                        logging.error(f"POC of {name} does not exist in info data.")
                    if not poc.get("available", False):
                        logging.error(f"POC of {name} is not available.")
                        print(f"POC of {name} is not available, please check the info file.")
                        choice = input("Do you want to run the benchmark anyway? (y/n): ").strip().lower()
                        if choice not in ['y', '']:
                            logging.info("User chose not to run the benchmark.")
                            raise KeyboardInterrupt

                    necessary = {
                        "git_repo": item.get("repo_url", ""),
                        "commit": security_issue.get("patch_commits", [{}])[0].get("commit_hash", ""),
                        "py_version": security_issue.get("python_version", ""),
                        "name": public_id.strip(),
                        "check_command": security_issue.get("check_command", ""),
                        "deploy_command": security_issue.get("deploy_command", None),
                        "run_kwargs": security_issue.get("run_kwargs", {}),
                    }
                    return item, necessary

        return {}, {}

    @staticmethod
    def format_info(info: dict):
        """
        Format the POC information into a readable string.
        :param info: The POC information dictionary.
        :return:
        """
        if not info:
            logging.error("No information available.")
            return

        output = "-" * 50 + "\n"
        for key, value in info.items():
            if isinstance(value, list):
                output += f"{key}:\n"
                for item in value:
                    if isinstance(item, dict):
                        output += "\t" + "\n\t".join(f"{k}: {v}" for k, v in item.items()) + "\n"
                    else:
                        output += f"\t{item}\n"
            output += f"{key}:\t{value}\n"
        output += "-" * 50 + "\n"
        return output

    def run_bench(self, git_repo: str, commit: str, py_version: str, name: str, check_command: str, patch: str = "",
                  lazy_deploy: bool = True, deploy_command: list = None, run_kwargs: dict = None):
        """
        Run the benchmark for a specific POC.
        :param git_repo: Git repository URL.
        :param commit: Commit hash to check out.
        :param py_version: Python version to use for the deployment.
        :param name: Name of the POC to run.
        :param check_command: Check command to run before and after patching.
        :param patch: Path to the patch file, if any.
        :param lazy_deploy: Lazy deploy or not, default is True.
        :param deploy_command: Command to run for deployment, if empty, will deploy automatically.
        :param run_kwargs: Additional arguments for running the container.
        :return:
        """
        deployer = Deploy()
        if not git_repo.startswith("http"):
            git_url = "https://github.com/" + git_repo.lstrip('/')
        else:
            git_url = git_repo.rstrip('/')
        repo_name = git_url.split("/")[-1].replace(".git", "")
        path = deployer.clone(git_url)
        current_commit = commit
        pc = deployer.get_parent_commit(repo_path=path, current_commit=current_commit)
        deployer.checkout(path, pc)

        if patch == '':
            # download the patch
            git_patch = f"{git_url}/commit/{current_commit}.patch"
            patch_path = deployer.download(git_patch,
                                           os.path.join(deployer.space_path, f"{repo_name}_{current_commit}.patch"))
        else:
            patch_path = patch
        # deployer.copy_file(patch_path, os.path.join(path, f"{repo_name}.patch"))

        # build the docker image and run the container by dockerfile
        logging.info(f"Building Docker image for {repo_name} at commit {pc} with Python version {py_version}.")
        logging.info(f"Please wait, this may take a while...")
        dp, container_ori = deployer.dockerfile_deploy(py_version=py_version, file_path=path, commit=pc,
                                                       lazy_deploy=lazy_deploy, other_commands=deploy_command,
                                                       run_kwargs=run_kwargs)
        logging.info(f"Container ID: {container_ori.id}")
        dh = DockerHandle()
        image_deployed = dh.get_image_by_container(container_id=container_ori.id)
        container_patched = dh.run_by_image(image=image_deployed, patched=True, run_kwargs=run_kwargs)
        logging.info(f"Container ID (patched): {container_patched.id}")

        # copy the poc files to the container
        deployer.docker_handle.container_copy(container_id=container_ori.id,
                                              src_path=self.local_poc_path,
                                              dest_path="/vulbench/poc")
        deployer.docker_handle.container_copy(container_id=container_patched.id,
                                              src_path=self.local_poc_path,
                                              dest_path="/vulbench/poc")

        # copy the patch file to the container
        deployer.docker_handle.container_copy(container_id=container_patched.id,
                                              src_path=patch_path,
                                              dest_path=f"/vulbench/{repo_name}.patch")

        # check_command = check_command
        output = deployer.docker_handle.container_exec(container_id=container_ori.id, command=check_command)
        logging.info(f"Output before patching: \n{output.strip()}")

        # patch the container and run the POC in the patched container
        deployer.docker_handle.container_exec(container_id=container_patched.id,
                                              command=f"git apply /vulbench/{repo_name}.patch")

        output = deployer.docker_handle.container_exec(container_id=container_patched.id, command=check_command)
        logging.info(f"Output after patching: \n{output.strip()}")

        # run the lazy deploy script
        if lazy_deploy:
            logging.info("Running lazy deploy script in both containers, this may take a while... ")
            deployer.docker_handle.container_exec(container_id=container_ori.id, command="bash /vulbench/vb_deploy.sh")
            deployer.docker_handle.container_exec(container_id=container_patched.id,
                                                  command="bash /vulbench/vb_deploy.sh")
            logging.info("Lazy deploy script executed successfully in both containers.")

        logging.info("Running POC...")
        # Run the POC in the original container
        output = deployer.docker_handle.container_exec(container_id=container_ori.id,
                                                       command=f"python /vulbench/poc/{name}/run.py")
        logging.info(f"Output of POC execution: \n{output.strip()}")

        # Run the POC again after patching
        output = deployer.docker_handle.container_exec(container_id=container_patched.id,
                                                       command=f"python /vulbench/poc/{name}/run.py")
        logging.info(f"Output of POC execution after patching: \n{output.strip()}")

        # Get vb_poc_result.json from the both container
        result_dir = os.path.join(deployer.space_path, f"result")
        result_ori = deployer.docker_handle.get_files_from_container(container_id=container_ori.id,
                                                                     src_path="/vulbench/vb_poc_result.json",
                                                                     dest_path=result_dir)
        if result_ori is not None:
            result_ori = os.path.join(result_dir, f"vb_poc_result.json")
            ori_to = os.path.join(result_dir, f"{repo_name}_{current_commit}ori.json")
            deployer.move_file(result_ori, ori_to)
            logging.info(f"Original result saved to {ori_to}")

        result_patched = deployer.docker_handle.get_files_from_container(container_id=container_patched.id,
                                                                         src_path="/vulbench/vb_poc_result.json",
                                                                         dest_path=result_dir)
        if result_patched is not None:
            result_patched = os.path.join(result_dir, f"vb_poc_result.json")
            patched_to = os.path.join(result_dir, f"{repo_name}_{current_commit}_patched.json")
            deployer.move_file(result_patched, patched_to)
            logging.info(f"Patched result saved to {patched_to}")


    def run_bench_by_name(self, name: str, patch: str):
        """
        Run the benchmark for a specific POC by its name.
        :param name: The name of the POC.
        :param patch: The path to the patch file.
        :return:
        """
        info, necessary = self.get_info(name)
        if not necessary:
            logging.error(f"Can not find POC {name} in the info file.")
            return
        print(f"Selected POC: {name}")
        print(self.format_info(info))
        logging.info(f"Running benchmark for POC: {name}")
        try:
            print("Please wait, this may take a while...")
            self.run_bench(git_repo=necessary["git_repo"],
                           commit=necessary["commit"],
                           py_version=necessary["py_version"],
                           name=name,
                           check_command=necessary["check_command"],
                           deploy_command=necessary["deploy_command"],
                           run_kwargs=necessary["run_kwargs"], )
            print("All done! You can check the results in the logs.")
        except Exception as e:
            logging.error(f"Error running benchmark for {name}: {e}")
            return
