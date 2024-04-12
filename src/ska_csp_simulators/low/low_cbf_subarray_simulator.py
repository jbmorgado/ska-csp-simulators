# -*- coding: utf-8 -*-
#
# This file is part of the CSP Simulators project
#
# GPL v3
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Simulator for the Low subarray of a CSP sub-system
"""
from __future__ import annotations

from collections import defaultdict

from ska_control_model import HealthState, ObsState, ResultCode
from tango import DebugIt, DevState
from tango.server import attribute, command, run

from ska_csp_simulators.common.subarray_simulator import (
    SubarraySimulatorDevice,
)

__all__ = ["LowCbfSubarraySimulator", "main"]


DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class LowCbfSubarraySimulator(SubarraySimulatorDevice):
    """
    Base simulator device
    """

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initialises the attributes and properties of the Motor."""
        super().init_device()
        self._health_state = HealthState.UNKNOWN
        self._stations = defaultdict(set)
        self._pstBeams = defaultdict(set)
        self._pssBeams = defaultdict(set)

    # ----------
    # Attributes
    # ----------
    @attribute(
        dtype="DevString",
        label="Station Beams",
        doc="Report configuration of all Station Beams",
    )
    def stations(self):
        """Return the stations attribute."""
        return str(self._stations)

    @attribute(
        dtype="DevString",
        label="Pulsar Search Beams",
        doc=(
            "Each Pulsar Search Beam is associated with one Station Beam, and "
            "has additional configuration parameters including a delay "
            "polynomial source (supplied via Configure)"
        ),
    )
    def pssBeams(self):
        """Return the pssBeams attribute."""
        return str(self._pss_beams)

    @attribute(
        dtype="DevString",
        label="Pulsar Timing Beams",
        doc=(
            "Each Pulsar Timing Beam is associated with one Station Beam, and "
            "has additional configuration parameters including a delay "
            "polynomial source (supplied via Configure)"
        ),
    )
    def pstBeams(self):
        """Return the pstBeams attribute."""
        return str(self._pst_beams)

    def set_communication(
        self: LowCbfSubarraySimulator,
        end_state: DevState,
        end_health: HealthState,
        connecting: bool,
    ):
        if connecting:
            super().set_communication(
                DevState.ON, HealthState.UNKNOWN, connecting
            )

    def is_End_allowed(self: LowCbfSubarraySimulator) -> bool:
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
                "End command not permitted in observation state "
                f"{ObsState(self._obs_state).name} or state {self.get_state()}"
            )
        return True

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def End(self) -> DevVarLongStringArrayType:
        """
        Subarray End scan
        """
        return self.GoToIdle()


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Motor module."""
    return run((LowCbfSubarraySimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
