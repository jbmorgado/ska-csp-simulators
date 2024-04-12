# -*- coding: utf-8 -*-
#
# This file is part of the CSP Simulators project
#
# GPL v3
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Simulator for the subarray of a CSP sub-system
"""

from __future__ import annotations

import json

from ska_control_model import ObsState, ResultCode
from tango import DebugIt, DevState
from tango.server import command, run

from ska_csp_simulators.common.obs_simulator import ObsSimulatorDevice

__all__ = ["SubarraySimulatorDevice", "main"]


DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class SubarraySimulatorDevice(ObsSimulatorDevice):
    """
    Base simulator device
    """

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initialises the attributes and properties of the Motor."""
        super().init_device()
        self._obs_state = ObsState.EMPTY

        # self._dev_factory = DevFactory()

    def is_AssignResources_allowed(self: SubarraySimulatorDevice) -> bool:
        """
        Return whether the `AssignResource` command may be called in the current state.

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
                "AssignResources command not permitted in observation state "
                f"{self._obs_state} or state {self.get_state()}"
            )
        return True

    @command(dtype_in="DevString", dtype_out="DevVarLongStringArray")
    @DebugIt()
    def AssignResources(self, argin) -> DevVarLongStringArrayType:
        """
        Subarray assign resources
        """
        self.check_raise_exception()

        def _assign_completed():
            self.logger.info("Command AssignResources completed on device}")
            self.update_obs_state(ObsState.IDLE)

        argin_dict = json.loads(argin)
        self.logger.info(f"Call assign with argument: {argin_dict}")
        self.update_obs_state(ObsState.RESOURCING)
        result_code, msg = self.do(
            "assign", completed=_assign_completed, argin=argin_dict
        )
        return ([result_code], [msg])

    def is_ReleaseAllResources_allowed(self: SubarraySimulatorDevice) -> bool:
        """
        Return whether the `ReleaseAllResource` command may be called in the current state.

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
                "ReleaseAllResources command not permitted in observation state "
                f"{self._obs_state} or state {self.get_state()}"
            )
        return True

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def ReleaseAllResources(
        self: SubarraySimulatorDevice,
    ) -> DevVarLongStringArrayType:
        def _releaseall_completed():
            self.logger.info(
                "Command ReleaseAllResources completed on device}"
            )
            self.update_obs_state(ObsState.EMPTY)

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
    return run((SubarraySimulatorDevice,), args=args, **kwargs)


if __name__ == "__main__":
    main()
