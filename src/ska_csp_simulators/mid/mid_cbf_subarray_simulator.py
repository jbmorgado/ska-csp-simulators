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
from tango import DebugIt, DevState
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

    def is_ConfigureScan_allowed(self: MidCbfSubarraySimulator) -> bool:
        """
        Return whether `Configure` may be called in the current device state.

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

    def is_AddReceptors_allowed(self: MidCbfSubarraySimulator) -> bool:
        """
        Return whether the `AddReceptors` command may be called in the current state.

        :raises ValueError: command not permitted in observation state

        :return: whether the command may be called in the current device
            state
        """
        # If we return False here, Tango will raise an exception that incorrectly blames
        # refusal on device state.
        # e.g. "AssignResources not allowed when the device is in ON state".
        # So let's raise an exception ourselves.
        if (
            self._obs_state not in [ObsState.EMPTY, ObsState.IDLE]
            or self.get_state() != DevState.ON
        ):
            raise ValueError(
                "AddReceptors command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

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

        self.check_raise_exception()
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

    def is_RemoveAllReceptors_allowed(self: MidCbfSubarraySimulator) -> bool:
        """
        Return whether the `RemoveAllReceptors` command may be called in the current state.

        :raises ValueError: command not permitted in observation state

        :return: whether the command may be called in the current device
            state
        """
        # If we return False here, Tango will raise an exception that incorrectly blames
        # refusal on device state.
        # e.g. "AssignResources not allowed when the device is in ON state".
        # So let's raise an exception ourselves.
        if self._obs_state != ObsState.IDLE or self.get_state() != DevState.ON:
            raise ValueError(
                "RemoveAllReceptors command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

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

        self.check_raise_exception()
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
