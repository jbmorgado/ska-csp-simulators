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