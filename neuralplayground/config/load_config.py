import os
import shutil

import yaml

import neuralplayground

from .plot_config import PlotsConfig


def _load_config(config_path: str = None):
    """Load config file

    Parameters
    ----------
    config_path: str
        Path to the config file

    Returns
    -------
    config: NPGConfig
        Config object
    """
    with open(config_path, "r") as file:
        CONFIG_FILE_YAML = yaml.safe_load(file)
        print(config_path)
    PLOT_CONFIG = PlotsConfig(CONFIG_FILE_YAML["plot_config"])
    return PLOT_CONFIG


def generate_config_file(dir_path: str = None):
    """Generate config file

    Parameters
    ----------
    dir_path: str
        Path to the new config file, use current path if dir_path is None

    """
    if dir_path is None:
        dir_path = "./"

    new_config_file_path = os.path.join(dir_path, "config_params.yaml")

    shutil.copyfile(os.path.join(neuralplayground.__path__[0], "config", "default_config.yaml"), new_config_file_path)
