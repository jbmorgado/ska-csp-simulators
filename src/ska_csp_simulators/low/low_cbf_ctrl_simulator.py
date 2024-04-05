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

from ska_control_model import ResultCode
from tango import DebugIt, DevVarLongStringArray
from tango.server import command, run

from ska_csp_simulators.common.base_simulator_device import BaseSimulatorDevice

__all__ = ["LowCbfCtrlSimulator", "main"]

DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class LowCbfCtrlSimulator(BaseSimulatorDevice):
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

    @command(
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def On(self: LowCbfCtrlSimulator) -> DevVarLongStringArray:
        message = "Ignored ON, controller does not have hardware"
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