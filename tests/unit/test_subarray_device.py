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

from ska_csp_simulators.common.subarray_simulator import (
    SubarraySimulatorDevice,
)
from ska_csp_simulators.DevFactory import DevFactory

module_logger = logging.getLogger(__name__)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": SubarraySimulatorDevice,
            "devices": [
                {
                    "name": "simul/test/0",
                },
            ],
        },
    )


@pytest.fixture
def subarray_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("simul/test/0")


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
    change_event_callbacks.assert_change_event("state", tango.DevState.UNKNOWN)
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


def test_obs_faulty(subarray_device):
    assert not subarray_device.obsFaulty
    subarray_device.obsFaulty = True
    assert subarray_device.obsFaulty


def test_subarray_device_is_alive(subarray_device):
    """Sanity check: test device on remote host is responsive"""
    try:
        subarray_device.ping()
    except tango.ConnectionFailed:
        pytest.fail("Could not contact the base device")


def test_assign(subarray_device, change_event_callbacks):
    """Test assign request on subarray"""
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    [[result_code], [command_id]] = subarray_device.AssignResources(
        '{"subarray_id":1}'
    )
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event("obsState", ObsState.RESOURCING)
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    change_event_callbacks.assert_change_event("obsState", ObsState.IDLE)


def test_configure(subarray_device, change_event_callbacks):
    """Test configure request on subarray"""
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    subarray_device.forceobsstate(ObsState.IDLE)
    change_event_callbacks.assert_change_event("obsState", ObsState.IDLE)
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


def test_abort_configure(subarray_device, change_event_callbacks):
    """Test abort request on subarray"""
    assert subarray_device.state() == tango.DevState.OFF
    assert subarray_device.obsstate == ObsState.EMPTY
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    subarray_device.forceobsstate(ObsState.IDLE)
    change_event_callbacks.assert_change_event("obsState", ObsState.IDLE)
    subarray_device.timeToComplete = 2
    assert subarray_device.timeToComplete == 2
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
    [[result_code], [abort_id]] = subarray_device.abort()
    change_event_callbacks.assert_change_event("obsState", ObsState.ABORTING)
    assert result_code == ResultCode.STARTED
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus",
        (command_id, "IN_PROGRESS", abort_id, "IN_PROGRESS"),
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus",
        (command_id, "ABORTED", abort_id, "IN_PROGRESS"),
    )
    change_event_callbacks.assert_change_event("obsState", ObsState.ABORTED)
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus",
        (command_id, "ABORTED", abort_id, "COMPLETED"),
    )


def test_scan(subarray_device, change_event_callbacks):
    """Test scan request on subarray"""
    assert subarray_device.state() == tango.DevState.OFF
    assert subarray_device.obsstate == ObsState.EMPTY
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    subarray_device.forceobsstate(ObsState.READY)
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)
    subarray_device.timeToComplete = 5
    assert subarray_device.timeToComplete == 5
    [[result_code], [command_id]] = subarray_device.Scan('{"subarray_id":1}')
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event("obsState", ObsState.SCANNING)
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    # wait a while before sending EndScan
    time.sleep(0.2)
    [[result_code], [endscan_id]] = subarray_device.EndScan()
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus",
        (command_id, "IN_PROGRESS", endscan_id, "IN_PROGRESS"),
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus",
        (command_id, "COMPLETED", endscan_id, "IN_PROGRESS"),
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus",
        (command_id, "COMPLETED", endscan_id, "COMPLETED"),
    )
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)


def test_obsfaulty_while_configuring(subarray_device, change_event_callbacks):
    """Test ObsState.FAULT  while configuring"""
    assert subarray_device.state() == tango.DevState.OFF
    assert subarray_device.obsstate == ObsState.EMPTY
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    subarray_device.forceobsstate(ObsState.IDLE)
    change_event_callbacks.assert_change_event("obsState", ObsState.IDLE)
    subarray_device.timeToComplete = 5
    assert subarray_device.timeToComplete == 5
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

    time.sleep(1)
    subarray_device.obsFaulty = True
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (command_id, "3"),
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus",
        (command_id, "COMPLETED"),
    )

    change_event_callbacks.assert_change_event("obsState", ObsState.FAULT)


def test_obsfaulty_while_scanning(subarray_device, change_event_callbacks):
    """Test ObsState.FAULT  while scanning"""
    assert subarray_device.state() == tango.DevState.OFF
    assert subarray_device.obsstate == ObsState.EMPTY
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    subarray_device.forceobsstate(ObsState.READY)
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)
    subarray_device.timeToComplete = 5
    assert subarray_device.timeToComplete == 5
    [[result_code], [command_id]] = subarray_device.Scan('{"subarray_id":1}')
    assert result_code == ResultCode.QUEUED

    change_event_callbacks.assert_change_event("obsState", ObsState.SCANNING)
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )

    time.sleep(1)
    subarray_device.obsFaulty = True
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult",
        (command_id, "3"),
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus",
        (command_id, "COMPLETED"),
    )

    change_event_callbacks.assert_change_event("obsState", ObsState.FAULT)
