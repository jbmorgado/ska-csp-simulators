# pylint: disable=redefined-outer-name
# -*- coding: utf-8 -*-
"""
Some simple unit tests of the PowerSupply device, exercising the device from
another host using a DeviceProxy.
"""
import logging

import pytest
import tango
from ska_control_model import (
    AdminMode,
    HealthState,
    ObsMode,
    ObsState,
    ResultCode,
)

from ska_csp_simulators.DevFactory import DevFactory
from ska_csp_simulators.mid.mid_cbf_subarray_simulator import (
    MidCbfSubarraySimulator,
)

module_logger = logging.getLogger(__name__)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": MidCbfSubarraySimulator,
            "devices": [
                {
                    "name": "sim-mid-cbf/subarray/01",
                },
            ],
        },
    )


@pytest.fixture
def subarray_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("sim-mid-cbf/subarray/01")


@pytest.fixture(autouse=True)
def subarray_device_online(subarray_device, change_event_callbacks):
    for attribute in [
        "state",
        "adminMode",
        "healthState",
        "obsState",
        "obsMode",
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
    change_event_callbacks.assert_change_event("obsMode", ObsMode.IDLE)
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


def test_mid_assign(subarray_device, change_event_callbacks):
    """Test assign request on subarray"""
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    [[result_code], [command_id]] = subarray_device.AddReceptors(
        ["SKA001", "SKA036"]
    )
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event("obsState", ObsState.RESOURCING)
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
    assert subarray_device.receptors == ("SKA001", "SKA036")
    assert subarray_device.assignedresources == ("SKA001", "SKA036")


@pytest.mark.parametrize(
    "device_init_obs_state",
    [
        ObsState.READY,
        ObsState.RESTARTING,
        ObsState.CONFIGURING,
        ObsState.ABORTED,
        ObsState.FAULT,
        ObsState.ABORTING,
        ObsState.RESOURCING,
        ObsState.SCANNING,
    ],
)
def test_addreceptors_not_allowed_in_wrong_obs_state(
    subarray_device, device_init_obs_state, change_event_callbacks
):
    """Test AddReceptors not allowed in wrong observing state"""
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    subarray_device.forceobsstate(device_init_obs_state)
    change_event_callbacks.assert_change_event(
        "obsState", device_init_obs_state
    )

    with pytest.raises(tango.DevFailed):
        subarray_device.AddReceptors(["SKA001"])


def test_mid_releaseall(subarray_device, change_event_callbacks):
    """Test assign request on subarray"""
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    subarray_device.forceobsstate(ObsState.IDLE)
    change_event_callbacks.assert_change_event("obsState", ObsState.IDLE)
    subarray_device.receptors = ["SKA002", "SKA005"]
    assert subarray_device.receptors
    [[result_code], [command_id]] = subarray_device.RemoveAllReceptors()
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event("obsState", ObsState.RESOURCING)
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "STAGING")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    change_event_callbacks.assert_change_event("obsState", ObsState.EMPTY)
    assert not subarray_device.receptors


def test_mid_configure(subarray_device, change_event_callbacks):
    """Test configure request on mid subarray"""
    subarray_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    subarray_device.forceobsstate(ObsState.IDLE)
    change_event_callbacks.assert_change_event("obsState", ObsState.IDLE)
    [[result_code], [command_id]] = subarray_device.ConfigureScan(
        '{"subarray_id":1}'
    )
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "obsState", ObsState.CONFIGURING
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "STAGING")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)
