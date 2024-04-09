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
from tango import DebugIt
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

    @command(dtype_in="DevString", dtype_out="DevVarLongStringArray")
    @DebugIt()
    def AssignResources(self, argin) -> DevVarLongStringArrayType:
        """
        Subarray assign resources
        """

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
