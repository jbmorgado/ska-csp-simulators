# pylint: disable=redefined-outer-name
# -*- coding: utf-8 -*-
"""
Some simple unit tests of the PowerSupply device, exercising the device from
another host using a DeviceProxy.
"""
import logging
import time

import pytest
import tango
from ska_control_model import AdminMode, HealthState, ObsState, ResultCode

from ska_csp_simulators.DevFactory import DevFactory
from ska_csp_simulators.low.low_cbf_subarray_simulator import (
    LowCbfSubarraySimulator,
)

module_logger = logging.getLogger(__name__)


def print_evt(evt):
    module_logger.info(evt)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": LowCbfSubarraySimulator,
            "devices": [
                {
                    "name": "sim-low-cbf/subarray/01",
                },
            ],
        },
    )


@pytest.fixture
def subarray_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("sim-low-cbf/subarray/01")


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
    change_event_callbacks.assert_change_event(
        "healthState", HealthState.UNKNOWN
    )
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
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)


def test_subarray_device_is_alive(subarray_device):
    """Sanity check: test device on remote host is responsive"""
    try:
        subarray_device.ping()
    except tango.ConnectionFailed:
        pytest.fail("Could not contact the base device")


def test_subarray_on(subarray_device, change_event_callbacks):
    """Test subarray on."""
    assert subarray_device.state() == tango.DevState.ON
    [[result_code], [command_id]] = subarray_device.On()
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "STAGING")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult", (command_id, "5")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    assert subarray_device.state() == tango.DevState.ON


def test_subarray_off(subarray_device, change_event_callbacks):
    """Test subarray off."""
    assert subarray_device.state() == tango.DevState.ON
    [[result_code], [command_id]] = subarray_device.Off()
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "STAGING")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult", (command_id, "5")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    assert subarray_device.state() == tango.DevState.ON


def test_subarray_standby(subarray_device):
    """Test subarray standby."""
    assert subarray_device.state() == tango.DevState.ON
    result_code = subarray_device.Standby()
    assert result_code[0] == ResultCode.REJECTED
    assert subarray_device.state() == tango.DevState.ON


def test_end(subarray_device, change_event_callbacks):
    """Test scan request on subarray"""
    assert subarray_device.state() == tango.DevState.ON
    subarray_device.forceobsstate(ObsState.READY)
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)
    time.sleep(2)
    assert subarray_device.obsState == ObsState.READY
    [[result_code], [command_id]] = subarray_device.End()
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "STAGING")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    change_event_callbacks.assert_change_event("obsState", ObsState.IDLE)


@pytest.mark.parametrize(
    "device_init_obs_state",
    [
        ObsState.EMPTY,
        ObsState.RESTARTING,
        ObsState.CONFIGURING,
        ObsState.ABORTED,
        ObsState.FAULT,
        ObsState.ABORTING,
        ObsState.RESOURCING,
        ObsState.SCANNING,
    ],
)
def test_end_not_allowed_in_wrong_obs_state(
    subarray_device, device_init_obs_state, change_event_callbacks
):
    """Test End not allowed when the device is in wrong status"""
    if device_init_obs_state != ObsState.EMPTY:
        subarray_device.forceobsstate(device_init_obs_state)
        change_event_callbacks.assert_change_event(
            "obsState", device_init_obs_state
        )
    with pytest.raises(tango.DevFailed):
        subarray_device.End()
