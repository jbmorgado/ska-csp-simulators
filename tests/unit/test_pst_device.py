# pylint: disable=redefined-outer-name
# -*- coding: utf-8 -*-
"""
Some simple unit tests of the PowerSupply device, exercising the device from
another host using a DeviceProxy.
"""
import json
import logging
import time

import pytest
import tango
from ska_control_model import (
    AdminMode,
    HealthState,
    ObsMode,
    ObsState,
    ResultCode,
)

from ska_csp_simulators.common.pst_beam_simulator import (
    PstBeamSimulatorDevice,
    PstObservationMode,
)
from ska_csp_simulators.DevFactory import DevFactory

module_logger = logging.getLogger(__name__)


@pytest.fixture()
def devices_to_load():
    return (
        {
            "class": PstBeamSimulatorDevice,
            "devices": [
                {
                    "name": "sim-pst/beam/01",
                },
            ],
        },
    )


@pytest.fixture
def pst_device(tango_context):
    """Create DeviceProxy for tests"""
    logging.info("%s", tango_context)
    dev_factory = DevFactory()

    return dev_factory.get_device("sim-pst/beam/01")


@pytest.fixture(autouse=True)
def pst_device_online(pst_device, change_event_callbacks):
    for attribute in [
        "state",
        "adminMode",
        "healthState",
        "obsState",
        "obsMode",
        "observationMode",
        "channelBlockConfiguration",
        "longRunningCommandProgress",
        "longRunningCommandStatus",
        "longRunningCommandResult",
    ]:
        pst_device.subscribe_event(
            attribute,
            tango.EventType.CHANGE_EVENT,
            change_event_callbacks[attribute],
        )
    change_event_callbacks.assert_change_event("state", tango.DevState.DISABLE)
    change_event_callbacks.assert_change_event("adminMode", AdminMode.OFFLINE)
    change_event_callbacks.assert_change_event("healthState", HealthState.OK)
    change_event_callbacks.assert_change_event("obsState", ObsState.IDLE)
    change_event_callbacks.assert_change_event("obsMode", ObsMode.IDLE)
    change_event_callbacks.assert_change_event(
        "observationMode", PstObservationMode.PULSAR_TIMING
    )
    change_event_callbacks.assert_change_event(
        "channelBlockConfiguration", "{}"
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandProgress", ()
    )
    change_event_callbacks.assert_change_event("longRunningCommandStatus", ())
    change_event_callbacks.assert_change_event(
        "longRunningCommandResult", ("", "")
    )
    pst_device.adminmode = 0
    change_event_callbacks.assert_change_event("adminMode", AdminMode.ONLINE)
    change_event_callbacks.assert_change_event("state", tango.DevState.OFF)


def test_pst_beam_configure(pst_device, change_event_callbacks):
    """Test configure request on PST Beam"""
    # load the cahnnel block configuration from a data file. This  file
    # is the same used by the PST simulator during beam configuration.
    f = open(
        "./tests/test_data/pst_channel_block_config.json",
        "r",
        encoding="utf-8",
    )
    channel_config = f.read().replace("\n", "")
    pst_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    pst_device.forceobsstate(ObsState.READY)
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)
    [[result_code], [command_id]] = pst_device.Configure('{"subarray_id":1}')
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
    time.sleep(0.2)
    assert json.loads(pst_device.channelBlockConfiguration) == json.loads(
        channel_config
    )


@pytest.mark.parametrize(
    "init_obs_state",
    [
        ObsState.ABORTED,
        ObsState.FAULT,
    ],
)
def test_pst_beam_restart(pst_device, init_obs_state, change_event_callbacks):
    """Test obsreset request on PST Beam"""
    pst_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    pst_device.forceobsstate(init_obs_state)
    change_event_callbacks.assert_change_event("obsState", init_obs_state)
    [[result_code], [command_id]] = pst_device.ObsReset()
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event("obsState", ObsState.RESETTING)
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


def test_beam_configure_not_allowed_in_wrong_state(pst_device):
    """Test beaam configure not allowed in wrong state"""
    assert pst_device.state() == tango.DevState.OFF
    with pytest.raises(tango.DevFailed):
        pst_device.ConfigureScan('{"subarray_id":1}')


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
def test_beam_configure_not_allowed_in_wrong_obs_state(
    pst_device, device_init_obs_state, change_event_callbacks
):
    """Test beam configure not allowed in wrong observing state"""
    pst_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    pst_device.forceobsstate(device_init_obs_state)
    change_event_callbacks.assert_change_event(
        "obsState", device_init_obs_state
    )
    with pytest.raises(tango.DevFailed):
        pst_device.ConfigureScan('{"subarray_id":1}')


def test_pst_beam_scan(pst_device, change_event_callbacks):
    """Test scan request on PST Beam"""
    # load the cahnnel block configuration from a data file. This  file
    # is the same used by the PST simulator during beam configuration.
    pst_device.forcestate(tango.DevState.ON)
    change_event_callbacks.assert_change_event("state", tango.DevState.ON)
    pst_device.forceobsstate(ObsState.READY)
    change_event_callbacks.assert_change_event("obsState", ObsState.READY)
    [[result_code], [command_id]] = pst_device.Scan('{"subarray_id":1}')
    assert result_code == ResultCode.QUEUED
    change_event_callbacks.assert_change_event("obsState", ObsState.SCANNING)
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "STAGING")
    )
    change_event_callbacks.assert_change_event(
        "longRunningCommandStatus", (command_id, "IN_PROGRESS")
    )
