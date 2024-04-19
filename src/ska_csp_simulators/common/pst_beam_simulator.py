# -*- coding: utf-8 -*-
#
# This file is part of the CSP Simulators project
#
# GPL v3
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Simulator for the PST beam sub-system
"""

from __future__ import annotations

import json
import threading
import time

from ska_control_model import ObsState, ResultCode, TaskStatus
from tango import DebugIt, DevState
from tango.server import attribute, command, run

from ska_csp_simulators.common.obs_simulator import ObsSimulatorDevice

__all__ = ["PstBeamSimulatorDevice", "main"]


DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class PstBeamSimulatorDevice(ObsSimulatorDevice):
    """
    Base simulator device
    """

    def init_device(self):
        """Initialises the attributes and properties of the device."""
        super().init_device()
        self._channel_block_configuration = {}
        self.set_change_event("channelBlockConfiguration", True)

    # ---------------
    # General methods
    # ---------------
    def update_channel_block(self, attr_value: str):
        # load the JSON string into a dict
        self._channel_block_configuration = json.loads(attr_value)
        # update the attribute using the string value
        self.push_change_event("channelBlockConfiguration", attr_value)

    # ----------
    # Attributes
    # ----------
    @attribute(
        dtype=str,
        doc="The channel block configuration based on scan configuration.",
    )
    def channelBlockConfiguration(self: PstBeamSimulatorDevice) -> str:
        # convert the dict information to a string
        return json.dumps(self._channel_block_configuration)

    # --------
    # Commands
    # --------

    @command(dtype_in=str, dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Configure(self, argin):
        """
        Subarray configure resources
        """
        self.check_raise_exception()

        def _configure_completed():
            self.logger.info("Command Configure completed on device}")
            if not self._abort_event.is_set():
                self.update_obs_state(ObsState.READY)
                with open(
                    "./tests/test_data/pst_channel_block_config.json",
                    "r",
                    encoding="utf-8",
                ) as f:
                    channel_config = f.read().replace("\n", "")
                    self.update_channel_block(channel_config)

        argin_dict = json.loads(argin)
        self.update_obs_state(ObsState.CONFIGURING)
        result_code, msg = self.do(
            "configure", completed=_configure_completed, argin=argin_dict
        )
        return ([result_code], [msg])

    def is_ConfigureScan_allowed(self: PstBeamSimulatorDevice) -> bool:
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
    def ConfigureScan(self, argin):
        """
        Subarray configure resources
        """
        return self.Configure(argin)

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def GoToIdle(self):
        self.check_raise_exception()

        def _end_completed():
            self.logger.info("Command GotoIdle completed on device}")
            self.update_obs_state(ObsState.IDLE)
            self.update_channel_block("{}")

        result_code, msg = self.do("end", completed=_end_completed)
        return ([result_code], [msg])

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Restart(self):
        def _restart():
            self.logger.info("Call _restart")
            self._command_tracker.update_command_info(
                command_id, status=TaskStatus.IN_PROGRESS
            )
            time.sleep(self._time_to_complete)
            self._command_tracker.update_command_info(
                command_id, status=TaskStatus.COMPLETED
            )
            self._abort_event.clear()
            self._obs_faulty = False
            self.update_obs_state(ObsState.IDLE)

        self.check_raise_exception()
        self.update_obs_state(ObsState.RESTARTING)
        command_id = self._command_tracker.new_command("restart")
        threading.Thread(target=_restart).start()
        return ([ResultCode.QUEUED], [command_id])


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the device module."""
    return run((ObsSimulatorDevice,), args=args, **kwargs)


if __name__ == "__main__":
    main()
