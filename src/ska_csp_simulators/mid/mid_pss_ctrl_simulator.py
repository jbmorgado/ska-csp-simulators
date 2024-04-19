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

from ska_control_model import HealthState, ResultCode
from tango import DevState
from tango.server import run

from ska_csp_simulators.common.base_simulator_device import BaseSimulatorDevice

__all__ = ["MidPssCtrlSimulator", "main"]

DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class MidPssCtrlSimulator(BaseSimulatorDevice):
    """
    Base simulator device
    """

    def init_device(self):
        """Initialises the attributes and properties of the device."""
        super().init_device()
        self._health_state = HealthState.OK
        self.set_state(DevState.OFF)

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
    """Main function of the device module."""
    return run((MidPssCtrlSimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
