"""
Scan components for aare_bec_widgets.

The scan components module allows you to define custom components that can be used in your scans.
These components can be used to encapsulate reusable logic, interact with devices, or perform specific actions during the scan lifecycle.
"""

from bec_server.scan_server.scans.scan_components import ScanComponents


class AareBecWidgetsScanComponents(ScanComponents):
    """Scan components for aare_bec_widgets."""
