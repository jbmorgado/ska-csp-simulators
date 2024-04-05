# pylint: disable=redefined-outer-name
# -*- coding: utf-8 -*-
"""
Some simple unit tests of the PowerSupply device, exercising the device from
another host using a DeviceProxy.
"""
import logging

import pytest
import tango
from ska_control_model import AdminMode, HealthState, ResultCode

from ska_csp_simulators.DevFactory import DevFactory
from ska_csp_simulators.low.low_cbf_ctrl_simulator import LowCbfCtrlSimulator

module_logger = logging.getLogger(__name__)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": LowCbfCtrlSimulator,
            "devices": [
                {
                    "name": "sim-low-cbf/control/0",
                },
            ],
        },
    )


@pytest.fixture
def ctrl_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("sim-low-cbf/control/0")


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
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    change_event_callbacks.assert_change_event("adminMode", AdminMode.OFFLINE)
    change_event_callbacks.assert_change_event(
        "healthState", HealthState.UNKNOWN
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


def test_turn_low_ctrl_on(ctrl_device):
    """Test device sets current on request"""
    result_code, _ = ctrl_device.On()
    assert result_code[0] == ResultCode.REJECTED


def test_turn_low_ctrl_off(ctrl_device):
    """Test device sets current off request"""
    result_code, _ = ctrl_device.Off()
    assert result_code[0] == ResultCode.REJECTED


def test_low_ctrl_reset(ctrl_device):
    """Test device sets current reset request"""
    result_code, _ = ctrl_device.Reset()
    assert result_code[0] == ResultCode.REJECTED
