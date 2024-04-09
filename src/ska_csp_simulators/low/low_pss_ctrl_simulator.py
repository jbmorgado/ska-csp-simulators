# -*- coding: utf-8 -*-
#
# This file is part of the CSP Simulators project
#
# GPL v3
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Simulator for the controller of a CSP sub-system
"""
from __future__ import annotations

from tango.server import run

from ska_csp_simulators.common.base_simulator_device import BaseSimulatorDevice

__all__ = ["LowPssCtrlSimulator", "main"]


class LowPssCtrlSimulator(BaseSimulatorDevice):
    """
    Base simulator device
    """

    # ---------------
    # General methods
    # ---------------

    # ----------
    # Attributes
    # ----------

    # --------
    # Commands
    # --------


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Motor module."""
    return run((LowPssCtrlSimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
