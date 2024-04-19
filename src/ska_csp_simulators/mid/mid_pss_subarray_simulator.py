# -*- coding: utf-8 -*-
#
# This file is part of the CSP Simulators project
#
# GPL v3
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Simulator for the Mid subarray of a CSP sub-system
"""
from __future__ import annotations

from ska_control_model import ObsState, ResultCode
from tango import DebugIt, DevState
from tango.server import command, run

from ska_csp_simulators.common.subarray_simulator import (
    SubarraySimulatorDevice,
)

__all__ = ["MidPssSubarraySimulator", "main"]


DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class MidPssSubarraySimulator(SubarraySimulatorDevice):
    """
    Base simulator device
    """

    # ---------------
    # General methods
    # ---------------

    # ----------
    # Attributes
    # ----------
    def is_ConfigureScan_allowed(self: MidPssSubarraySimulator) -> bool:
        """
        Return whether `ConfigureScan` may be called in the current device state.

        :raises ValueError: command not permitted in observation state

        :return: whether the command may be called in the current device
            state
        """
        if (
            self._obs_state not in [ObsState.IDLE, ObsState.READY]
            or self.get_state() != DevState.ON
        ):
            raise ValueError(
                "ConfigureScan command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

    @command(dtype_in=str, dtype_out="DevVarLongStringArray")
    @DebugIt()
    def ConfigureScan(self: MidPssSubarraySimulator, argin):
        """
        Subarray configure resources
        """
        return self.Configure(argin)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the device module."""
    return run((MidPssSubarraySimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
