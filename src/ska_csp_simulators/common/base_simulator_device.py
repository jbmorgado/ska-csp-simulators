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
import itertools
import json

# PyTango imports
import logging
import threading
import time
from random import uniform
from typing import Any

from ska_control_model import (
    AdminMode,
    HealthState,
    ResultCode,
    SimulationMode,
    TaskStatus,
)
from tango import DebugIt, DevState
from tango.server import Device, attribute, command, run

from ska_csp_simulators.common.command_tracker import CommandTracker

MAX_QUEUED_COMMANDS = 64
MAX_REPORTED_COMMANDS = 2 * MAX_QUEUED_COMMANDS + 2


__all__ = ["BaseSimulatorDevice", "main"]

DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]

# pylint: disable=logging-fstring-interpolation
# pylint: disable=unused-argument


class BaseSimulatorDevice(Device):
    """
    Base simulator device
    """

    # ---------------
    # General methods
    # ---------------
    PROGRESS_REPORTING_POINTS = ["33", "66"]

    def init_device(self):
        """Initialises the attributes and properties of the Motor."""
        super().init_device()
        self.logger = logging.getLogger(__name__)
        self._health_state = HealthState.OK
        self._admin_mode = AdminMode.OFFLINE
        self._simulation_mode = SimulationMode.TRUE
        self._command_ids_in_queue: list[str] = []
        self._commands_in_queue: list[str] = []
        self._command_statuses: list[str] = []
        self._command_progresses: list[str] = []
        self._command_result: tuple[str, str] = ("", "")
        self._time_to_complete = 0.4
        self._time_to_return = 0.05
        self._abort_event = threading.Event()
        self._command_tracker = CommandTracker(
            queue_changed_callback=self._update_commands_in_queue,
            status_changed_callback=self._update_command_statuses,
            progress_changed_callback=self._update_command_progresses,
            result_callback=self._update_command_result,
            exception_callback=self._update_command_exception,
        )

        for attribute_name in [
            "state",
            "status",
            "adminMode",
            "healthState",
            "simulationMode",
            "longRunningCommandsInQueue",
            "longRunningCommandIDsInQueue",
            "longRunningCommandStatus",
            "longRunningCommandProgress",
            "longRunningCommandResult",
        ]:
            self.set_change_event(attribute_name, True)
        self.update_state(DevState.UNKNOWN)
        self.logger.info("Device ready!")

        # self._dev_factory = DevFactory()
        # PROTECTED REGION END #    //  Motor.init_device

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        self._abort_event.clear()

    def delete_device(self):
        """Hook to delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """

    def update_state(self: BaseSimulatorDevice, value: DevState):
        if self.get_state() != value:
            self.set_state(value)
            self.push_change_event("state", value)

    def update_health_state(self: BaseSimulatorDevice, value: HealthState):
        if self._health_state != value:
            self._health_state = value
            self.push_change_event("healthstate", value)

    def update_admin_mode(self: BaseSimulatorDevice, value: AdminMode):
        if self._admin_mode != value:
            self._admin_mode = value
            self.push_change_event("adminmode", value)

    def set_communication(self: BaseSimulatorDevice, connecting: bool):
        """
        Enable or disable the connection with the system under control.
        """

        def _end_communicating(adminmode, delay):
            if adminmode == AdminMode.ONLINE:
                self.logger.info(
                    "Waiting to setup communication with the system"
                )
            else:
                self.logger.info(
                    "Disconnecting from the system under control!"
                )
            time.sleep(delay)
            if adminmode == AdminMode.ONLINE:
                self.logger.info("Communication established!")
                self.update_admin_mode(AdminMode.ONLINE)
                self.update_state(DevState.OFF)
                self.update_health_state(HealthState.OK)
            else:
                self.logger.info("System disconnected!")
                self.update_admin_mode(AdminMode.OFFLINE)
                self.update_state(DevState.DISABLE)

        thread_id = None
        if connecting:
            thread_id = threading.Thread(
                target=_end_communicating, args=(AdminMode.ONLINE, 1)
            )
        else:
            if self._admin_mode != AdminMode.OFFLINE:
                # return self.update_state(DevState.DISABLE)
                thread_id = threading.Thread(
                    target=_end_communicating, args=(AdminMode.OFFLINE, 1)
                )
        if thread_id:
            thread_id.start()

    def _simulate_latency(self) -> None:
        random_sleep = uniform(0.0, self._time_to_return)
        time.sleep(random_sleep)

    def _simulate_task_execution(
        self,
        task_callback,
        task_abort_event: threading.Event,
        result: Any,
    ) -> None:
        # Simulate the synchronous latency cost of communicating with this component.
        self._simulate_latency()

        def simulate_async_task_execution() -> None:
            def _call_task_callback(*args: Any, **kwargs: Any) -> None:
                if task_callback is not None:
                    try:
                        task_callback(*args, **kwargs)
                    except Exception as e:
                        self.logger.error(e)

            _call_task_callback(status=TaskStatus.IN_PROGRESS)
            if task_abort_event and task_abort_event.is_set():
                _call_task_callback(status=TaskStatus.ABORTED)
                return
            sleep_time = self._time_to_complete / (
                len(self.PROGRESS_REPORTING_POINTS) + 1
            )
            for progress_point in self.PROGRESS_REPORTING_POINTS:
                time.sleep(sleep_time)

                if task_abort_event and task_abort_event.is_set():
                    _call_task_callback(status=TaskStatus.ABORTED)
                    return

                _call_task_callback(progress=progress_point)

            time.sleep(sleep_time)

            if task_abort_event and task_abort_event.is_set():
                _call_task_callback(status=TaskStatus.ABORTED)
                return

            _call_task_callback(status=TaskStatus.COMPLETED)

        threading.Thread(target=simulate_async_task_execution).start()

    def configure_callback(self, command_id):
        return functools.partial(
            self._command_tracker.update_command_info, command_id
        )

    def do(self, command_name, completed=None, argin=None):
        """
        Invoke the execution of the command.

        :return: a tuple with the ResultCode and a message.
        """
        command_id = self._command_tracker.new_command(
            command_name, completed_callback=completed
        )
        if argin:
            self.logger.info(
                f"Command {command_name} executed with argument {argin}"
            )
        try:
            self._simulate_task_execution(
                self.configure_callback(command_id),
                task_abort_event=self._abort_event,
                result=(ResultCode.OK, f"{command_name} command completed OK"),
            )
            status = TaskStatus.QUEUED
        except Exception as e:
            self.logger.error(f"Command {command_name} exception: {e}")
            return ResultCode.FAILED, "Command failed"
        if status == TaskStatus.QUEUED:
            return ResultCode.QUEUED, command_id
        if status == TaskStatus.REJECTED:
            return ResultCode.REJECTED, f"Command {command_name} rejected"

    def _update_commands_in_queue(
        self, commands_in_queue: list[tuple[str, str]]
    ) -> None:
        if commands_in_queue:
            command_ids, command_names = zip(*commands_in_queue)
            self._command_ids_in_queue = [
                str(command_id) for command_id in command_ids
            ]
            self._commds_in_queue = [
                str(command_name) for command_name in command_names
            ]
        else:
            self._command_ids_in_queue = []
            self._commands_in_queue = []
        self.push_change_event(
            "longRunningCommandsInQueue", self._commands_in_queue
        )
        self.push_change_event(
            "longRunningCommandIDsInQueue", self._command_ids_in_queue
        )

    def _update_command_statuses(
        self,
        command_statuses: list[tuple[str, TaskStatus]],
    ) -> None:
        statuses = [(uid, status.name) for (uid, status) in command_statuses]
        self._command_statuses = [
            str(item) for item in itertools.chain.from_iterable(statuses)
        ]
        self.push_change_event(
            "longRunningCommandStatus", self._command_statuses
        )
        self.logger.info("pushed command status")

    def _update_command_progresses(
        self,
        command_progresses: list[tuple[str, int]],
    ) -> None:
        self._command_progresses = [
            str(item)
            for item in itertools.chain.from_iterable(command_progresses)
        ]
        self.push_change_event(
            "longRunningCommandProgress", self._command_progresses
        )

    def _update_command_result(
        self,
        command_id: str,
        command_result: tuple[ResultCode, str],
    ) -> None:
        self._command_result = (command_id, json.dumps(command_result))
        self.push_change_event(
            "longRunningCommandResult", self._command_result
        )

    def _update_command_exception(
        self,
        command_id: str,
        command_exception: Exception,
    ) -> None:
        self.logger.error(
            f"Command '{command_id}' raised exception {command_exception}"
        )
        self._command_result = (command_id, str(command_exception))
        self.push_change_event(
            "longRunningCommandResult", self._command_result
        )

    # ----------
    # Attributes
    # ----------
    @attribute(dtype="DevBoolean")
    def faulty(self):
        return self._faulty

    @faulty.write
    def faulty(self, value: bool):
        self._faulty = value

    @attribute(dtype="DevUShort")
    def timeToComplete(self):
        return self._time_to_complete

    @timeToComplete.write  # type: ignore[no-redef]
    def timeToComplete(self: BaseSimulatorDevice, value) -> None:
        self._time_to_complete = value

    @attribute(dtype=AdminMode, memorized=True, hw_memorized=True)
    def adminMode(self: BaseSimulatorDevice) -> AdminMode:
        """
        Read the Admin Mode of the device.

        It may interpret the current device condition and condition of all
        managed devices to set this. Most possibly an aggregate attribute.

        :return: Admin Mode of the device
        """
        return self._admin_mode

    @adminMode.write  # type: ignore[no-redef]
    def adminMode(self: BaseSimulatorDevice, value: AdminMode) -> None:
        """
        Set the Admin Mode of the device.

        :param value: Admin Mode of the device.

        :raises ValueError: for unknown adminMode
        """
        if self._admin_mode == AdminMode.ONLINE and value in [
            AdminMode.NOT_FITTED,
            AdminMode.RESERVED,
        ]:
            self.logger.warning(
                f"The device administration mode can't be set to {value}"
                f"when it is ONLINE. Set it to OFFLINE and then to {value}"
            )
        else:
            # self.update_admin_mode(value)
            enable_communication = value == AdminMode.ONLINE
            self.set_communication(enable_communication)

    @attribute(dtype=HealthState)
    def healthState(self: BaseSimulatorDevice) -> HealthState:
        """
        Read the Health state of the device.

        It may interpret the current device condition and condition of all
        managed devices to set this. Most possibly an aggregate attribute.

        """
        return self._health_state

    @attribute(dtype=SimulationMode)
    def simulationMode(self: BaseSimulatorDevice) -> SimulationMode:
        """
        Read the simulation mode of the device.

        It may interpret the current device condition and condition of all
        managed devices to set this. Most possibly an aggregate attribute.

        """
        return self._simulation_mode

    @simulationMode.write  # type: ignore[no-redef]
    def simulationMode(
        self: BaseSimulatorDevice, value: SimulationMode
    ) -> None:
        """
        Set the Simulation Mode of the device.

        :param value: Simulation Mode of the device.

        :raises ValueError: for unknown adminMode
        """
        self._simulation_mode = value

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=MAX_QUEUED_COMMANDS
    )
    def longRunningCommandsInQueue(self) -> list[str]:
        """
        Read the long running commands in the queue.

        Keep track of which commands are in the queue.
        Pop off from front as they complete.

        :return: tasks in the queue
        """
        return self._commands_in_queue

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=MAX_QUEUED_COMMANDS
    )
    def longRunningCommandIDsInQueue(
        self: BaseSimulatorDevice,
    ) -> list[str]:
        """
        Read the IDs of the long running commands in the queue.

        Every client that executes a command will receive a command ID as response.
        Keep track of IDs in the queue. Pop off from front as they complete.

        :return: unique ids for the enqueued commands
        """
        return self._command_ids_in_queue

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=MAX_REPORTED_COMMANDS * 2  # 2 per command
    )
    def longRunningCommandStatus(self) -> list[str]:
        """
        Read the status of the currently executing long running commands.

        ID, status pair of the currently executing command.
        Clients can subscribe to on_change event and wait for the
        ID they are interested in.

        :return: ID, status pairs of the currently executing commands
        """
        return self._command_statuses

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",), max_dim_x=2  # Only one command can execute at once
    )
    def longRunningCommandProgress(self) -> list[str]:
        """
        Read the progress of the currently executing long running command.

        ID, progress of the currently executing command.
        Clients can subscribe to on_change event and wait
        for the ID they are interested in.

        :return: ID, progress of the currently executing command.
        """
        return self._command_progresses

    @attribute(  # type: ignore[misc]  # "Untyped decorator makes function untyped"
        dtype=("str",),
        max_dim_x=2,  # Always the last result (unique_id, JSON-encoded result)
    )
    def longRunningCommandResult(
        self,
    ) -> tuple[str, str]:
        """
        Read the result of the completed long running command.

        Reports unique_id, json-encoded result.
        Clients can subscribe to on_change event and wait for
        the ID they are interested in.

        :return: ID, result.
        """
        return self._command_result

    # --------
    # Commands
    # --------

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def On(self):
        def _on_completed():
            self.logger.info("Command On completed on device}")
            self.update_state(DevState.ON)

        result_code, msg = self.do("on", _on_completed, argin=None)
        return ([result_code], [msg])

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Off(self):
        def _off_completed():
            self.update_state(DevState.OFF)

        result_code, msg = self.do("off", _off_completed)
        return ([result_code], [msg])

    @command(dtype_in="DevState")
    @DebugIt()
    def ForceState(self, value):
        self.update_state(value)

    @command(dtype_in=HealthState)
    @DebugIt()
    def ForceHealthState(self, value):
        self.update_health_state(value)


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Motor module."""
    return run((BaseSimulatorDevice,), args=args, **kwargs)


if __name__ == "__main__":
    main()
