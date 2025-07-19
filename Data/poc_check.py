# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging
import os
import PatchesAnalysis
import requests
import re
from bs4 import BeautifulSoup
from Driver.PageAnalysis import PageAnalysis

# filename = 'clear_poc.json'
# filename = 'patches_poc.json'
filename = 'poc_LLM_dsv324_3.json'
patches_path = os.path.join(os.path.dirname(__file__), filename)
pa = PatchesAnalysis.PatchesAnalysis(patches_path=patches_path)

all_patches = pa.get_patches()

def get_references(cve_id):
    """
    Get the references of a CVE ID from NVD.
    :param cve_id: CVE ID
    :return: list of references
    """
    if not cve_id.startswith("CVE-"):
        cve_id = "CVE-" + cve_id
    url = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    references = []
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', class_='table table-striped table-condensed table-bordered detail-table')
    if table:
        tbody = table.find('tbody')
        if tbody:
            references = [a['href'] for a in tbody.find_all('a', href=True)]
    return references

def url_reduplicate(urls):
    """
    Remove duplicate URLs from a list.
    :param urls: list of URLs
    :return: list of unique URLs
    """
    unique_urls = []
    for url in urls:
        if url not in unique_urls:
            unique_urls.append(url)
    return unique_urls

def update_poc(all_patches):
    """
    Update the poc of all patches.
    :param all_patches:
    :return: updated patches
    """
    count = 0
    for patch in all_patches:
        for issues in patch['security_issues']:
            count += 1
            urls = issues["poc"]["url"]
            if len(urls)==0:
                print("CVE Reference not exists, try to get it from NVD")
                urls = get_references(issues['public_id'])
                print(urls)
            urls = url_reduplicate(urls)
            issues["poc"]={
                "exists": False,
                "type": "null",
                "url": urls
            }

    print(f"Total number of security issues: {count}")
    return all_patches

def get_clear_poc(all_patches):
    """
    Get the clear poc of all patches.
    :param all_patches:
    :return: clear poc
    """
    cps = []
    regex1 = re.compile(r"^(http|https)://github.com/.*/commit/.*") # GitHub commit is useless for poc link
    regex2 = re.compile(r"^(http|https)://www.securityfocus.com/.*") # Lost DNS
    for patch in all_patches:
        cp = {
            "library_name": patch['library_name'],
            "security_issues": [
                {
                    "public_id": issues['public_id'],
                    "poc": {
                        "exists": issues['poc']['exists'],
                        "type": issues['poc']['type'],
                        "url": [url for url in issues['poc']['url'] if not (regex1.match(url) or regex2.match(url))],
                    }
                } for issues in patch['security_issues']
            ]
        }
        cps.append(cp)

    return cps

def get_nvd(all_patches):
    """
    Get the NVD links of all patches.
    :param all_patches:
    :return: nvd_list
    """
    index = 0
    nvd_list = []

    while True:
        print("-"*40)
        current_patch = all_patches[index]
        print(f"[{index}]{current_patch['library_name']}: {len(current_patch['security_issues'])}")
        for issues in current_patch['security_issues']:
            cve = issues['public_id']
            if not cve.startswith("CVE-"):
                cve = "CVE-" + cve
            nvd = f"https://nvd.nist.gov/vuln/detail/{cve}"
            nvd_list.append(nvd)
            print(f"{cve} : {nvd}")
            # if issues["poc"]["exists"]:
            #     continue
            # print("poc not exists, please check it")

        index += 1
        if index >= len(all_patches):
            break

    return nvd_list


# all_patches = update_poc(all_patches)
# new_path = os.path.join(os.path.dirname(__file__), 'patches_poc.json')
# pa.save_patches(patches=all_patches, new_path=new_path)
#
# cps = get_clear_poc(all_patches)
# new_path = os.path.join(os.path.dirname(__file__), 'clear_poc.json')
# pa.save_patches(patches=cps, new_path=new_path)

def llm_check(all_patches):

    def url_decision(urls):
        """
        Decide whether the URL is a poc link or not.
        :param urls: list of URLs
        """
        decision = []
        for url in urls:
            if url.startswith("(LLM:unknown)"):
                # Unknown, re-check it
                url = url.replace("(LLM:unknown) ", "")
            if url.startswith("(LLM:"):
                # Already checked by LLM, skip it
                llm_decision,ori_url  = url.split(" ")
                llm_decision = llm_decision.replace("(LLM:", "").replace(")", "")
                logging.info(f"LLM Already Decision: {llm_decision} for {ori_url}")
                decision.append({"url": url, "type": llm_decision})
                continue
            page_analysis = PageAnalysis()
            pc = page_analysis.poclink_classification(url).strip().lower()
            if pc in ["executable", "description", "brief"]:
                ds = pc
            else:
                ds = "unknown"
            decision.append({"url": f"(LLM:{ds}) {url}", "type": ds})
        return decision

    for patch in all_patches:
        # try:
        #     if patch['security_issues'][0]['poc']['type'] != 'null':
        #         continue
        # except Exception as e:
        #     logging.error(f"LLM Check Error: {e}")

        for issue in patch['security_issues']:
            # if issue['poc']['exists']:
            #     continue
            urls = issue['poc']['url']
            cve = issue['public_id']
            if len(urls) == 0:
                print(f"{cve} Reference not exists.")
                logging.warning(f"{cve} Reference not exists.")
                continue
            if urls[0].startswith("http"):
                # URLs are checked by human, skip it
                continue

            logging.info(f"LLM Checking {cve} poc link, total {len(urls)} links")

            ud = url_decision(urls)

            all_type = set()
            for u in ud:
                all_type.add(u['type'])
            if 'executable' in all_type:
                poc_type = 'executable'
            elif 'description' in all_type:
                poc_type = 'description'
            elif 'brief' in all_type:
                poc_type = 'brief'
            else:
                poc_type = 'null'

            poc_exist = True if poc_type in ['executable','description'] else False

            issue['poc'] = {
                "exists": poc_exist,
                "type": poc_type,
                "url": [u['url'] for u in ud]
            }

            # Save patches every issue update
            # new_path = os.path.join(os.path.dirname(__file__), 'poc_LLM_checked.json')
            # new_path = os.path.join(os.path.dirname(__file__), 'poc_LLM_examine.json')
            new_path = os.path.join(os.path.dirname(__file__), 'poc_LLM_dsv324_4.json')
            pa.save_patches(patches=all_patches, new_path=new_path)

    return all_patches

def llm_examine(all_patches):
    """
    Examine the poc of all patches.
    :param all_patches:
    :return: examined patches
    """
    pass


lc = llm_check(all_patches)
# new_path = os.path.join(os.path.dirname(__file__), 'poc_LLM_checked.json')
# pa.save_patches(patches=lc, new_path=new_path)