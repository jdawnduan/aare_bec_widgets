"""
Pre-startup script for BEC client. This script is executed before the BEC client
is started. It can be used to add additional command line arguments.
"""

import os

from bec_lib.service_config import ServiceConfig

import aare_bec_widgets


def extend_command_line_args(parser):
    """
    Extend the command line arguments of the BEC client.
    """

    # parser.add_argument("--session", help="Session name", type=str, default="cSAXS")

    return parser

def get_config() -> ServiceConfig:
    """
    Create and return the ServiceConfig for the plugin repository
    """
    deployment_path = os.path.dirname(os.path.dirname(os.path.dirname(aare_bec_widgets.__file__)))
    files = os.listdir(deployment_path)
    if "bec_config.yaml" in files:
        return ServiceConfig(config_path=os.path.join(deployment_path, "bec_config.yaml"))
    else:
        return ServiceConfig(redis={"host": "localhost", "port": 6379})
