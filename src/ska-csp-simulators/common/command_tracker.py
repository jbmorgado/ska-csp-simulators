from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Callable, TypedDict

from ska_control_model import ResultCode, TaskStatus

module_logger = logging.getLogger(__name__)

# pylint: disable=logging-fstring-interpolation


class _CommandData(TypedDict):
    name: str
    status: TaskStatus
    progress: int | None
    completed_callback: Callable[[], None] | None


def generate_command_id(command_name: str) -> str:
    """
    Generate a unique command ID for a given command name.

    :param command_name: name of the command for which an ID is to be
        generated.

    :return: a unique command ID string
    """
    return f"{time.time()}_{uuid.uuid4().fields[-1]}_{command_name}"


class CommandTracker:  # pylint: disable=too-many-instance-attributes
    """A class for keeping track of the state and progress of commands."""

    def __init__(  # pylint: disable=too-many-arguments
        self: CommandTracker,
        queue_changed_callback: Callable[[list[tuple[str, str]]], None],
        status_changed_callback: Callable[
            [list[tuple[str, TaskStatus]]], None
        ],
        progress_changed_callback: Callable[[list[tuple[str, int]]], None],
        result_callback: Callable[[str, tuple[ResultCode, str]], None],
        exception_callback: Callable[[str, Exception], None] | None = None,
        removal_time: float = 10.0,
    ) -> None:
        """
        Initialise a new instance.

        :param queue_changed_callback: called when the queue changes
        :param status_changed_callback: called when the status changes
        :param progress_changed_callback: called when the progress changes
        :param result_callback: called when command finishes
        :param exception_callback: called in the event of an exception
        :param removal_time: timer
        """
        self.__lock = threading.RLock()
        self._queue_changed_callback = queue_changed_callback
        self._status_changed_callback = status_changed_callback
        self._progress_changed_callback = progress_changed_callback
        self._result_callback = result_callback
        self._most_recent_result: tuple[
            str, tuple[ResultCode, str] | None
        ] | None = None
        self._exception_callback = exception_callback
        self._most_recent_exception: tuple[str, Exception] | None = None
        self._commands: dict[str, _CommandData] = {}
        self._removal_time = removal_time

    def new_command(
        self: CommandTracker,
        command_name: str,
        completed_callback: Callable[[], None] | None = None,
    ) -> str:
        """
        Create a new command.

        :param command_name: the command name
        :param completed_callback: an optional callback for command completion

        :return: a unique command id
        """
        command_id = generate_command_id(command_name)

        self._commands[command_id] = {
            "name": command_name,
            "status": TaskStatus.STAGING,
            "progress": None,
            "completed_callback": completed_callback,
        }
        self._queue_changed_callback(self.commands_in_queue)
        return command_id

    def _schedule_removal(self: CommandTracker, command_id: str) -> None:
        def remove(command_id: str) -> None:
            del self._commands[command_id]
            self._queue_changed_callback(self.commands_in_queue)

        threading.Timer(self._removal_time, remove, (command_id,)).start()

    def update_command_info(  # pylint: disable=too-many-arguments
        self: CommandTracker,
        command_id: str,
        status: TaskStatus | None = None,
        progress: int | None = None,
        result: tuple[ResultCode, str] | None = None,
        exception: Exception | None = None,
    ) -> None:
        """
        Update status information on the command.

        :param command_id: the unique command id
        :param status: the status of the asynchronous task
        :param progress: the progress of the asynchronous task
        :param result: the result of the completed asynchronous task
        :param exception: any exception caught in the running task
        """
        module_logger.info(f"Received status: {status} {command_id}")
        with self.__lock:
            if exception is not None:
                self._most_recent_exception = (command_id, exception)
                if self._exception_callback is not None:
                    self._exception_callback(command_id, exception)
            if result is not None:
                self._most_recent_result = (command_id, result)
                self._result_callback(command_id, result)
            if progress is not None:
                self._commands[command_id]["progress"] = progress
                self._progress_changed_callback(self.command_progresses)
            if status is not None:
                self._commands[command_id]["status"] = status
                module_logger.info(f"Updating to {self.command_statuses}")
                self._status_changed_callback(self.command_statuses)

                if status == TaskStatus.COMPLETED:
                    completed_callback = self._commands[command_id][
                        "completed_callback"
                    ]
                    if completed_callback is not None:
                        completed_callback()
                if status in [
                    TaskStatus.ABORTED,
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.REJECTED,
                ]:
                    self._commands[command_id]["progress"] = None
                    self._schedule_removal(command_id)

    @property
    def commands_in_queue(self: CommandTracker) -> list[tuple[str, str]]:
        """
        Return a list of commands in the queue.

        :return: a list of (command_id, command_name) tuples, ordered by
            when invoked.
        """
        with self.__lock:
            return list(
                (command_id, command["name"])
                for command_id, command in self._commands.items()
                if command["name"] is not None
            )

    @property
    def command_statuses(self: CommandTracker) -> list[tuple[str, TaskStatus]]:
        """
        Return a list of command statuses for commands in the queue.

        :return: a list of (command_id, status) tuples, ordered by when
            invoked.
        """
        with self.__lock:
            return list(
                (command_id, command["status"])
                for command_id, command in self._commands.items()
                if command["status"] is not None
            )

    @property
    def command_progresses(self: CommandTracker) -> list[tuple[str, int]]:
        """
        Return a list of command progresses for commands in the queue.

        :return: a list of (command_id, progress) tuples, ordered by
            when invoked.
        """
        with self.__lock:
            return list(
                (command_id, command["progress"])
                for command_id, command in self._commands.items()
                if command["progress"] is not None
            )

    @property
    def command_result(
        self: CommandTracker,
    ) -> tuple[str, tuple[ResultCode, str] | None] | None:
        """
        Return the result of the most recently completed command.

        :return: a (command_id, result) tuple. If no command has
            completed yet, then None.
        """
        return self._most_recent_result

    @property
    def command_exception(
        self: CommandTracker,
    ) -> tuple[str, Exception] | None:
        """
        Return the most recent exception, if any.

        :return: a (command_id, exception) tuple. If no command has
            raised an uncaught exception, then None.
        """
        return self._most_recent_exception

    def get_command_status(
        self: CommandTracker, command_id: str
    ) -> TaskStatus:
        """
        Return the current status of a running command.

        :param command_id: the unique command id

        :return: a status of the asynchronous task.
        """
        if command_id in self._commands:
            return self._commands[command_id]["status"]
        return TaskStatus.NOT_FOUND
