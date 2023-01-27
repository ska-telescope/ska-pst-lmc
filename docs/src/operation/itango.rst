.. _operation_itango:

.. raw:: html

    <style> .red {color:red} </style>

.. role:: red

Using itango
============

Start up and set up
-------------------

Start an iTango session:

.. code-block:: console

    $ kubectl exec -it ska-tango-base-itango-console -- itango3

List the Tango devices:

.. code-block:: python

    In [1]: lsdev

.. code-block:: none

    Device                Alias  Server                    Class
    --------------------- ------ ------------------------- --------------------
    low-pst/beam/01              low-pst-beam/01           PstBeam
    low-pst/dsp/01               low-pst-beam/01           PstDsp
    low-pst/recv/01              low-pst-beam/01           PstReceive
    low-pst/smrb/01              low-pst-beam/01           PstSmrb
    sys/access_control/1         TangoAccessControl/1      TangoAccessControl
    sys/database/2               DataBaseds/2              DataBase
    sys/rest/0                   TangoRestServer/rest      TangoRestServer
    sys/tg_test/1                TangoTest/test            TangoTest

This interface allows direct interaction with the devices, such as querying and
changing attributes and issuing Tango commands to control pst processing. 

To set things up and turn the beam on, cut and paste the following commands into the itango terminal:

.. code-block:: python

    beam = DeviceProxy('low-pst/beam/01')

    # utility method to display monitoring params
    def display_monitoring(beam):
        print(f"received rate: {beam.dataReceiveRate}")
        print(f"received bytes: {beam.dataReceived}")
        print(f"dropped rate: {beam.dataDropRate}")
        print(f"dropped bytes: {beam.dataDropped}")
        print(f"write rate: {beam.dataRecordRate}")
        print(f"written bytes: {beam.dataRecorded}")
        print(f"disk available bytes: {beam.availableDiskSpace}")
        print(f"disk available time: {beam.availableRecordingTime}")
        print(f"ring buffer utilisation: {beam.ringBufferUtilisation}")
    
    # set logging level to DEBUG
    beam.loggingLevel = 5

    # set BEAM into AdminMode.ONLINE
    beam.adminMode = 0

    # set BEAM into SimulationMode.TRUE
    beam.simulationMode = 1
    
    # Turn on BEAM
    beam.On()

The last line should result in an output message like the following

.. code-block:: python

    [array([2], dtype=int32), ['1673570914.504404_276635284857679_On']]

Configure a scan
----------------

The argument of the ``ConfigureScan`` command is a
configuration string that sets the mode of
operation and provides the values of various required attributes.

To obtain a valid example of a configuration string,
visit `ska-csp-configure <https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html>`_
and expand the `Example (CSP configuration for PST pulsar timing scan)`, then highlight and copy the entire block of
text that appears below this heading.  Paste this block of text as indicated in the following block of code, then
execute this code in the itango terminal.

.. code-block:: python

    import json
    scan_configuration = json.dumps( <paste configure string here> )
    beam.ConfigureScan(scan_configuration)

Check the state (should be ``<obsState.READY: 4>``):

.. code-block:: python

    beam.obsState

Check the configuration ID (should be ``'sbi-mvp01-20200325-00001-science_A'``):

.. code-block:: python

    beam.configurationId

Check the scan ID (should be ``0``):

.. code-block:: python

    beam.scanId

Start and stop a scan
---------------------

First, display the monitoring statistics and confirm that they are in the initial state:

.. code-block:: python

    display_monitoring(beam)

.. code-block:: none

    received rate: 0.0
    received bytes: 0
    dropped rate: 0.0
    dropped bytes: 0
    write rate: 0.0
    written bytes: 0
    disk available bytes: 251758821376
    disk available time: 31536000.0
    ring buffer utilisation: 0.0

Start a (simulated) scan and display (fake) monitoring statistics:

.. code-block:: python

    beam.Scan("1")
    display_monitoring(beam)

.. code-block:: none

    received rate: 154.0
    received bytes: 19250000000
    dropped rate: 0.09227995411094783
    dropped bytes: 11534992
    write rate: 2937349865.8648005
    written bytes: 2937349864
    disk available bytes: 248821487896
    disk available time: 84.70951682929442
    ring buffer utilisation: 0.0

Check the state (should be ``<obsState.SCANNING: 5>``):

.. code-block:: python

    beam.obsState

Stop the scan:

.. code-block:: python

    beam.EndScan()

Check the state (should be ``<obsState.READY: 4>``):

.. code-block:: python

    beam.obsState

Deconfigure the scan and return to the idle state:

.. code-block:: python

   beam.GoToIdle()

Check the state (should be ``<obsState.IDLE: 2>``):

.. code-block:: python

    beam.obsState

