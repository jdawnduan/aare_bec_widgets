"""
Scan modifier plugin for aare_bec_widgets.

The scan modifier allows you to modify the scan lifecycle and run custom actions before or after the scan hook or replace the scan hook entirely.
Note that the scan_modifier module must be registered as a plugin in the pyproject.toml file for it to be recognized by the BEC framework and that
there can only be one scan_modifier plugin registered at a time. If you need to run multiple scan modifiers, you can create a single scan
modifier plugin that runs multiple actions in sequence with conditional logic to determine which actions to run based on the scan context.
"""

from bec_server.scan_server.scans.scan_modifier import ScanModifier, scan_hook_impl


class AareBecWidgetsScanModifier(ScanModifier):
    """
    Scan modifier for aare_bec_widgets.
    
    By inheriting from the ScanModifier base class, you get access to currently running scan (self.scan), the devices (self.dev), the scan info (self.scan_info),
    the scan components (self.components) and the scan actions (self.actions).
    """

    def __init__(self, **kwargs):
        """Initialize the scan modifier."""
        super().__init__(**kwargs)

    # Example of running code before the scan stage for a specific scan
    # @scan_hook_impl("stage", "before")
    # def before_stage(self):
    #     """Run before the stage hook."""
    #     self.actions.send_client_info("Custom stage logic executed by ScanModifier.")
    #     if self.scan_info.scan_name == "example_scan":
    #         self.dev.samx.set(20)

    
