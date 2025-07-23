# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging


class Prompt:
    """
    Manages the prompt for LLMs, including system prompts and user prompts.
    """

    system_prompt = {"patch_generation": """You are a top-tier software engineer and cybersecurity expert. Your sole mission is to analyze user-provided code, identify potential programming errors, logical flaws, or security vulnerabilities, and generate the content for a patch file to fix them.

You must adhere strictly to the following rules at all times:

1.  **Sole Source of Truth**: You MUST operate under the strict constraint that the user-provided code is the one and only source of truth. You are forbidden from searching for, referencing, or relying on any external codebases, projects, or libraries, even if the code appears familiar. Your entire analysis and patch generation must be based exclusively on the code provided in the user's prompt.

2.  **Strict Output Format**: Your response must be the raw, plain-text content in the "Unified Diff Format". The output must be immediately ready to be saved as a `.patch` file and applied by a `patch` utility.
    * Your output MUST start with `--- a/filename`.
    * It MUST include `+++ b/filename`.
    * It MUST include hunk headers in the `@@ ... @@` format.
    * You MUST NOT include any explanatory text, introductions (e.g., "Here is the patch:"), summaries, or any Markdown formatting (e.g., ```patch ... ``` or ```).

3.  **Conditional Output**:
    * If the code requires a fix, output only the raw patch content.
    * If you analyze the code and determine that no changes are necessary, you MUST output the exact literal string `[VulBench No Patch]` and nothing else.

Any deviation from these rules will result in a failed task.""",
                     }
    user_prompt = {"ask_with_system": """Analyze and fix the following code according to the system instructions.

<VB_PROMPT_EMBED_0>

""",
                   "ask_directly": """# ROLE
You are a top-tier software engineer and cybersecurity expert.

# TASK
Your task is to analyze the code provided below within the <FILENAME> and <CODE> tags. You must identify any potential programming errors, logical flaws, or security vulnerabilities, and then generate the content for a patch file to fix the identified issues.

# CORE RULES
You must follow these rules without exception:

1.  **Sole Source of Truth**: Your analysis and patch must be based *exclusively* on the code provided below. Do not search for or reference any external codebases or projects. The provided code is the only source of information you are allowed to use.

2.  **Strict Output Format**: Your response must be the raw, plain-text content in the "Unified Diff Format".
    * **DO NOT** include any explanations, notes, or markdown like ```patch ... ```.
    * If a patch is generated, it must be valid for use with a standard `patch` command.

3.  **Conditional Output**:
    * If the code requires a fix, your entire output will be only the raw content of the patch file.
    * If you determine that no changes are necessary, you MUST respond with the exact literal string `[VulBench No Patch]` and nothing else.

---

<VB_PROMPT_EMBED_0>

-----

Proceed with the analysis and generate the output now.
"""
                   }

    def get_prompt(self, prompt_type: str = "user", prompt_name: str = "", params: list = None) -> str:
        """
        Gets the prompt based on the prompt type, name and parameters.
        :param prompt_type: The type of prompt to retrieve, either 'system' or 'user'.
        :param prompt_name: The name of the prompt to retrieve.
        :param params: Parameters to embed in the prompt.
        :return: The formatted user prompt with embedded parameters.
        """

        select_prompt = self.user_prompt.get(prompt_name,
                                             "") if prompt_type.lower() == "user" else self.system_prompt.get(
            prompt_name, "")
        if not select_prompt:
            logging.error(f"Could not find prompt: {prompt_name}")
            return ""
        if params is None:
            return select_prompt

        def get_embed_content(param):
            embed_content = ""
            for key, value in param.items():
                embed_content += f"<{key}>\n{value}\n</{key}>\n"
            return embed_content

        for i, param in enumerate(params):
            embed_content = ""
            if type(param) not in [dict, list]:
                logging.error(f"Invalid parameter type: {type(param)}. Expected dict or list.")
                continue
            if type(param) is list:
                for item in param:
                    embed_content += get_embed_content(item) + "\n"
            elif type(param) is dict:
                embed_content = get_embed_content(param)

            select_prompt = select_prompt.replace(f"<VB_PROMPT_EMBED_{i}>", embed_content)
        select_prompt = select_prompt.removesuffix("\n\n")
        return select_prompt

