# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging
import os
import json
from LLM.ChatGPT import ChatGPT
from LLM.Prompt import Prompt


class PatchGen:
    def __init__(self):
        self.prompt = Prompt()
        self.llm = ChatGPT(system_prompt=self.prompt.get_prompt(prompt_type='system', prompt_name='patch_generation'))

    def get_patch(self, file_code: list = None, given_prompt: str = None) -> str:
        """
        Get patch from LLM based on the provided filename and code.
        :param file_code: Filename and code to be used for patch generation.
        :param given_prompt: Custom prompt to be used instead of the default.
        :return: Patch as a string.
        """

        if file_code is None:
            return ""

        if given_prompt is not None and given_prompt.strip() != "":
            prompt = given_prompt
            logging.info("Using given prompt for patch generation.")
        else:
            prompt = self.prompt.get_prompt(prompt_type='user', prompt_name='ask_directly', params=file_code)
        result = ""

        if self.llm.stream:
            for text_chunk in self.llm.get_response(prompt):
                result += text_chunk
            #     print(text_chunk, end="", flush=True)
            # print()
        else:
            response = self.llm.get_response(prompt)
            if response:
                result = response
                # print(response)
            else:
                logging.error("Could not get response from LLM")

        logging.info(f"Response from LLM: {result}")
        return result

    def generate_patch(self, data_path: str = '', prompt_path: str = '', add_vuln: bool = False) -> str:
        """
        Generate a patch based on the provided data path and optional prompt path.
        :param data_path: Directory containing the data files (e.g., path.txt and code files).
        :param prompt_path: If provided, use this prompt instead of the default one.
        :param add_vuln: Add vulnerability type to the patch if available.
        :return: The generated patch as a string.
        """

        if not os.path.exists(data_path) or not os.path.isdir(data_path):
            logging.error(f"Invalid data path: {data_path}")
            return ""

        path_file = os.path.join(data_path, 'path.txt')
        if not os.path.exists(path_file):
            logging.error(f"Path file does not exist: {path_file}")
            return ""

        filenames = []
        with open(path_file, 'r', encoding='utf-8') as f:
            filenames = f.read().splitlines()
        filenames = [filename.strip() for filename in filenames if filename.strip()]

        file_content = []

        for filename in filenames:
            if '->' in filename:
                filename, localfile = filename.split('->')
            else:
                localfile = os.path.basename(filename)

            filename = filename.strip()
            localfile = localfile.strip()

            if not os.path.exists(os.path.join(data_path, localfile)):
                logging.error(f"Local file does not exist: {os.path.join(data_path, localfile)}")
                continue
            with open(os.path.join(data_path, localfile), 'r', encoding='utf-8') as f:
                content = f.read()
            file_content.append({"filename": filename, "code": content})

        file_code = []
        for file in file_content:
            file_code.append({"FILENAME": file['filename'], "CODE": file['code']})
        file_code = [file_code]
        if add_vuln:
            if os.path.exists(os.path.join(os.path.dirname(data_path), 'info.json')):
                info_data = json.load(open(os.path.join(os.path.dirname(data_path), 'info.json'), 'r', encoding='utf-8'))
                dirname = os.path.basename(data_path)
                for library in info_data:
                    for issue in library.get('security_issues', []):
                        if issue.get('public_id', '').lower() == dirname.lower():
                            vuln_type = issue.get('type', '')
                            if vuln_type:
                                file_code[0].insert(0, {"VULNERABILITY_TYPE": vuln_type})

        given_prompt = None
        if prompt_path and os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                given_prompt = f.read()
        patch = self.get_patch(file_code=file_code, given_prompt=given_prompt)
        if patch.strip() == "":
            patch = "[VulBench No Patch]"
        if patch.strip().lower() == "[vulbench no patch]":
            return ""

        return patch.strip()

    def save_patch(self, data_dir: str, result_dir: str, prompt_dir: str = '', add_vuln: bool = False) -> bool:
        """
        Generate and save patches for all cases in the specified data directory.
        :param data_dir: Directory containing the data for which patches need to be generated.
        :param result_dir: Directory where the generated patches will be saved.
        :param prompt_dir: Optional directory containing custom prompts.
        :param add_vuln: Whether to add vulnerability type to the patch if available.
        :return: True if patches were successfully generated and saved, False otherwise.
        """

        if not os.path.exists(data_dir):
            logging.error(f"Data directory does not exist: {data_dir}")
            return False

        try:
            all_dir = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
            logging.info(f"Generating patches for {len(all_dir)} cases.")

            model = os.path.basename(self.llm.model)
            if model.strip() == "":
                exit()
            final_result_dir = os.path.join(result_dir, "patches", model)
            all_dir = list(sorted(all_dir))[::-1]
            for case in all_dir:
                if not os.path.exists(final_result_dir):
                    os.makedirs(final_result_dir)
                case_file = os.path.join(final_result_dir, f"{case}.patch")
                logging.info(f"Generating patch for case: {case}, saving to {case_file}")
                if os.path.exists(case_file):
                    logging.warning(f"{case_file} already exists, skipping.")
                    continue
                prompt_path = ''
                if prompt_dir and os.path.exists(prompt_dir):
                    prompt_path = os.path.join(prompt_dir, f"{case}.txt")
                patch = self.generate_patch(data_path=os.path.join(data_dir, case),
                                            prompt_path=prompt_path,
                                            add_vuln=add_vuln)
                with open(case_file, 'w', encoding='utf-8') as f:
                    f.write(patch)
                logging.info(f"Successfully saved patch for case {case} to {case_file}")
            return True
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return False

