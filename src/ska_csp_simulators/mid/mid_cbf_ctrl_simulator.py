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

import functools
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
    def init_device(self):
        """Initialises the attributes and properties of the Motor."""
        super().init_device()
        self._sys_param = ""
        self._source_sys_param = ""

    # ----------
    # Attributes
    # ----------
    @attribute(dtype="DevString")
    def sysParam(self):
        return self._sys_param

    @attribute(dtype="DevString")
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
        def _initsys_completed(argin_dict):
            self.logger.info(f" input argumnet {argin_dict}")
            self.logger.info("Command InitSysParam completed on device}")
            file_path = argin_dict["tm_data_filepath"]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    vcc_map = f.read().replace("\n", "")
                    self._sys_param = vcc_map
            except Exception as e:
                self.logger.error(e)
                self._sys_param = ""

        result_code = ResultCode.OK
        msg = "Dish-VCC map correctly programmed"
        try:
            argin_dict = json.loads(argin)
            if "tm_data_filepath" in argin_dict:
                result_code, msg = self.do(
                    "initsysparam",
                    functools.partial(_initsys_completed, argin_dict),
                    argin=None,
                )
                self._source_sys_param = argin
            else:
                self._sys_param = argin
                self._source_sys_param = ""

        except Exception as e:
            self.logger.error(e)
            msg = f"{e}"
            result_code = ResultCode.FAILED
        return [[result_code], [msg]]


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Motor module."""
    return run((MidCbfCtrlSimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
