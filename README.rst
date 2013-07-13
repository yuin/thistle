thistle
=======================================

* thistle is a simple server monitoring app.

Requirements
---------------------------------------

* Python2.7

Installation
---------------------------------------

::

    git clone git://github.com/yuin/thistle.git
    sudo cp -R thistle /opt/thistle
    cd /opt/thistle
    sudo ./setup.sh install

    (edit your /etc/thistle/config.py)

    service thistle start

Uninstallation
---------------------------------------

::

    sudo service thistle stop
    cd /opt/thistle
    ./setup.sh uninstall

Configuration
---------------------------------------
Monitors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
thistle has 3 monitors.:

ProcessMonitor
    monitors processes whether the number of processes is outside the required threshold ranges.

CommandOutputVarMonitor
    runs a given command and monitors its output whether value is outside the required ranges.

LogMonitor
    checks a given log file to match regular expressions.


ProcessMonitor
+++++++++++++++++++++++++

::

    (ProcessMonitor, {
      "interval": 10,
      "targets": [
        {"name": "sleep process",
         "pattern": ".*sleep.*",
         "min": 1,
         "max": 1}
      ]
    })


:interval: Monitoring interval(secs).
:targets:  List of processes to monitor.
:name:     Plain name, used in log messages.
:pattern:  Regular expressions for this process.
:min:      Minimum threshold for the number of processes.
:max:      Maximum threshold for the number of processes.


CommandOutputVarMonitor
+++++++++++++++++++++++++
"command" must generate standard outputs like "VARNAME=VALUE". The plugins/sysinfo.sh generates standard outputs like the following::

    CPU_USAGE=0
    LOAD_AVERAGE_1=0.00
    LOAD_AVERAGE_5=0.00
    LOAD_AVERAGE_15=0.00
    MEM_USAGE=29
    DISK_USAGE_/=17
    DISK_USAGE_/boot=13
    DISK_USAGE_/dev/shm=0

::

    (CommandOutputVarMonitor, {
      "interval": 10,
      "command" : [os.path.join(PATH, "plugins", "sysinfo.sh")],
      "logger"  : sys.stdout.write,
      "vars": [
        {"name" : "CPU_USAGE",
         "gt" : 95 },
        {"name" : "CPU_USAGE",
         "gt" : 85 
         "level": Event.WARN},
        {"name" : "MEM_USAGE",
         "gt" : 90 },
        {"name" : "MEM_USAGE",
         "gt" : 80 
         "level": Event.WARN},
      ]
    })

:interval: Monitoring interval(secs).
:command:  Command to get informations.
:logger:   Python function that write command output to the files. This function takes one string arugment.
:vars:     List of variable definitions.
:name:     Variable name.
:gt:       Maximum threshold for the variable value.
:lt:       Minimum threshold for the variable value.
:ne:       A value that the variable should have same value.
:level:    An event level.(default `Event.ERROR`)


LogMonitor
+++++++++++++++++++++++++

::


    (LogMonitor, {
      "interval": 10,
      "file": "/home/foo/test1.log",
      "encoding": "utf8",
      "targets": [
        {"pattern": ".*warn.*",
         "message": "foo has occurred.",
         "level": Event.WARN}
      ]
    })

:interval: Monitoring interval(secs).
:file:     A file to monitor.
:encoding: A file character encoding.
:targets:  List of line patterns.
:patterns: Regular expressions to match line.
:message:  A message if a line matches the regular expressions.
:level:    An event level.(default `Event.ERROR`)


