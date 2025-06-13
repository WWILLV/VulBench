# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging
from utils import config
from Driver.Browser import Browser
from LLM.ChatGPT import ChatGPT
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from html2text import html2text

class PageAnalysis:
    def __init__(self):
        self.driver = Browser().get_driver()
        self.page_source = None
        self.bot = None

    def access(self, url):
        """
        Access a webpage using the WebDriver.
        :param url: The URL of the webpage to access.
        """
        try:
            self.driver.get(url)

            # wait for the page to load completely
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            self.page_source = self.driver.page_source
            logging.info(f"Accessed URL: {url}")
        except Exception as e:
            logging.error(f"Error accessing URL {url}: {e}")
            self.page_source = None
        return self.page_source

    def xpath(self, xpath):
        """
        Find an element on the webpage using XPath.
        :param xpath: The XPath of the element to find.
        :return: The found element.
        """
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            logging.info(f"Element found with XPath: {xpath}")
            return element
        except Exception as e:
            logging.error(f"Error finding element with XPath {xpath} in {self.driver.current_url}: {e}")
            return None

    def get_all_text(self):
        """
        Get all text from the webpage.
        :return: The text content of the webpage.
        """
        try:
            body = self.xpath("//body")
            if body is None:
                logging.error("Body element not found.")
                return None
            return body.text
        except Exception as e:
            logging.error(f"Error getting all text: {e}")
            return None

    def get_pretty_text(self):
        """
        Get the prettified text from the webpage.
        :return: The prettified text content of the webpage.
        """
        try:
            body = self.xpath("//body")
            if body is None:
                logging.error("Body element not found.")
                return None
            html = body.get_attribute('outerHTML')
            return html2text(html)
        except Exception as e:
            logging.error(f"Error getting pretty text: {e}")
            return None

    def poclink_classification(self, url):
        """
        Classify the type of POC link based on the URL.
        :param url: The URL to classify.
        :return: The classification result.
        """
        self.access(url)
        text = self.get_pretty_text()
        if text is None:
            logging.error(f"Failed to retrieve text from the webpage: {url}")
            return "unknown"
        system_prompt = """
你是一位精通网络安全和漏洞分析的专家，任务是根据用户提供的 Markdown 格式的漏洞信息，判断其中是否包含关于漏洞利用的 PoC（Proof of Concept）内容。你的目标是对内容进行严谨、专业的分析，并根据以下标准将 Markdown 信息准确归类为三种类型中的一种：
executable：信息中包含完整、可直接运行的 PoC 代码，能够直接验证漏洞；
description：信息中不包含完整的可运行代码，但提供了漏洞利用方法的自然语言描述和部分 PoC 代码片段，具备构造完整 PoC 的依据；
brief：信息仅包含漏洞的简要描述，未涉及任何利用细节或代码内容。
你必须严格按照标准分类，仅返回一个最合适的分类词（即 executable、description 或 brief）。请勿输出其他解释性内容或附加说明。
""".strip()
        prompt = """
请阅读以下根据漏洞报告页面整理而成的 Markdown 信息，并判断其是否包含关于漏洞利用的 PoC（Proof of Concept）相关内容。根据内容，将其归类为以下三类之一，并仅返回对应的分类词（executable、description 或 brief）：
1. executable：包含可直接运行的完整 PoC 代码，能够用于验证漏洞是否存在；
2. description：不包含完整的可运行代码，但提供了漏洞利用的自然语言描述和部分代码片段，足以辅助构造出完整的 PoC；
3. brief：仅包含漏洞的简要描述，不涉及任何漏洞利用方法或相关代码细节。
请仔细阅读 Markdown 内容，只能选择最符合的一个分类，并确保你的判断严格依据上述标准。最终，请仅回复对应的分类词，不要添加任何其他内容。
以下是 Markdown 信息：""".strip()+f"\n{text}"

        print(prompt)

        if self.bot is None:
            self.bot = ChatGPT(system_prompt=system_prompt)
        response = ''
        if config.get("LLM").get("stream", False):
            for chunk in self.bot.get_response(prompt=prompt):
                response += chunk
        else:
            response = self.bot.get_response(prompt=prompt)
        if response is None or response == '':
            logging.error(f"Failed to get response from LLM for URL: {url}")
            return "unknown"
        if response.strip().lower() not in ["executable", "description", "brief"]:
            logging.error(f"Unexpected response from LLM: {response}")
            return "unknown"
        logging.info(f"Response from LLM: {response}")
        return response



if __name__ == '__main__':
    page_analysis = PageAnalysis()
    pc = page_analysis.poclink_classification("https://github.com/Netflix/lemur/security/advisories/GHSA-5fqv-mpj8-h7gm")
    print(pc)
