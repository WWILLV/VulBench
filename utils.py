# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging
import yaml
import os
import time

vrb_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(vrb_dir, 'config.yaml')
log_dir = os.path.join(vrb_dir, 'Logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
if not os.path.exists(config_path):
    raise FileNotFoundError("Could not find config.yaml file. Please check the path.")


def load_config():
    """
    Load the configuration file and return the configuration dictionary.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        vrb_config = yaml.safe_load(f)
    return vrb_config


def setup_logging():
    """
    Set up logging configuration.
    """
    log_config = load_config().get("Log", {"level": "", "format": ""})
    user_level = log_config.get("level", "").upper().strip()
    if user_level != "":
        if user_level == "DEBUG":
            user_level = logging.DEBUG
        elif user_level == "INFO":
            user_level = logging.INFO
        elif user_level == "WARNING":
            user_level = logging.WARNING
        elif user_level == "ERROR":
            user_level = logging.ERROR
        elif user_level == "CRITICAL":
            user_level = logging.CRITICAL
        else:
            user_level = logging.INFO

    user_format = log_config.get("format", "").strip()
    user_format = user_format if user_format != "" else '%(asctime)s\t%(name)s\t%(levelname)s\t[%(filename)s:%(lineno)d]\t%(message)s'

    logging.basicConfig(
        level=None if user_level == "" else user_level,
        format=user_format,
        handlers=[
            logging.FileHandler(
                os.path.join(log_dir, f"vrb_{time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))}.log")),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    # logger.info("VRBench initialized.")
    # logger.warning("test warning")
    # logger.error("test error")
    # logger.critical("test critical")
    # logger.debug("test debug")
    return logger


def clean_logs(delete_days=7, delete_all=False):
    """
    Clean up log files older than the specified number of days.
    :param delete_days: Number of days to keep logs.
    :param delete_all: If True, delete all log files.
    """
    now = time.time()
    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)
        if delete_all:
            if logging.getLogger().hasHandlers():
                logging.getLogger().handlers[0].close()
                logging.getLogger().removeHandler(logging.getLogger().handlers[0])
            os.remove(file_path)
            print(f"Deleted log file: {file_path}")
            continue
        if os.path.isfile(file_path) and (now - os.path.getmtime(file_path)) > delete_days * 86400:
            os.remove(file_path)
            print(f"Deleted log file: {file_path}")


def get_workspace():
    space_path = load_config().get("workspace", os.path.join(__file__, 'workspace'))
    if not os.path.exists(space_path):
        os.makedirs(space_path)
    return space_path


config = load_config()
if config is None:
    raise ValueError("Config file is not found or invalid.")

if not logging.getLogger().hasHandlers():
    setup_logging()
