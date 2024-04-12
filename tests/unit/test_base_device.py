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

from ska_csp_simulators.common.base_simulator_device import BaseSimulatorDevice
from ska_csp_simulators.DevFactory import DevFactory

module_logger = logging.getLogger(__name__)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": BaseSimulatorDevice,
            "devices": [
                {
                    "name": "simul/test/0",
                },
            ],
        },
    )


@pytest.fixture
def base_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("simul/test/0")


@pytest.fixture(autouse=True)
def base_device_online(base_device, change_event_callbacks):
    for attribute in [
        "state",
        "adminMode",
        "healthState",
        "longRunningCommandProgress",
        "longRunningCommandStatus",
        "longRunningCommandResult",
    ]:
        base_device.subscribe_event(
            attribute,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[attribute],
            # print_event
        )
    change_event_callbacks.assert_change_event("state", tango.DevState.DISABLE)
    change_event_callbacks.assert_change_event("adminMode", AdminMode.OFFLINE)
    change_event_callbacks.assert_change_event("healthState", HealthState.OK)
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", ()
    )
    change_event_callbacks.assert_change_event("longRunningCommandStatus", ())
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult", ("", "")
    )
    base_device.adminmode = 0
    change_event_callbacks.assert_change_event("adminMode", AdminMode.ONLINE)
    change_event_callbacks.assert_change_event("state", tango.DevState.OFF)


def test_device_is_alive(base_device):
    """Sanity check: test device on remote host is responsive"""
    try:
        base_device.ping()
    except tango.ConnectionFailed:
        pytest.fail("Could not contact the base device")


def test_device_offline(base_device, change_event_callbacks):
    assert base_device.adminmode == AdminMode.ONLINE
    base_device.adminmode = AdminMode.OFFLINE
    change_event_callbacks.assert_change_event("adminMode", AdminMode.OFFLINE)
    change_event_callbacks.assert_change_event("state", tango.DevState.DISABLE)


def test_simulation_mode(base_device):
    assert base_device.simulationMode


def test_health_state(base_device, change_event_callbacks):
    assert base_device.healthState == HealthState.OK
    base_device.forcehealthstate(HealthState.DEGRADED)
    change_event_callbacks.assert_change_event(
        "healthState", HealthState.DEGRADED
    )


def test_faulty_in_command(base_device):
    assert not base_device.faultyInCommand
    base_device.faultyInCommand = True
    assert base_device.faultyInCommand


def test_raise_exception(base_device):
    assert not base_device.raiseException
    base_device.raiseException = True
    assert base_device.raiseException


@pytest.mark.parametrize(
    "device_init_state",
    [
        tango.DevState.ON,
        tango.DevState.OFF,
        tango.DevState.STANDBY,
        tango.DevState.UNKNOWN,
    ],
)
def test_turn_on(base_device, change_event_callbacks, device_init_state):
    """Test device sets current on request"""
    assert base_device.state() == tango.DevState.OFF
    base_device.forcestate(device_init_state)
    if device_init_state != tango.DevState.OFF:
        change_event_callbacks.assert_change_event("state", device_init_state)
    [[result_code], [command_id]] = base_device.On()
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", (command_id, "33")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", (command_id, "66")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    if device_init_state != tango.DevState.ON:
        change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    assert base_device.longRunningCommandStatus == (command_id, "COMPLETED")
    assert base_device.longRunningCommandsInQueue == ()
    assert base_device.longRunningCommandIDsInQueue == (command_id,)


@pytest.mark.parametrize(
    "device_init_state",
    [
        tango.DevState.ON,
        tango.DevState.OFF,
        tango.DevState.FAULT,
        tango.DevState.STANDBY,
        tango.DevState.UNKNOWN,
    ],
)
def test_turn_off(base_device, change_event_callbacks, device_init_state):
    """Test device sets current off request"""
    base_device.forcestate(device_init_state)
    if device_init_state != tango.DevState.OFF:
        change_event_callbacks.assert_change_event("state", device_init_state)
    [[result_code], [command_id]] = base_device.Off()
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", (command_id, "33")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", (command_id, "66")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "COMPLETED")
    )
    if device_init_state != tango.DevState.OFF:
        change_event_callbacks.assert_change_event("state", tango.DevState.OFF)


@pytest.mark.parametrize(
    "device_init_state",
    [
        tango.DevState.INIT,
        tango.DevState.FAULT,
    ],
)
def test_on_not_allowed_commmands(
    base_device, device_init_state, change_event_callbacks
):
    base_device.forcestate(device_init_state)
    change_event_callbacks.assert_change_event("state", device_init_state)

    with pytest.raises(tango.DevFailed):
        base_device.On()


@pytest.mark.parametrize(
    "device_init_state",
    [
        tango.DevState.INIT,
    ],
)
def test_off_not_allowed_commmands(
    base_device, device_init_state, change_event_callbacks
):
    base_device.forcestate(device_init_state)
    change_event_callbacks.assert_change_event("state", device_init_state)

    with pytest.raises(tango.DevFailed):
        base_device.On()
