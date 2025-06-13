# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging
import utils
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service

class Browser:
    driver = None
    config = utils.config

    def __init__(self):
        # Load configuration
        browser_config = self.config.get("Browser")
        if browser_config is None:
            raise ValueError("Config file is not found or invalid.")

        # Initialize WebDriver
        options = webdriver.ChromeOptions()
        if browser_config.get("headless", False):
            options.add_argument("--headless")
        if browser_config.get("chrome_options") is not None:
            for option in browser_config["chrome_options"]:
                options.add_argument(option)
        if browser_config.get("user_agent","") != "":
            options.add_argument(f"user-agent={browser_config['user_agent']}")
        if browser_config.get("use_proxy", False):
            proxy = browser_config.get("proxy_host", "")
            if proxy != "":
                options.add_argument(f"--proxy-server={proxy}")
        if browser_config.get("unhandledPromptBehavior","") != "":
            options.set_capability('unhandledPromptBehavior', browser_config["unhandledPromptBehavior"])

        # hide the automation flag
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")

        if browser_config.get("remote", False):
            # Set up the remote WebDriver if specified
            remote_url = browser_config.get("remote_url", "http://127.0.0.1:4444/wd/hub")
            self.driver = webdriver.Remote(command_executor=remote_url,options=options)
        else:
            if browser_config.get("specify", False):
                # Specify the path to the Chrome binary and driver
                chrome_driver_path = browser_config["driver_path"]
                chrome_binary_path = browser_config["chrome_path"]
                options.binary_location = chrome_binary_path
                service = Service(executable_path=chrome_driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(60) # Set page load timeout to 60 seconds

    def get_driver(self):
        """
        Get the WebDriver instance.
        :return: WebDriver instance.
        """
        if self.driver is None:
            raise ValueError("WebDriver is not initialized.")
        return self.driver

    def quit(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        # self.quit()
        pass


    def get_document_from_url(self, url):
        try:
            # open the URL
            self.driver.get(url)
            logging.info(f"Visited {url}")

            # wait for the page to load completely
            WebDriverWait(self.driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Get document content of the page (i.e., the HTML)
            document = self.driver.execute_script("return document.documentElement.outerHTML;")
            return document
        finally:
            pass
