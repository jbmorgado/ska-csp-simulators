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
from tango import DebugIt, DevState, DevVarLongStringArray
from tango.server import command, run

from ska_csp_simulators.common.base_simulator_device import BaseSimulatorDevice

__all__ = ["LowCbfCtrlSimulator", "main"]

DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class LowCbfCtrlSimulator(BaseSimulatorDevice):
    """
    Base simulator device
    """

    def init_device(self):
        """Initialises the attributes and properties of the Motor."""
        super().init_device()
        self._health_state = HealthState.UNKNOWN

    # ---------------
    # General methods
    # ---------------
    def set_communication(
        self: LowCbfCtrlSimulator,
        end_state,
        end_health,
        connecting: bool,
    ):
        """
        Override the behavior of the method to set different
        values fot the State and healthState of the device.
        """
        if connecting:
            super().set_communication(
                DevState.ON, HealthState.UNKNOWN, connecting
            )

    # ----------
    # Attributes
    # ----------

    # --------
    # Commands
    # --------

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def On(self: LowCbfCtrlSimulator) -> DevVarLongStringArray:
        message = "Ignored ON, controller does not have hardware"
        self.logger.error(message)
        return [[ResultCode.REJECTED], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Off(self: LowCbfCtrlSimulator) -> DevVarLongStringArray:
        message = "Ignored OFF, controller does not have hardware"
        self.logger.error(message)
        return [[ResultCode.REJECTED], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Standby(self: LowCbfCtrlSimulator) -> DevVarLongStringArray:
        message = "Ignored STANDBY, controller does not have hardware"
        self.logger.error(message)
        return [[ResultCode.REJECTED], [message]]

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def Reset(self: LowCbfCtrlSimulator) -> DevVarLongStringArray:
        message = "Ignored RESET, controller does not have hardware"
        self.logger.error(message)
        return [[ResultCode.REJECTED], [message]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Motor module."""
    return run((LowCbfCtrlSimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
