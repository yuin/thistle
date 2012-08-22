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
    runs a given command and monitors its output whether value is output the required ranges.

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
      "vars": [
        {"name" : "CPU_USAGE",
         "gt_e" : 95,
         "gt_w" : 85
        },
        {"name" : "MEM_USAGE",
         "gt_e" : 95,
         "gt_w" : 85
        },
        {"name" : "DISK_USAGE_/",
         "gt_e" : 95,
         "gt_w" : 85
        },
      ]
    })

:interval: Monitoring interval(secs).
:command:  Command to get informations.
:vars:     List of variable definitions.
:name:     Variable name.
:gt_e:     Maximum threshold for the variable value.(ERROR)
:gt_w:     Maximum threshold for the variable value.(WARN)
:lt_e:     Minimum threshold for the variable value.(ERROR)
:lt_w:     Minimum threshold for the variable value.(WARN)
:ne:       A value that the variable should have same value.(ERROR)


LogMonitor
+++++++++++++++++++++++++

::


    (LogMonitor, {
      "interval": 10,
      "file": "/home/foo/test1.log",
      "targets": [
        {"pattern": ".*warn.*",
         "message": "foo has occurred.",
         "level": Monitor.EVENT_WARN}
      ]
    })

:interval: Monitoring interval(secs).
:file:     A file to monitor.
:targets:  List of line patterns.
:patterns: Regular expressions to match line.
:message:  A message if a line matches the regular expressions.
:level:    An event level.(default `Monitor.EVENT_ERROR`)


