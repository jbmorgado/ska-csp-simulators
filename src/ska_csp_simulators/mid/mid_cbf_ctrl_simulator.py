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

import json

from ska_control_model import ResultCode
from tango import DebugIt, DevVarLongStringArray
from tango.server import attribute, command, run

from ska_csp_simulators.common.base_simulator_device import BaseSimulatorDevice

__all__ = ["MidCbfCtrlSimulator", "main"]

DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class MidCbfCtrlSimulator(BaseSimulatorDevice):
    """
    Base simulator device
    """

    # ---------------
    # General methods
    # ---------------

    # ----------
    # Attributes
    # ----------
    @attribute(dtype="str")
    def sysParam(self):
        return self._sys_param

    @attribute(dtype="str")
    def sourceSysParam(self):
        return self._source_sys_param

    # --------
    # Commands
    # --------

    @command(
        dtype_in="DevString",
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def InitSysParam(
        self: MidCbfCtrlSimulator, argin: str
    ) -> DevVarLongStringArray:
        def _initsys_completed():
            self.logger.info("Command InitSysParam completed on device}")
            self._source_sys_param = argin
            self._source_sys_param = ""

        argin_dict = json.loads(argin)
        return_code, msg = self.do(
            "initsysparam", _initsys_completed, argin=argin_dict
        )
        return [[return_code], [msg]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Motor module."""
    return run((MidCbfCtrlSimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
