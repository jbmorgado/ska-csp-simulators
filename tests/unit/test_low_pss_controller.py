# pylint: disable=redefined-outer-name
# -*- coding: utf-8 -*-
"""
Some simple unit tests of the PowerSupply device, exercising the device from
another host using a DeviceProxy.
"""
import logging

import pytest
import tango
from ska_control_model import AdminMode, HealthState

from ska_csp_simulators.DevFactory import DevFactory
from ska_csp_simulators.low.low_pss_ctrl_simulator import LowPssCtrlSimulator

module_logger = logging.getLogger(__name__)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": LowPssCtrlSimulator,
            "devices": [
                {
                    "name": "sim-low-pss/control/0",
                },
            ],
        },
    )


@pytest.fixture
def ctrl_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("sim-low-pss/control/0")


@pytest.fixture(autouse=True)
def ctrl_device_online(ctrl_device, change_event_callbacks):
    for attribute in [
        "state",
        "adminMode",
        "healthState",
        "longRunningCommandProgress",
        "longRunningCommandStatus",
        "longRunningCommandResult",
    ]:
        ctrl_device.subscribe_event(
            attribute,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[attribute],
            # print_event
        )
    change_event_callbacks.assert_change_event("state", tango.DevState.DISABLE)
    change_event_callbacks.assert_change_event("adminMode", AdminMode.OFFLINE)
    change_event_callbacks.assert_change_event(
        "healthState", HealthState.UNKNOWNOK
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", ()
    )
    change_event_callbacks.assert_change_event("longRunningCommandStatus", ())
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult", ("", "")
    )
    ctrl_device.adminmode = 0
    change_event_callbacks.assert_change_event("adminMode", AdminMode.ONLINE)
    assert ctrl_device.state() == tango.DevState.OFF
