from collections import namedtuple
import os

import yaml

from .utils import perform_request

Config = namedtuple('Config', ["gitlab_base_url", "gitlab_project_id", "default_headers",
                               "gitlab_notes_header", "gitlab_internal_notes_header",
                               "gitlab_explicit_no_notes_header"])


def get_config(path):
    configuration = {}
    configuration.update(_load_defaults(path))
    return Config(**configuration)


def _load_defaults(path):
    with open(os.path.join(path, "defaults.yml")) as f:
        config = yaml.load(f)

    defaults = {}

    for key in config:
        if key == "gitlab_private_token":
            defaults["default_headers"] = {"private-token": config[key]}
        else:
            defaults[key] = config[key]

    return defaults
