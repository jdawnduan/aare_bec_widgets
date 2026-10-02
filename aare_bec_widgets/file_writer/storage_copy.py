"""
Beamline storage-copy hook for aare_bec_widgets.

Use this module to handle ``bec.beamline_storage_copy(...)`` requests with
beamline-specific file transfer logic.

The plugin_storage_copy function is commented out by default. Uncomment and implement it to handle
beamline-specific storage copy operations. The function should accept the source file path,
a scope identifier, the active BEC account, and an optional subdirectory for the destination. It should
perform the necessary checks and copy the file to the appropriate location based on the provided scope.
The subdirectory, if provided, has already been sanitized to ensure it is safe for use in file paths.
"""

# import os
# import shutil

# from bec_lib.logger import bec_logger

# logger = bec_logger.logger


# def plugin_storage_copy(
#     source_file: str, scope: str, active_account: str, subdir: str | None = None
# ) -> None:
#     """
#     Run a beamline-defined storage copy operation.

#     Args:
#         source_file: Source file that should be copied.
#         scope: Beamline-defined copy scope identifier.
#         active_account: Active BEC account, if one is available.
#         subdir: Optional sanitized relative destination subdirectory.
#     """
#     supported_file_extensions = [
#         ".h5",
#         ".txt",
#         ".csv",
#         ".log",
#         ".json",
#         ".png",
#         ".jpg",
#         ".jpeg",
#         ".tiff",
#         ".yaml",
#         ".yml",
#     ]
#     if not any(source_file.endswith(ext) for ext in supported_file_extensions):
#         logger.error(
#             f"Unsupported file type for '{source_file}'. Supported extensions: "
#             f"{supported_file_extensions}"
#         )
#         return

#     # Example storage mapping. Replace this with beamline-specific scopes and paths.
#     storage_locations = {"alignment": f"/sls/x99sa/data/p12345/raw/bec/alignment/{active_account}/"}
#     if scope not in storage_locations:
#         logger.error(
#             f"Received unknown scope '{scope}'. Available scopes: {list(storage_locations.keys())}"
#         )
#         return

#     if not os.path.isfile(source_file):
#         logger.error(f"File '{source_file}' does not exist or is not reachable.")
#         return

#     destination_dir = storage_locations[scope]
#     if subdir:
#         destination_dir = os.path.join(destination_dir, subdir)
#     os.makedirs(destination_dir, exist_ok=True)
#     destination_file = os.path.join(destination_dir, os.path.basename(source_file))

#     try:
#         shutil.copy(source_file, destination_file)
#         logger.info(f"Copied '{source_file}' to '{destination_file}'")
#     except Exception as exc:
#         logger.error(f"Failed to copy '{source_file}' to '{destination_file}': {exc}")
