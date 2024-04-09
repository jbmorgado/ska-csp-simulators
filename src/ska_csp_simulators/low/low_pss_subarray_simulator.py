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

from tango.server import run

from ska_csp_simulators.common.subarray_simulator import (
    SubarraySimulatorDevice,
)

__all__ = ["LowPssSubarraySimulator", "main"]


class LowPssSubarraySimulator(SubarraySimulatorDevice):
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
    return run((LowPssSubarraySimulator,), args=args, **kwargs)


if __name__ == "__main__":
    main()
