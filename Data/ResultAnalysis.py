# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import os
import json
import base64
import logging


class PatchResult:
    def __init__(self, result_path):
        self.result_path = result_path
        self.result_data = self.load_result()

    def load_result(self, result_path=None):
        if result_path is None:
            result_path = self.result_path
        if not os.path.exists(result_path):
            raise FileNotFoundError(f"Result file {result_path} does not exist.")

        with open(result_path, 'r', encoding='utf-8') as file:
            result_data = json.load(file)
        # logging.info(f"Loaded results from {result_path}")
        return result_data

    def get_result(self, result_data=None):
        if result_data is None:
            result_data = self.result_data
        data = {
            'poc': '',
            'poc_input': '',
            'poc_output': '',
            'poc_error': '',
            'running_time': 0,
            'expected_output': '',
            'expected_error': '',
            'expected_time': 0,
            'match_result': {
                'output': False,
                'error': False,
                'ontime': False,
                'is_dos': False
            }
        }
        data.update(result_data)
        data['poc_output'] = base64.b64decode(data['poc_output']).decode('utf-8') if data['poc_output'] else ''
        data['poc_error'] = base64.b64decode(data['poc_error']).decode('utf-8') if data['poc_error'] else ''
        return data

    def result_diff(self, compared, local=None):
        diff = {}
        if local is None:
            local = self.get_result()

        for key in local:
            if key not in compared or local[key] != compared[key]:
                diff[key] = {
                    'local': local.get(key, None),
                    'compared': compared.get(key, None)
                }
        return diff

    def get_pair(self):
        dir_path = os.path.dirname(self.result_path)
        file_name = os.path.basename(self.result_path)
        if '_ori' in file_name:
            pair_file = file_name.replace('_ori', '_patched')
        elif '_patched' in file_name:
            pair_file = file_name.replace('_patched', '_ori')
        else:
            logging.warning(f"Cannot determine pair file for {file_name}.")
            return ''

        pair_file = os.path.join(dir_path, pair_file)
        if not os.path.exists(pair_file):
            logging.warning(f"Pair file {pair_file} does not exist.")
            return ''

        logging.info(f"Found pair file: {pair_file}")
        return pair_file

    def analyze_result(self):
        ori_result = self.get_result()
        pair_file = self.get_pair()
        if not pair_file:
            logging.warning("No pair file found for analysis.")
            return

        patched_result = self.get_result(self.load_result(pair_file))

        diff = self.result_diff(patched_result)

        # logging.info(f"Difference between original and patched results: \n{json.dumps(diff, indent=4)}")
        return diff


