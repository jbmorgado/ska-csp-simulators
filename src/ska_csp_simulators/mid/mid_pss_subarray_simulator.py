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

from ska_control_model import ResultCode
from tango.server import run

from ska_csp_simulators.common.subarray_simulator import (
    SubarraySimulatorDevice,
)

__all__ = ["MidPssSubarraySimulator", "main"]


DevVarLongStringArrayType = tuple[list[ResultCode], list[str]]
# pylint: disable=logging-fstring-interpolation


class MidPssSubarraySimulator(SubarraySimulatorDevice):
    """
    Base simulator device
    """

    # ---------------
    # General methods
    # ---------------

    # ----------
    # Attributes
    # ----------


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the Motor module."""
    return run((MidPssSubarraySimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
