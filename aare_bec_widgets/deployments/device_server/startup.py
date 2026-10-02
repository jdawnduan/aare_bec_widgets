import os


def setup_epics_ca():
    # os.environ["EPICS_CA_AUTO_ADDR_LIST"] = "NO"
    # os.environ["EPICS_CA_ADDR_LIST"] = "129.129.122.255 sls-x12sa-cagw.psi.ch:5836"
    os.environ["PYTHONIOENCODING"] = "latin1"


def run():
    setup_epics_ca()
