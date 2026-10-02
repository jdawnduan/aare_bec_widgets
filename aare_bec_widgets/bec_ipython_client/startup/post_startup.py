"""
Post startup script for the BEC client. This script is executed after the
IPython shell is started. It is used to load the beamline specific
information and to setup the prompts.

The script is executed in the global namespace of the IPython shell. This
means that all variables defined here are available in the shell.

While command-line arguments have to be set in the pre-startup script, the
post-startup script can be used to load beamline specific information and
to setup the prompts.

    from bec_lib.logger import bec_logger

    logger = bec_logger.logger

    # pylint: disable=import-error
    _args = _main_dict["args"]

    _session_name = "cSAXS"
    if _args.session.lower() == "lamni":
        from csaxs_bec.bec_ipython_client.plugins.cSAXS import *
        from csaxs_bec.bec_ipython_client.plugins.LamNI import *

        _session_name = "LamNI"
        lamni = LamNI(bec)
        logger.success("LamNI session loaded.")

    elif _args.session.lower() == "csaxs":
        print("Loading cSAXS session")
        from csaxs_bec.bec_ipython_client.plugins.cSAXS import *

        logger.success("cSAXS session loaded.")
"""

# pylint: disable=invalid-name, unused-import, import-error, undefined-variable, unused-variable, unused-argument, no-name-in-module
