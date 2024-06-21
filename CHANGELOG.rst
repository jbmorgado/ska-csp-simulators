###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

Latest pre-release
------------------

0.4.0
------------------
- Update ska-tango-base to 1.0.0 (to use new ska-control-model package)
- update charts
    - ska-tango-util v 0.4.11
    - ska-tango-base v 0.4.10
- update simulators to use version 0.3.1

0.3.1
------------------
- Set events to always pushing
- Remove lint and test jobs for notebooks (not used in the project)
- Update dependencies

0.3.0
------------------
- Fix some wrong behaviors of the simulators.
- Modified Restart command in PST Beam to set the end observing
state to IDLE (not EMPTY)
- Changed the Low CBF subarray to support adminMode change.
- Added ConfigureScan command to PSS Subarray.
- Update Mid Helm charts to deploy PST Beams.

0.2.0
-----
- Implementation of the is_XXX_allowed methods for the commands.

0.1.0
-----
- First implementation of ska-csp-simulators as a separate project
