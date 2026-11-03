"""Simulated Aerotech sample stage with the production axis names: x/y/z (mm) and omega `u` (deg).

Why: the real `aerotech` (pxii_bec.devices.aerotech.Aerotech) is a REST device whose omega is the
sub-signal `u`. The omega widget targets `aerotech.u`, so the dev loop needs a device of the same shape;
ophyd_devices has no composite sim stage. Mirrors mx_bec's SimAerotechStage with the real axis names.
"""

from ophyd import Component as Cpt
from ophyd import Device
from ophyd_devices import SimPositioner


class SimAerotech(Device):
    x = Cpt(SimPositioner, name="x", limits=[-5, 5])
    y = Cpt(SimPositioner, name="y", limits=[-5, 5])
    z = Cpt(SimPositioner, name="z", limits=[-5, 5])
    # low == high disables SimPositioner's limit check: omega is a continuous rotation, +180 must work anywhere.
    # ponytail: update_frequency 10 Hz readback is enough for a demo; raise it if the GUI looks choppy.
    u = Cpt(SimPositioner, name="u", limits=[0, 0], update_frequency=10)
