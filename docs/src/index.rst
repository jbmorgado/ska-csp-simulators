.. skeleton documentation master file, created by
   sphinx-quickstart on Thu May 17 15:17:35 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SKA CSP Simulators 
==================

This project creates a set of TANGO Devices working as simulators of the CSP subordinate sub-systems.
The use of simulators allows us to test the CSP.LMC system under conditions that are difficult to
reproduce with real devices, but can be easily induced in simulated devices.

Another use of simulators involves the possibility of instantiating a more complex CSP system, with
a greater number of subordinate devices, including the PSS subsystem which is not yet available.
This way, we can also analyze how the system behaves in terms of scalability, reliability, and
responsiveness.



Simulators are implemented starting with two base devices that were subsequently specialized
to give rise to the ecosystem of devices for the subsystems of both the Low and Mid versions of CSP.
The simulators implement the same basic set of attributes and modes as the SKA Base classes, 
as well as the same set of commands.
Additionally, they replicate the initial state of the devices in the Mid and Low subsystems.
Similarly, the commands replicate the behavior of commands executed on real devices.

Through the configuration of certain TANGO attributes, the simulators can alter their behavior
and generate anomalous conditions, such as command failure, raising an exception, etc.
It is also possible to force the device into a specific state through the execution of some 
TANGO commands.

The table Below reports the list of attributes and commands that allow injecting errors into the various
subsystems of the CSP

- faulty
- raiseException
- obsFaulty
- ForceState
- ForceHealthState
- ForceObsState

.. list-table::
   :widths: 15 35 10 5 35
   :header-rows: 1

   * - Name
     - Description
     - Type
     - R/W
     - Example
   * - faultyInCommand
     - injects a failure during the execution of a command
     - bool
     - R/W
     - Default value False
   * - obsFaulty  
     - when set, simulate the generation of a FAULT condition in the observing state of the device during the execution of a command. This is implemented only in subarray and pst bean devices.
     - bool
     - R/W
     - Default value is False. This flag is reset executing the Restart command,
   * - raiseException
     - when set, the first execution of a command fails raising an exception.
     - bool
     - R/W
     - default value False
   
.. list-table::
   :widths: 15 25 15 25
   :header-rows: 1

   * - Command name
     - Description
     - Parameters
     - Note
   * - *ForceState*
     - Set the state to the specified value and push a change event.
     - The desired State value
     -
   * - *ForceHealthState*
     - Set the health state to the specified value and push a change event.
     - The desired hralthState value
     -
   * - *ForceObsState*
     - Set the observing state to the specified value and push a change event.
     - The desired observing state value
     -

The simulators
**************
The project provides simulators for the Mid and Low CSP sub-systems.
The deployed devices are those specified in the *values.yaml* of the *ska-csp-simulatos* Helm chart
and reported in the tables below:

.. list-table::
   :widths: 40 50
   :header-rows: 1

   * - Device type
     - Device fqdn
     
   * - *Mid Controller*
     - sim-mid-cbf/control/0
   * - *Mid Subarray 1*
     - sim-mid-cbf/subarray/01
   * - *Mid Subarray 2*
     - sim-mid-cbf/subarray/02
   * - *Mid Subarray 3*
     - sim-mid-cbf/subarray/03

.. list-table::
   :widths: 40 50
   :header-rows: 2

   * - Device type
     - Device fqdn
     
   * - *Low Controller*
     - sim-low-cbf/control/0
   * - *Low Subarray 1*
     - sim-low-cbf/subarray/01
   * - *Low Subarray 2*
     - sim-low-cbf/subarray/02
   * - *Low Subarray 3*
     - sim-low-cbf/subarray/03
   * - *Low PstBeam 1*
     - sim-low-pst/beam/01


Examples
********
To operate and manage the Low and Mid simulators using itango3, a proxy must be established
for the devices. Here,we provide an example for the Mid simulators, but the same principles
apply to the Low ones as well.
::
    
    cbf_ctrl = Device('sim-mid-cbf/control/0')
    cbf_sub1 = Device('sim-mid-cbf/subarray/01')

The default status of the simulators reflects the status of the corresponding ral devices:

- state DISABLE.
- healthState UNKNOWN
- adminMode OFFLINE
- obstState EMPTY (subarrays)

To start the communication use the following command::
    
    cbf_ctrl.adminMode = 0
    cbf_sub1.adminMode = 0

Force a device in a different state::

  cbf_ctrl.ForceState(DevState.FAULT)
  cbf_sub1.ForceState(DevState.OFF)

Force a device in a different health state::

  cbf_ctrl.ForceHealthState(HealthState.DEGRADED)
  cbf_sub1.ForceHealthState(HealthState.FAILED)

Force a device in a different observing state::

  cbf_sub1.ForceObsState(ObsState.FAULT)


Force an exception at command esecution::

  In [1]: cbf_sub1.raiseException = True
  In [2]: cbf_sub1.Configure("...")
  PyDs_PythonError: ValueError: Error in executing command

  (For more detailed information type: tango_error)

Inject a generic failure during the execution of a command::

  In [11] cbf_sub1.faultyInCommand = True
  In [12]: cbf_sub1.On()
  Out[12]: [array([2], dtype=int32), ['1712835893.3101838_68202739659046_On']]
  In [13]:  cbf_sub1.longrunningCommandStatus
  Out[13]: ('1712835893.3101838_68202739659046_On', 'COMPLETED')
  In [14]: cbf_sub1.longrunningCommandResult
  Out[14]: ('1712835893.3101838_68202739659046_On', '3')

Set the time of execution of a command::

  In [15]: cbf_sub1.timeToComplete =5

The successive command issued on the subarray takes up to 5 sec to complete.

Force generation of FAULT  in the observing state during the execution of a command::

  In [16]: cbf_sub1.obsFaulty = True
  In [17]: cbf_sub1.Scan('{subarray_id":1}')
  Out[17]: [array([2], dtype=int32), ['1712838030.4151556_138953440081808_scan']]
  In [18]:  cbf_sub1.longrunningCommandStatus
  Out[18]: ('1712838030.4151556_138953440081808_scan', 'COMPLETED')
  In [19]: cbf_sub1.longrunningcommandresult
  Out[19]: ('1712838030.4151556_138953440081808_scan', '3')
  In [20]: cbf_sub1.obsstate
  Out[20]: <obsState.FAULT: 9>
  In [21]: cbf_sub1.restart()
  Out[21]: [array([2], dtype=int32), ['1712838194.3179753_51746492240993_restart']]
  In [22]: cbf_sub1.obsstate
  Out[22]: <obsState.EMPTY: 0>
  In [23]: cbf_sub1.obsFaulty
  Out[23]: False

