# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import json
import os
import logging
import base64
import time
import concurrent.futures
from Docker.Deploy import Deploy
from Docker.DockerHandle import DockerHandle
from Data.ResultAnalysis import BenchResult
from utils import get_workspace, load_config


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

    @staticmethod
    def show_results(result_file: str, output: bool = True, result_type: str = '') -> dict:
        """
        Show the results of the benchmark.
        :param result_file: The path to the result file.
        :param output: Whether to print the results to the console.
        :param result_type: The type of the result, can be any string to indicate the type of result.
        :return: Object containing the decoded results.
        """
        result = {
            "poc": "",
            "input": "",
            "output": "",
            "error": "",
            "running_time": 0
        }
        if not os.path.exists(result_file):
            logging.error(f"Result file {result_file} does not exist.")
            return result
        with open(result_file, 'r') as f:
            data = json.load(f)
        result["poc"] = data.get("poc", "")
        result["input"] = data.get("poc_input", "")
        result["output"] = base64.b64decode(data.get("poc_output", "")).decode('utf-8') if data.get(
            "poc_output") else ""
        result["error"] = base64.b64decode(data.get("poc_error", "")).decode('utf-8') if data.get("poc_error") else ""
        result["running_time"] = data.get("running_time", 0)
        if output:
            print()
            embed = '-' * 50
            if result_type != '':
                embed = '-' * 20 + f" {result_type.upper()} RESULT " + '-' * 20
            print(embed)
            if result['input'].strip() == '':
                print(f"[VulBench] POC {result['poc']} running with no input.")
            else:
                print(f"[VulBench] POC {result['poc']} running with input: {result['input']}")
            if result['output'].strip() != '':
                print(f"\n[VulBench] Output: \n{result['output']}")
            else:
                print(f"\n[VulBench] POC {result['poc']} running with no output.")
            if result['error'].strip() != '':
                print(f"\n[VulBench] Error: \n{result['error']}")
            else:
                print(f"\n[VulBench] POC {result['poc']} running with no error.")
            print(f"\n[VulBench] Running time: {result['running_time']} seconds")
            print(embed)
            print()
        return result

    def run_bench(self, git_repo: str, commit: str, py_version: str, name: str, check_command: str, patch: str = "",
                  lazy_deploy: bool = True, deploy_command: list = None, run_kwargs: dict = None) -> dict:
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
        :return: Results of the benchmark execution.
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

        bench_result = {
            "name": name,
            "patch_path": patch_path,
            "repo_name": repo_name,
            "repo_path": path,
            "commit": current_commit,
            "parent_commit": pc,
            "patch_result": {"git_apply": None, "patch_p1": None},
            "check_result": {"ori": None, "patched": None},
            "result_path": {"ori": None, "patched": None},
        }  # Initialize the benchmark result dictionary

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

        # patch the container and run the POC in the patched container
        patch_result = deployer.docker_handle.container_exec(container_id=container_patched.id,
                                                             command=f"git apply /vulbench/{repo_name}.patch")
        bench_result["patch_result"]["git_apply"] = patch_result
        if "error: patch failed:" in patch_result or "error: corrupt patch at line" in patch_result or str(
                patch_result).strip().startswith("error:"):
            logging.error(f"\n{patch_result}")
            logging.error(f"Patch {patch_path} does not apply to the container, try `patch` command")
            patch_result = deployer.docker_handle.container_exec(container_id=container_patched.id,
                                                                 command=f"sh -c 'patch -p1 < /vulbench/{repo_name}.patch'")
            logging.warning(f"\n{patch_result}")
            bench_result["patch_result"]["patch_p1"] = patch_result

        if check_command is not None and check_command.strip():
            # check_command = check_command
            output = deployer.docker_handle.container_exec(container_id=container_ori.id, command=check_command)
            logging.info(f"Output before patching: \n{output}")
            bench_result["check_result"]["ori"] = output

            output = deployer.docker_handle.container_exec(container_id=container_patched.id, command=check_command)
            logging.info(f"Output after patching: \n{output}")
            bench_result["check_result"]["patched"] = output

        # run the lazy deploy script
        if lazy_deploy:
            logging.info("Running lazy deploy script in both containers, this may take a while... ")
            # deployer.docker_handle.container_exec(container_id=container_ori.id, command="bash /vulbench/vb_deploy.sh")
            # deployer.docker_handle.container_exec(container_id=container_patched.id,
            #                                       command="bash /vulbench/vb_deploy.sh")
            # Use ThreadPoolExecutor to run the lazy deploy script in both containers concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(deployer.docker_handle.container_exec, container_ori.id,
                                    "bash /vulbench/vb_deploy.sh"),
                    executor.submit(deployer.docker_handle.container_exec, container_patched.id,
                                    "bash /vulbench/vb_deploy.sh")
                ]
                concurrent.futures.wait(futures)
            logging.info("Lazy deploy script executed successfully in both containers.")

        logging.info("Running POC...")
        # Run the POC in the original container
        output = deployer.docker_handle.container_exec(container_id=container_ori.id,
                                                       command=f"python /vulbench/poc/{name}/run.py")
        logging.info(f"Output of POC execution: \n{output}")

        # Run the POC again after patching
        output = deployer.docker_handle.container_exec(container_id=container_patched.id,
                                                       command=f"python /vulbench/poc/{name}/run.py")
        logging.info(f"Output of POC execution after patching: \n{output}")

        print(f"POC {name} executed successfully in both containers.")

        # Get vb_poc_result.json from the both container
        result_dir = os.path.join(deployer.space_path, f"result")
        result_ori = deployer.docker_handle.get_files_from_container(container_id=container_ori.id,
                                                                     src_path="/vulbench/vb_poc_result.json",
                                                                     dest_path=result_dir)
        if result_ori is not None:
            result_ori = os.path.join(result_dir, f"vb_poc_result.json")
            ori_to = os.path.join(result_dir, f"{name}_ori_{repo_name}_{current_commit}.json")
            deployer.move_file(result_ori, ori_to)
            logging.info(f"Original result saved to {ori_to}")
            bench_result["result_path"]["ori"] = ori_to
            self.show_results(ori_to, result_type="original")

        result_patched = deployer.docker_handle.get_files_from_container(container_id=container_patched.id,
                                                                         src_path="/vulbench/vb_poc_result.json",
                                                                         dest_path=result_dir)
        if result_patched is not None:
            result_patched = os.path.join(result_dir, f"vb_poc_result.json")
            patched_to = os.path.join(result_dir, f"{name}_patched_{repo_name}_{current_commit}.json")
            deployer.move_file(result_patched, patched_to)
            logging.info(f"Patched result saved to {patched_to}")
            bench_result["result_path"]["patched"] = patched_to
            self.show_results(patched_to, result_type="patched")

        return bench_result

    def run_bench_by_name(self, name: str, patch: str = ''):
        """
        Run the benchmark for a specific POC by its name.
        :param name: The name of the POC.
        :param patch: The path to the patch file.
        :return:
        """
        info, necessary = self.get_info(name)
        if not necessary:
            logging.error(f"Can not find POC {name} in the info file.")
            return None
        if patch != '' and not os.path.exists(patch):
            logging.error(f"Patch file {patch} does not exist.")
            return None
        print(f"Selected POC: {name}")
        print(self.format_info(info))
        logging.info(f"Running benchmark for POC: {name}")
        try:
            print("Please wait, this may take a while...")
            start_time = time.time()

            bench_result = self.run_bench(git_repo=necessary["git_repo"],
                                          commit=necessary["commit"],
                                          py_version=necessary["py_version"],
                                          name=name,
                                          check_command=necessary["check_command"],
                                          deploy_command=necessary["deploy_command"],
                                          run_kwargs=necessary["run_kwargs"],
                                          patch=patch if patch is not None else "")
            end_time = time.time()
            duration = end_time - start_time
            print(f"\n[VulBench] All test for {name} done! You can check the results in the logs.")
            logging.info(f"Benchmark for {name} completed in {duration:.2f} seconds.")
            print(f"[VulBench] Completed benchmark for {name} in {duration:.2f} seconds.\n")
            return bench_result
        except Exception as e:
            logging.error(f"Error running benchmark for {name}: {e}")
            return None

    def run_all_bench(self, patch_dir: str = None, poc_list: list = None):
        """
        Run the benchmark for all POCs.
        :param patch_dir: The directory containing patch files, if any.
        :param poc_list: A list of POC names to run, if None, will run all available POCs.
        :return:
        """
        info_file = os.path.join(self.local_poc_path, "info.json")
        if not os.path.exists(info_file):
            logging.error("Info file does not exist.")
            return

        if patch_dir != '' and not os.path.exists(patch_dir):
            logging.error(f"Patch directory {patch_dir} does not exist.")
            return

        with open(info_file, 'r') as f:
            info = json.load(f)

        if poc_list is None:
            available_id = [issue.get("public_id", "") for item in info for issue in item.get("security_issues", [])
                            if issue.get("poc", {}).get("available", False)]
        else:
            available_id = [name for name in poc_list if name.strip()]
        available_id = sorted(list(set(available_id)))[::-1]
        logging.info(f"Running benchmarks for {len(available_id)} available POCs.")
        logging.info(f"Available POCs: {', '.join(ai for ai in available_id)}")
        print(
            f"[VulBench] Running benchmarks for {len(available_id)} available POCs: {', '.join(ai for ai in available_id)}")
        index = 1
        total = len(available_id)
        all_bench_result = []
        start_time = time.time()
        for name in available_id:
            try:
                patch = ''
                if patch_dir != '':
                    patch_path = os.path.join(patch_dir, f"{name}.patch")
                    if os.path.exists(patch_path):
                        patch = patch_path

                # If not allow empty patch, continue to next POC
                allow_empty_patch = load_config().get("Patch", {}).get("allow_empty_patch", True)
                if not allow_empty_patch:
                    with open(patch, 'r') as f:
                        content = f.read().strip()
                    if content == '':
                        logging.warning("Do not allow empty patch, skipping this POC.")
                        continue

                print('-' * 50)
                print(f"[{index}/{total}] Running benchmark for POC: {name}")
                pass_time = time.time() - start_time
                remaining_time = (total + 1 - index) * pass_time / index
                print(
                    f"[VulBench] Time passed: {pass_time:.2f} seconds, estimated remaining time: {remaining_time:.2f} seconds")
                bench_result = self.run_bench_by_name(name, patch=patch)
                if bench_result is not None:
                    all_bench_result.append(bench_result)
                print('-' * 50)
                index += 1
            except KeyboardInterrupt:
                logging.info("Benchmarking interrupted by user.")
                break
            except Exception as e:
                logging.error(f"Error running benchmark for {name}: {e}")
                continue

        # Save all benchmark results to a file
        try:
            result_save_path = os.path.join(get_workspace(), f"VulBench_results_{time.time()}.json")
            with open(result_save_path, 'w') as f:
                json.dump(all_bench_result, f, indent=4)
            logging.info(f"All benchmark results saved to {result_save_path}")
            logging.info("Starting result analysis...")
            br = BenchResult(result_save_path)
            valid_patches, working_patches = br.analyze_result()
            print('-'*20+"VulBench"+'-'*20)
            print(f"Valid Patches [{len(valid_patches)}]:")
            for vp in valid_patches:
                print(f"{vp.get('name','')}\t{vp.get('patch_path','')}")
            print(f"Working Patches [{len(working_patches)}]:")
            for wp in working_patches:
                print(f"{wp.get('name','')}\t{wp.get('patch_path','')}")
            print('-'*20+f"Result: {os.path.basename(result_save_path)}"+'-'*20)
        except Exception as e:
            logging.error(f"Error saving all benchmark results: {e}")

        dh = DockerHandle()
        images = dh.get_image_vulbench()
        containers = dh.get_container_vulbench()
        if len(containers) >= 3 * len(images):
            msg = (f"{len(images)} VulBench images and {len(containers)} containers found, " +
                   "please clean up the unused containers and images with `-c docker`.")
            logging.warning(msg)
            print(msg)

        return all_bench_result
