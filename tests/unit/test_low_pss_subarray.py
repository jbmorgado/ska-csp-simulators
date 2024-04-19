# pylint: disable=redefined-outer-name
# -*- coding: utf-8 -*-
"""
Some simple unit tests of the PowerSupply device, exercising the device from
another host using a DeviceProxy.
"""
import logging

import pytest
import tango
from ska_control_model import AdminMode, HealthState, ObsState, ResultCode

from ska_csp_simulators.DevFactory import DevFactory
from ska_csp_simulators.low.low_pss_subarray_simulator import (
    LowPssSubarraySimulator,
)

module_logger = logging.getLogger(__name__)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": LowPssSubarraySimulator,
            "devices": [
                {
                    "name": "sim-low-pss/subarray/01",
                },
            ],
        },
    )


@pytest.fixture
def subarray_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("sim-low-pss/subarray/01")


@pytest.fixture(autouse=True)
def subarray_device_online(subarray_device, change_event_callbacks):
    for attribute in [
        "state",
        "adminMode",
        "healthState",
        "obsState",
        "longRunningCommandProgress",
        "longRunningCommandStatus",
        "longRunningCommandResult",
    ]:
        subarray_device.subscribe_event(
            attribute,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[attribute],
        )
    change_event_callbacks.assert_change_event("state", tango.DevState.DISABLE)
    change_event_callbacks.assert_change_event("adminMode", AdminMode.OFFLINE)
    change_event_callbacks.assert_change_event("healthState", HealthState.OK)
    change_event_callbacks.assert_change_event("obsState", ObsState.EMPTY)
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", ()
    )
    change_event_callbacks.assert_change_event("longRunningCommandStatus", ())
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult", ("", "")
    )
    subarray_device.adminmode = 0
    change_event_callbacks.assert_change_event("adminMode", AdminMode.ONLINE)
    change_event_callbacks.assert_change_event("state", tango.DevState.OFF)


def test_subarray_device_is_alive(subarray_device):
    """Sanity check: test device on remote host is responsive"""
    try:
        subarray_device.ping()
    except tango.ConnectionFailed:
        pytest.fail("Could not contact the base device")


def test_pss_subarray_configure(subarray_device, change_event_callbacks):
    """Test configure request on PSS Subarray"""
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    subarray_device.forceobsstate(ObsState.READY)
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)
    [[result_code], [command_id]] = subarray_device.Configure(
        '{"subarray_id":1}'
    )
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "obsState", ObsState.CONFIGURING
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)


def test_pss_subarray_configure_not_allowed_in_wrong_state(subarray_device):
    """Test PSS Subarray configure not allowed in wrong state"""
    assert subarray_device.state() == tango.DevState.OFF
    with pytest.raises(tango.DevFailed):
        subarray_device.ConfigureScan('{"subarray_id":1}')
