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

import functools

from ska_control_model import ObsState, ResultCode
from tango import DebugIt
from tango.server import attribute, command, run

from ska_csp_simulators.common.subarray_simulator import (
    SubarraySimulatorDevice,
)

__all__ = ["MidCbfSubarraySimulator", "main"]


DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class MidCbfSubarraySimulator(SubarraySimulatorDevice):
    """
    Base simulator device
    """

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initialises the attributes and properties of the Motor."""
        super().init_device()
        self._receptors = []
        self._assigned_resources = []

        # self._dev_factory = DevFactory()
        # PROTECTED REGION END #   //  Motor.init_device

    # ----------
    # Attributes
    # ----------
    @attribute(dtype=("str",), max_dim_x=197)
    def receptors(self):
        return self._receptors

    @receptors.write
    def receptors(self, value):
        self._receptors = value

    @attribute(
        dtype=("str",),
        max_dim_x=32,
    )
    def assignedResources(self):
        return self._assigned_resources

    @command(dtype_in="DevString", dtype_out="DevVarLongStringArray")
    @DebugIt()
    def ConfigureScan(self, argin) -> DevVarLongStringArrayType:
        """
        Subarray configure resources
        """
        return self.Configure(argin)

    @command(dtype_in=str, dtype_out="DevVarLongStringArray")
    @DebugIt()
    def AssignResources(self, argin: str) -> DevVarLongStringArrayType:
        raise ValueError(
            "AssignResources not used by Mid CBF. Use AddReceptors command"
        )

    @command(dtype_in=("str",), dtype_out="DevVarLongStringArray")
    @DebugIt()
    def AddReceptors(self, receptors_list) -> DevVarLongStringArrayType:
        """
        Subarray assign resources
        """

        def _assign_completed(receptors_list):
            self.logger.info("Command AssignResources completed on device}")
            self.update_obs_state(ObsState.IDLE)
            self._receptors = receptors_list
            self._assigned_resources = receptors_list

        self.logger.info(f"Call assign with argument: {receptors_list}")
        self.update_obs_state(ObsState.RESOURCING)
        result_code, msg = self.do(
            "assign",
            completed=functools.partial(_assign_completed, receptors_list),
        )
        return ([result_code], [msg])

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def ReleaseAllResources(self, argin: str) -> DevVarLongStringArrayType:
        raise ValueError(
            "ReleaseAllResources not used by Mid CBF. Use AddReceptors command"
        )

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def RemoveAllReceptors(
        self: MidCbfSubarraySimulator,
    ) -> DevVarLongStringArrayType:
        def _releaseall_completed():
            self.logger.info(
                "Command ReleaseAllResources completed on device}"
            )
            self.update_obs_state(ObsState.EMPTY)
            self._receptors = []

        self.update_obs_state(ObsState.RESOURCING)
        result_code, msg = self.do(
            "releaseall", completed=_releaseall_completed, argin=None
        )
        return ([result_code], [msg])


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Motor module."""
    return run((MidCbfSubarraySimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