class BenchResult:
    def __init__(self, result_path):
        self.result_path = result_path
        self.result_data = self.load_result()

    def load_result(self, result_path=None):
        if result_path is None:
            result_path = self.result_path
        if not os.path.exists(result_path):
            raise FileNotFoundError(f"Result file {result_path} does not exist.")

        with open(result_path, 'r', encoding='utf-8') as file:
            result_data = json.load(file)
        # logging.info(f"Loaded VulBench results from {result_path}")
        return result_data

    def get_result(self):
        return self.result_data

    def get_patch_diff(self, ori_path='', patch_path=''):
        logging.info(f"Analyzing patch results between {ori_path} and {patch_path}")
        if not ori_path or not patch_path:
            raise ValueError("Both original and patched result paths must be provided.")
        if not os.path.exists(ori_path) or not os.path.exists(patch_path):
            raise FileNotFoundError("One or both of the result files do not exist.")

        ori = PatchResult(ori_path)
        patch = PatchResult(patch_path)
        ori_result = ori.get_result()
        patch_result = patch.get_result()

        diff = ori.result_diff(patch_result, ori_result)
        # logging.info(f"Difference between original and patched results: \n{json.dumps(diff, indent=4)}")
        return diff

    def check_patch_valid(self, item_data=None):
        if item_data is None:
            return False

        patch_error = {
            "patch": {'git_apply': '', 'patch_p1': ''},
            "check": {'ori': '', 'patched': ''},
        }

        patch_result = item_data.get('patch_result', {"git_apply": '', "patch_p1": ''})
        patch_error['patch']['git_apply'] = patch_result.get('git_apply', '').strip() if patch_result.get(
            'git_apply') else ''
        patch_error['patch']['patch_p1'] = patch_result.get('patch_p1', '').strip() if patch_result.get(
            'patch_p1') else ''

        check_result = item_data.get('check_result', {"ori": '', "patched": ''})
        patch_error['check']['ori'] = check_result.get('ori', '').strip() if check_result.get('ori') else ''
        patch_error['check']['patched'] = check_result.get('patched', '').strip() if check_result.get('patched') else ''

        git_apply_msg = patch_error['patch']['git_apply']
        patch_p1_msg = patch_error['patch']['patch_p1']
        ori_check = patch_error['check']['ori']
        patched_check = patch_error['check']['patched']

        patch_valid = False

        if 'error:' not in git_apply_msg and patch_p1_msg == '':
            logging.info("Patch applied successfully, no errors found.")
            patch_valid = True
        elif ('Hunk' not in patch_p1_msg and
              'Reversed patch detected' not in patch_p1_msg and
              'malformed patch' not in patch_p1_msg):
            logging.info("Patch applied successfully with patch_p1.")
            patch_valid = True
        elif ori_check != patched_check:
            logging.info("After patching, the original and patched code differ.")
            patch_valid = True

        return patch_valid

    def check_patch_work(self, item_data=None):
        if item_data is None:
            return False

        ori_result = item_data.get('result_path', {}).get('ori', '')
        patched_result = item_data.get('result_path', {}).get('patched', '')
        if not ori_result or not patched_result:
            raise ValueError("Both original and patched result paths must be provided.")
        if not os.path.exists(ori_result) or not os.path.exists(patched_result):
            raise FileNotFoundError("One or both of the result files do not exist.")

        diff = self.get_patch_diff(ori_result, patched_result)
        if not diff:
            logging.info("No differences found between original and patched results.")
            return False

        important_keys = ['poc_output', 'poc_error', 'match_result']
        for ik in important_keys:
            if ik not in diff:
                continue

            local_value = diff[ik]['local']
            compared_value = diff[ik]['compared']

            if ik in ('poc_output', 'poc_error'):  # Return True if both output and error differ
                opposite_key = 'poc_error' if ik == 'poc_output' else 'poc_output'
                if diff.get(opposite_key) is None:
                    continue
                if (
                        local_value != compared_value and
                        diff[opposite_key]['local'] != diff[opposite_key]['compared']
                ):
                    logging.info(f"Patch works: {ik} differs between original and patched results.")
                    return True

            if ik == 'match_result':
                if local_value['is_dos']:  # For Denial of Service (DoS) situations
                    l_time = local_value['ontime']
                    c_time = compared_value['ontime']
                    if l_time == (not c_time):  # If match ontime is different, patch is working
                        return True
                    else:  # If running time is significantly longer, patch is working
                        rt_l = diff["running_time"]['local']
                        rt_c = diff["running_time"]['compared']
                        if max(rt_l, rt_c) > min(rt_c, rt_l) * 1.5:
                            return True
                else:  # For non-DoS situations, only check output and error
                    output_l = local_value['output']
                    output_c = compared_value['output']
                    error_l = local_value['error']
                    error_c = compared_value['error']
                    if output_l != output_c or error_l != error_c:
                        return True

        return False

    def analyze_result(self):

        valid_patches = []
        working_patches = []
        for item in self.result_data:
            if not isinstance(item, dict):
                logging.warning("Item in result data is not a dictionary, skipping.")
                continue
            if self.check_patch_valid(item):
                valid_patches.append(item)
            if self.check_patch_work(item):
                working_patches.append(item)

        logging.info(f"Valid patches found: {len(valid_patches)}")
        logging.info(f"Working patches found: {len(working_patches)}")

        for i, vp in enumerate(valid_patches):
            logging.info("-" * 20 + f" VALID PATCHES [{i + 1}] " + "-" * 20)
            logging.info(f"Patch valid: {vp['name']}")
            logging.info(json.dumps(vp, indent=4))
        for i, wp in enumerate(working_patches):
            logging.info("-" * 20 + f" WORKING PATCHES  [{i + 1}] " + "-" * 20)
            logging.info(f"Patch working: {wp['name']}")
            logging.info(json.dumps(wp, indent=4))
            logging.info(f"Patch diff for {wp['name']}:")
            pr = PatchResult(wp['result_path']['ori'])
            logging.info("-" * 20 + " PATCH RESULT " + "-" * 20)
            logging.info(json.dumps(pr.analyze_result(), indent=4))
