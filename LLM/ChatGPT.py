# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging
from utils import config
from openai import OpenAI
import time


class ChatGPT:
    """
    ChatGPT class to handle interactions with the OpenAI API.
    """

    def __init__(self, system_prompt=""):
        """
        Initialize the ChatGPT object with the provided API key.
        :param system_prompt: The system prompt to be used for the OpenAI API.
        """
        self.api_key = config.get("LLM").get("api_key", "")
        self.base_url = config.get("LLM").get("base_url", "https://api.openai.com/v1")
        self.model = config.get("LLM").get("model", "gpt-3.5-turbo")
        self.system_prompt = system_prompt if system_prompt else "You are a helpful assistant named VulBench, a tool for vulnerability repair benchmark."
        self.stream = config.get("LLM").get("stream", False)
        self.temperature = config.get("LLM").get("temperature", 0.6)
        self.top_p = config.get("LLM").get("top_p", 0.95)
        self.max_tokens = config.get("LLM").get("max_tokens", 8192)
        self.timeout = config.get("LLM").get("timeout", None)
        self.thinking = config.get("LLM").get("thinking", False)
        self.thinking_budget = config.get("LLM").get("thinking_budget", 4096)
        self.openai = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logging.info(f"OpenAI API initialized. Model: {self.model}, base_url: {self.base_url}")

    def chat(self, messages):
        """
        Send a chat message to the OpenAI API and return the response.
        :param messages: A list of messages to be sent to the OpenAI API.
        :return: The response from the OpenAI API.
        """
        try:
            args = {}
            if self.thinking:
                logging.info(f"Using thinking mode with budget: {self.thinking_budget}")
                args = {"extra_body": {"thinking_budget": self.thinking_budget}}
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=self.stream,
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                **args if self.thinking else {}
            )
            return response

        except Exception as e:
            if "rate limiting" in str(e).lower():
                logging.error(f"TPM limited error: {e}, waiting for 60 seconds.")
                time.sleep(60)
                return None
            else:
                logging.error(f"Error processing response: {e}")
                return None

    def get_response(self, prompt, history=None):
        """
        Get a response from the OpenAI API based on the provided prompt.
        :param prompt: The prompt to be sent to the OpenAI API.
        :param history: Optional history of previous messages to maintain context.
        :return: The response from the OpenAI API.
        """
        if history is None:
            messages = [{"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}]
        else:
            if history[0]["role"] == "system":
                history = history[1:]
            messages = [{"role": "system", "content": self.system_prompt}] + history + \
                       [{"role": "user", "content": prompt}]
        response = self.chat(messages)
        if response is None:
            logging.error("No response received from API")
            return None

        def stream_response(response):
            """
            Handle streaming response from OpenAI API.
            :param response: The streaming response from the OpenAI API.
            :return: The full text response.
            """
            full_text = ""
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_text += content
                        yield content
            return full_text if not self.stream else None

        try:
            if not self.stream:
                return response.choices[0].message.content
            else:
                return stream_response(response)
        # except TimeoutException as e:
        #     logging.error(f"Timeout error: {e}")
        #     sleep(2)
        #     return None
        except Exception as e:
            logging.error(f"Error processing response: {e}")
            return None
