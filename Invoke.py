# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import json
import logging
import os.path
import utils
import time
from Manage import Manage
from Docker.DockerHandle import DockerHandle
from Docker.Deploy import Deploy
from Data.PatchesAnalysis import PatchesAnalysis

utils.setup_logging()

class Invoke:
    def __init__(self, args=None):
        self.args = args

    def parse_args(self):
        fun_args = []

        if self.args.clean is not None:  # Cleaning up resources
            logging.info(f"Cleaning up resources with args: {self.args.clean}")
            clean_args = []
            for arg in self.args.clean.split(','):
                keyword = arg.strip().lower()
                if keyword == '':
                    continue
                if keyword not in ['all', 'workspace', 'log', 'docker']:
                    logging.error(f"Unknown clean argument: {keyword}")
                    return None
                else:
                    if keyword == 'all':
                        clean_args = ['all']
                        break
                    clean_args.append(keyword)
            if not clean_args:  # If no valid clean arguments were provided, default to 'log'
                clean_args = ['log']
            fun_args.append({"function": "clean", "args": clean_args})
            return fun_args  # If user selected clean, we return immediately
        elif self.args.new is not None:  # Creating a new POC
            new_arg = self.args.new.strip()
            if new_arg == '':
                logging.error("Must provide a name for the new poc.")
                return None
            fun_args.append({"function": "new", "args": new_arg})
        elif self.args.start is not None:
            start_arg = self.args.start.strip()
            if start_arg == '':
                logging.error("Must provide a name for the poc to start.")
                return None
            patch_path = ''
            if self.args.patch is not None:
                patch_path = self.args.patch.strip()
                if patch_path == '':
                    logging.error("Must provide a path for the patch to apply.")
                    return None
                if not os.path.exists(patch_path):
                    logging.error(f"Patch file does not exist: {patch_path}")
                    return None
            fun_args.append({"function": "start", "args": start_arg, "patch": patch_path})

        return fun_args

    @staticmethod
    def clean(clean_args: list):
        """
        Clean up resources based on the provided arguments.
        :param clean_args: Only 'all', 'workspace', 'log', and 'docker' are supported.
        :return:
        """

        def clean_workspace():
            logging.info("[CLEAN] Cleaning workspace.")
            # Only back up the workspace, do not delete it
            workspace_path = utils.get_workspace()
            logging.warning(f"Cleaning workspace at: {workspace_path}")
            if os.path.exists(workspace_path):
                logging.warning("It will only back up the workspace; please remove it manually if you need to.")
                backup_path = f"{workspace_path}.backup_{int(time.time())}.tar"
                deployer = Deploy()
                logging.info(f"Backing up workspace to: {backup_path}")
                try:
                    deployer.tar_dir(workspace_path, backup_path)
                    logging.info("Workspace backup successfully.")
                except Exception as e:
                    logging.error(f"Failed to back up workspace: {e}")
                    return
            else:
                logging.info("Workspace directory does not exist, nothing to clean.")

        def clean_docker():
            logging.info("[CLEAN] Cleaning Docker resources.")
            dh = DockerHandle()

            # Clean up Docker containers related to VulBench
            vb_containers = dh.get_container_vulbench()
            if vb_containers:
                all_containers = [container.name for container in vb_containers if container.name]
                print(f"{len(all_containers)} VulBench containers found: {all_containers}")
                choice = input("Do you want to remove these containers? (y/n): ").strip().lower()
                if choice == 'y':
                    for container in vb_containers:
                        logging.warning(f"Removing container: {container.name}")
                        dh.container_remove(container.name)
                else:
                    logging.info("Skipping container removal.")
            else:
                logging.info("No VulBench containers found.")

            # Clean up Docker images related to VulBench
            vb_images = dh.get_image_vulbench()
            if vb_images:
                all_images = [image.tags[0] for image in vb_images if image.tags]
                print(f"{len(all_images)} VulBench images found: {all_images}")
                choice = input("Do you want to remove these images? (y/n): ").strip().lower()
                if choice == 'y':
                    for image in vb_images:
                        logging.warning(f"Removing image: {image.tags[0]}")
                        dh.image_remove(image.tags[0])
                else:
                    logging.info("Skipping image removal.")
            else:
                logging.info("No VulBench images found.")

            dh.remove_dangling_images(only_vulbench=True)

        def clean_log():
            logging.info("[CLEAN] Cleaning logs.")
            utils.clean_logs()

        if 'all' in clean_args:
            logging.info("Cleaning all resources.")
            clean_workspace()
            clean_log()
        else:
            for arg in clean_args:
                if arg == 'workspace':
                    clean_workspace()
                elif arg == 'log':
                    clean_log()
                elif arg == 'docker':
                    clean_docker()
                else:
                    logging.error(f"Unknown clean argument: {arg}")

    @staticmethod
    def new_poc(name: str):
        """
        Create a new POC of VulBench.
        :param name: The name of the new POC.
        :return:
        """

        def get_info_by_cve(cve: str):
            """
            Get info data by CVE.
            :param cve: CVE ID.
            :return: info data.
            """
            patches_poc = os.path.join(os.path.dirname(__file__), 'Data', 'patches_poc.json')
            if not os.path.exists(patches_poc):
                logging.error(f"patches_poc file does not exist: {patches_poc}")
                return None
            pa = PatchesAnalysis(patches_poc)
            patches = pa.select_patches_by_public_id(public_id=cve)
            if len(patches) == 0:
                return None
            logging.info(f"Found {len(patches)} patches for CVE: {cve}")
            patch = patches[0]
            logging.info(f"Selected first only: \n{patch}")
            print(f"Selected patch for CVE {cve}: \n{Manage().format_info(patch)}")

            if patch.get("security_issues") is None:
                logging.error(f"No security issues found for CVE: {cve}")
                return None

            for issue in patch["security_issues"]:
                if issue.get("public_id").lower().strip() == cve.lower().strip():
                    issue["python_version"] = ""
                    issue["check_command"] = ""
                    issue["run_kwargs"] = {}
                    issue["poc"]["exists"] = True
                    issue["poc"]["type"] = "executable"
                    issue["poc"]["available"] = False
                    break

            return patch

        logging.info(f"Creating a new VulBench POC: {name}")
        deployer = Deploy()
        sample = os.path.join(os.path.dirname(__file__), 'Data', 'poc', 'sample')
        new_poc_dir = os.path.join(os.path.dirname(__file__), 'Data', 'poc', name)
        if os.path.exists(sample):
            if os.path.exists(new_poc_dir):
                logging.error(f"POC directory already exists: {new_poc_dir}")
                return
            deployer.copy_dir(sample, new_poc_dir)
        else:
            logging.error(f"Sample directory does not exist: {sample}")
        if os.path.exists(new_poc_dir):
            logging.info(f"New POC '{name}' created successfully.")
            logging.info(f"Benchmark files are located at: {new_poc_dir}")
            logging.info("Please edit the benchmark files in above directory.")
            logging.info("Try to update the info.json file.")
            info = get_info_by_cve(name)
            if info is not None:
                info_path = os.path.join(os.path.dirname(__file__), 'Data', 'poc', 'info.json')
                with open(info_path, 'r', encoding='utf-8') as f:
                    info_data = json.load(f)

                update_flag = False
                for idata in info_data:
                    if idata.get("library_name","").lower().strip() == info["library_name"].lower().strip():
                        logging.info(f"Info data for CVE '{name}' already exists, updating it.")
                        idata = info
                        update_flag = True
                        break
                if not update_flag:
                    info_data.append(info)

                with open(info_path, 'w', encoding='utf-8') as f:
                    json.dump(info_data, f, indent=4, ensure_ascii=False)

                logging.info(f"Info data for CVE '{name}' written to: {info_path}")
            else:
                logging.error(f"Failed to get info data for CVE '{name}'.")
                logging.error("Please update the info.json file manually.")
        else:
            logging.error(f"New POC '{name}' creation failed.")

    def start(self):
        logging.info("VulBench initialized.")
        fun_args = self.parse_args()
        if fun_args is None:
            return

        for fun_arg in fun_args:
            if fun_arg['function'] == 'clean':  # Cleaning up resources
                self.clean(fun_arg['args'])
                break
            if fun_arg['function'] == 'new':  # Creating a new benchmark
                self.new_poc(fun_arg['args'])
                break
            if fun_arg['function'] == 'start':
                manage = Manage()
                manage.run_bench_by_name(fun_arg['args'], fun_arg['patch'])
                break

        pass
