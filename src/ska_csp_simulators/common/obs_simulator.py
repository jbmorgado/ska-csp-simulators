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
import threading
import time
from typing import Any

from ska_control_model import ObsMode, ObsState, ResultCode, TaskStatus
from tango import DebugIt, DevState
from tango.server import attribute, command, run

from ska_csp_simulators.common.base_simulator_device import BaseSimulatorDevice

__all__ = ["ObsSimulatorDevice", "main"]


DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation

# se scan time to 30 sec
SCAN_TIME = 30


class ObsSimulatorDevice(BaseSimulatorDevice):
    """
    Base simulator device
    """

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initialises the attributes and properties of the device."""
        super().init_device()
        self._obs_mode = ObsMode.IDLE
        self._obs_state = ObsState.IDLE
        self._obs_faulty = False
        self._timeout = False
        self._endscan_event = threading.Event()
        for attribute_name in [
            "obsState",
            "obsMode",
        ]:
            self.set_change_event(attribute_name, True, False)
        self.logger.info("Device ready!")

        # self._dev_factory = DevFactory()

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        self._endscan_event.clear()

    def update_obs_state(self: ObsSimulatorDevice, value: ObsState):
        if self._obs_state != value:
            self._obs_state = value
            self.push_change_event("obsState", value)

    def update_obs_mode(self: ObsSimulatorDevice, value: ObsMode):
        if self._obs_mode != value:
            self._obs_mode = value
            self.push_change_event("obsMode", value)

    def _simulate_task_execution(
        self,
        task_callback,
        task_abort_event: threading.Event,
        result: Any,
    ) -> None:
        # Simulate the synchronous latency cost of communicating with this component.
        self._simulate_latency()
        self.logger.info("Call to simulate task execution")

        def simulate_async_task_execution() -> None:
            def _call_task_callback(*args: Any, **kwargs: Any) -> None:
                if task_callback is not None:
                    try:
                        self.logger.info(
                            f"task callback called with {kwargs} {task_callback.args[0]}"
                        )
                        task_callback(*args, **kwargs)
                    except Exception as e:
                        self.logger.error(e)

            start_time = time.time()
            _call_task_callback(status=TaskStatus.IN_PROGRESS)
            while (time.time() - start_time) < self._time_to_complete:
                if self._endscan_event and self._endscan_event.is_set():
                    _call_task_callback(status=TaskStatus.COMPLETED)
                    return
                if task_abort_event and task_abort_event.is_set():
                    _call_task_callback(status=TaskStatus.ABORTED)
                    self.update_obs_state(ObsState.ABORTED)
                    return

                if self._obs_faulty or self._faulty_in_command:
                    _call_task_callback(
                        status=TaskStatus.COMPLETED, result=ResultCode.FAILED
                    )
                    if self._faulty_in_command:
                        self._faulty_in_command = 0
                    return
                time.sleep(0.1)

            _call_task_callback(status=TaskStatus.COMPLETED)
            self.logger.info("Asynchronous task completed!")

        threading.Thread(target=simulate_async_task_execution).start()

    # ----------
    # Attributes
    # ----------
    @attribute(dtype=ObsState)
    def obsState(self):
        return self._obs_state

    @attribute(dtype=ObsMode)
    def obsMode(self):
        return self._obs_mode

    @attribute(dtype="DevBoolean")
    def obsFaulty(self):
        return self._obs_faulty

    @obsFaulty.write
    def obsFaulty(self, value: bool):
        self._obs_faulty = value

    # --------
    # Commands
    # --------
    @command(dtype_in=ObsState)
    @DebugIt()
    def ForceObsState(self: ObsSimulatorDevice, value: ObsState) -> None:
        """
        Force the subarray observing state to the desired value
        """
        self.logger.info(
            f"Force observing state from {ObsState(self._obs_state).name} "
            f"to {ObsState(value).name}"
        )
        self.update_obs_state(value)

    @command(dtype_in=ObsMode)
    @DebugIt()
    def ForceObsMode(self: ObsSimulatorDevice, value: ObsMode) -> None:
        """
        Force the subarray observing mode to the desired value
        """
        self.logger.info(
            f"Force observing state from {ObsMode(self._obs_mode).name} "
            f"to {ObsMode(value).name}"
        )
        self.update_obs_mode(value)

    def is_Configure_allowed(self: ObsSimulatorDevice) -> bool:
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
                "Configure command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

    @command(dtype_in=str, dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Configure(self, argin):
        """
        Subarray configure resources
        """
        self.check_raise_exception()

        def _configure_completed():
            self.logger.info("Command Configure completed on device}")
            if self._obs_faulty:
                return self.update_obs_state(ObsState.FAULT)
            if self._faulty_in_command:
                self.update_obs_state(ObsState.IDLE)
            if (
                not self._abort_event.is_set()
                and not self._obs_faulty
                and not self._faulty_in_command
            ):
                self.update_obs_state(ObsState.READY)

        argin_dict = json.loads(argin)
        self.update_obs_state(ObsState.CONFIGURING)
        result_code, msg = self.do(
            "configure", completed=_configure_completed, argin=argin_dict
        )
        return ([result_code], [msg])

    def is_Scan_allowed(self: ObsSimulatorDevice) -> bool:
        """
        Return whether `Scan` may be called in the current device state.

        :raises ValueError: command not permitted in observation state

        :return: whether the command may be called in the current device
            state
        """
        if (
            self._obs_state != ObsState.READY
            or self.get_state() != DevState.ON
        ):
            raise ValueError(
                "Scan command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

    @command(dtype_in=str, dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Scan(self, argin):
        def _scan_completed():
            self.logger.info("Scan completed on device}")
            if self._obs_faulty:
                self.update_obs_state(ObsState.FAULT)
            if self._faulty_in_command:
                self.update_obs_state(ObsState.READY)
            self._time_to_complete = 0.4
            self.logger.info(
                f"Reset timeToComplete to {self._time_to_complete} sec"
            )

        self._time_to_complete = SCAN_TIME
        self.check_raise_exception()
        argin_dict = json.loads(argin)
        self.update_obs_state(ObsState.SCANNING)
        result_code, msg = self.do(
            "scan", completed=_scan_completed, argin=argin_dict
        )
        return ([result_code], [msg])

    def is_EndScan_allowed(self: ObsSimulatorDevice) -> bool:
        """
        Return whether `EndScan` may be called in the current device state.

        :raises ValueError: command not permitted in observation state

        :return: whether the command may be called in the current device
            state
        """
        if (
            self._obs_state != ObsState.SCANNING
            or self.get_state() != DevState.ON
        ):
            raise ValueError(
                "EndScan command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def EndScan(self):
        self.check_raise_exception()

        def _endscan():
            self.logger.info("Event scan started")
            self._command_tracker.update_command_info(
                command_id, status=TaskStatus.IN_PROGRESS
            )
            time.sleep(0.2)
            self._command_tracker.update_command_info(
                command_id, status=TaskStatus.COMPLETED
            )
            self.update_obs_state(ObsState.READY)

        command_id = self._command_tracker.new_command("endscan")
        self._endscan_event.set()
        threading.Thread(target=_endscan).start()
        result_code, _ = ResultCode.STARTED, "EndScan invoked"
        return ([result_code], [command_id])

    def is_GoToIdle_allowed(self: ObsSimulatorDevice) -> bool:
        """
        Return whether `GoToIdle` may be called in the current device state.

        :raises ValueError: command not permitted in observation state

        :return: whether the command may be called in the current device
            state
        """
        if (
            self._obs_state != ObsState.READY
            or self.get_state() != DevState.ON
        ):
            raise ValueError(
                "GoToIdle command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def GoToIdle(self):
        self.check_raise_exception()

        def _end_completed():
            self.logger.info("Command GotoIdle completed on device}")
            self.update_obs_state(ObsState.IDLE)

        result_code, msg = self.do("end", completed=_end_completed)
        return ([result_code], [msg])

    def is_ObsReset_allowed(self: ObsSimulatorDevice) -> bool:
        """
        Return whether the `ObsReset` command may be called in the current device state.

        :raises ValueError: command not permitted in observation state

        :return: whether the command may be called in the current device
            state
        """
        if (
            self._obs_state not in [ObsState.FAULT, ObsState.ABORTED]
            or self.get_state() != DevState.ON
        ):
            raise ValueError(
                "ObsREset command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def ObsReset(self: ObsSimulatorDevice):
        def _obsreset():
            self.logger.info("Call _obsreset")
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
        self.update_obs_state(ObsState.RESETTING)
        command_id = self._command_tracker.new_command("obsreset")
        threading.Thread(target=_obsreset).start()
        return ([ResultCode.QUEUED], [command_id])

    def is_Abort_allowed(self: ObsSimulatorDevice) -> bool:
        """
        Return whether `Abort` may be called in the current device state.

        :raises ValueError: command not permitted in observation state

        :return: whether the command may be called in the current device
            state
        """
        if (
            self._obs_state
            not in [
                ObsState.RESOURCING,
                ObsState.IDLE,
                ObsState.CONFIGURING,
                ObsState.READY,
                ObsState.SCANNING,
                ObsState.RESETTING,
            ]
            or self.get_state() != DevState.ON
        ):
            raise ValueError(
                "Abort command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Abort(self):
        def _abort():
            self._command_tracker.update_command_info(
                command_id, status=TaskStatus.IN_PROGRESS
            )
            time.sleep(0.2)
            self._command_tracker.update_command_info(
                command_id, status=TaskStatus.COMPLETED
            )

        obs_state_ori = self._obs_state

        self.update_obs_state(ObsState.ABORTING)
        command_id = self._command_tracker.new_command("abort")
        self.logger.info("Invoking Abort")

        result_code, _ = ResultCode.STARTED, "Abort invoked"
        if obs_state_ori in [ObsState.IDLE, ObsState.READY]:
            self.update_obs_state(ObsState.ABORTED)
            self._obs_faulty = False
            result_code = ResultCode.OK
        else:
            self._abort_event.set()
            threading.Thread(target=_abort).start()
        return ([result_code], [command_id])


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the device module."""
    return run((ObsSimulatorDevice,), args=args, **kwargs)


if __name__ == "__main__":
    main()
