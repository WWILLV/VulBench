# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import os
import json
import copy

class PatchesAnalysis:

    def __init__(self, patches_path=''):
        if patches_path == '':
            self.patches_path = os.path.join(os.path.dirname(__file__), 'filtered_patches.json')
        else:
            self.patches_path = patches_path
        if not os.path.exists(patches_path):
            raise FileNotFoundError(f'File {patches_path} not found')

    def get_patches(self, patches_path=''):
        """
        Get patches from json file
        :param patches_path: path to the patches file
        :return: list of patches
        """
        if patches_path == '':
            patches_path = self.patches_path
        if not os.path.exists(patches_path):
            print(f'Error: {patches_path} not exists')
            raise FileNotFoundError(f'{patches_path} not exists')
        if patches_path.endswith('.json'):
            with open(patches_path, 'r') as f:
                data = json.load(f)
            return data
        else:
            print(f'Error: {self.patches_path} not a json file')
            raise ValueError(f'{self.patches_path} not a json file')

    def commits_count(self, patches=None):
        """
        Count the number of commits in patches
        :type patches: list of patches
        :return: number of commits
        """
        count = 0
        if patches is None:
            patches = self.get_patches()
        for patch in patches:
            for issues in patch['security_issues']:
                count += len(issues['patch_commits'])
        return count

    def commits_derepelicate(self, patches=None):
        """
        Remove duplicate patche_commits
    :param patches: list of patches
        :return: list of unique patches
        """
        unique_patches = []  # 用于存储去重后的补丁列表
        if patches is None:
            patches = self.get_patches()
        for patch in patches:  # 遍历每个补丁
            for issues in patch['security_issues']:  # 遍历补丁中的每个安全问题
                issues['patch_commits'].sort(key=lambda commit: commit['commit_hash'],
                                             reverse=True)  # 对每个安全问题中的提交进行逆序排序 （保留最长hash）
            new_patch = copy.deepcopy(patch)  # 深拷贝当前补丁，避免修改原始数据
            new_patch['security_issues'] = []  # 初始化新的安全问题列表
            for issues in patch['security_issues']:  # 遍历补丁中的每个安全问题
                seen_hashes = set()  # 用于存储已见过的提交哈希值
                unique_commits = []  # 用于存储去重后的提交列表

                for commit in issues['patch_commits']:  # 遍历安全问题中的每个提交
                    commit_hash = commit['commit_hash']  # 获取提交的哈希值
                    # 检查当前提交哈希是否与已见过的哈希有前缀匹配
                    if not any(commit_hash.startswith(h) or h.startswith(commit_hash) for h in seen_hashes):
                        seen_hashes.add(commit_hash)  # 将当前哈希值添加到已见集合
                        unique_commits.append(commit)  # 将当前提交添加到去重后的提交列表

                new_issues = copy.deepcopy(issues)  # 深拷贝当前安全问题
                new_issues['patch_commits'] = unique_commits  # 替换为去重后的提交列表
                new_patch['security_issues'].append(new_issues)  # 将新的安全问题添加到补丁中
            unique_patches.append(new_patch)  # 将去重后的补丁添加到结果列表
        return unique_patches  # 返回去重后的补丁列表

    def save_patches(self, patches, new_path=''):
        """
        Save patches to json file
        :param patches: list of patches
        :param new_path: new path to save the patches
        :return: None
        """
        if new_path == '':
            new_path = self.patches_path
        with open(new_path, 'w') as f:
            json.dump(patches, f, indent=4)

    def select_patches_by_commit(self, patches=None, commit_hash=''):
        """
        Select patches based on a commit hash prefix
        :param patches: list of patches
        :param commit_hash: commit hash prefix to filter patches
        :return: list of selected patches
        """
        if patches is None:
            patches = self.get_patches()
        selected_patches = []
        commit_hash = commit_hash.lower().strip()
        for patch in patches:
            for issues in patch['security_issues']:
                for commit in issues['patch_commits']:
                    if commit['commit_hash'].lower().startswith(commit_hash):
                        selected_patches.append(patch)
                        break
                else:
                    continue
                break
        return selected_patches

    def select_patches_by_library_name(self, patches=None, library_name=''):
        """
        Select patches based on a library name
        :param patches: list of patches
        :param library_name: library name to filter patches
        :return: list of selected patches
        """
        if patches is None:
            patches = self.get_patches()
        selected_patches = []
        library_name = library_name.lower().strip()
        for patch in patches:
            if patch['library_name'].lower() == library_name:
                selected_patches.append(patch)
        return selected_patches

    def select_patches_by_public_id(self, patches=None, public_id=''):
        """
        Select patches based on a public ID
        :param patches: list of patches
        :param public_id: public ID to filter patches
        :return: list of selected patches
        """
        if patches is None:
            patches = self.get_patches()
        selected_patches = []
        public_id = public_id.lower().strip()
        for patch in patches:
            for issues in patch['security_issues']:
                if issues['public_id'].lower() == public_id:
                    selected_patches.append(patch)
        return selected_patches

    def get_all_library_names(self, patches=None):
        """
        Get all library names from patches
        :param patches: list of patches
        :return: list of library names
        """
        if patches is None:
            patches = self.get_patches()
        library_names = set()
        for patch in patches:
            library_names.add(patch['library_name'])
        return list(library_names)

    def get_all_public_ids(self, patches=None):
        """
        Get all public IDs from patches
        :param patches: list of patches
        :return: list of public IDs
        """
        if patches is None:
            patches = self.get_patches()
        public_ids = set()
        for patch in patches:
            for issues in patch['security_issues']:
                public_ids.add(issues['public_id'])
        return list(public_ids)

if __name__ == '__main__':
    patches_path = os.path.join(os.path.dirname(__file__), 'unique_filtered_patches.json')
    # patches_path = os.path.join(os.path.dirname(__file__), 'filtered_patches.json')
    pa = PatchesAnalysis(patches_path)
    # patches = pa.get_patches()
    # print(f'Loaded {len(patches)} patches from {patches_path}')
    # print(f'Number of commits: {pa.commits_count()}')
    # unique_patches = pa.commits_derepelicate()
    # print(f'Number of commits (deduplication): {pa.commits_count(unique_patches)}')
    commit_count = pa.commits_count()
    print(f'Number of commits: {commit_count}')
    allname = sorted(pa.get_all_library_names())
    print(f"Number of unique library names: {len(allname)}")
    # print(allname)
    allid = sorted(pa.get_all_public_ids())
    print(f"Number of unique public IDs: {len(allid)}")
    # print(allid)

