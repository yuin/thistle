from __future__ import print_function
import os.path
from thistle import *

log_file = os.path.join(PATH, "dat", "thistle.log")
def setup_logger():
  import logging, logging.handlers, subprocess
  LOGGER.setLevel(logging.DEBUG)
  host=subprocess.check_output("hostname").strip()
  log_format="%(asctime)s "+host+" %(name)s[%(process)s]: %(levelname)s: %(message)s"
  formatter = logging.Formatter(log_format)
  trh = logging.handlers.TimedRotatingFileHandler(filename=log_file, when='W0', backupCount=10)
  trh.setFormatter(formatter)
  LOGGER.addHandler(trh)
setup_logger()

def log_message(level, message, *args):
  LOGGER.log(level, message)

Monitor.DEFAULT_CONFIG.update({
  "callback": {
    Monitor.EVENT_CRIT:  [log_message],
    Monitor.EVENT_ERROR: [log_message],
    Monitor.EVENT_WARN:  [log_message],
    Monitor.EVENT_INFO:  [log_message]
  }
})

config = {
  "pid_file": os.path.join(PATH, "dat", "thistle.pid"),
  "monitors": [
    ProcessMonitor({
      "interval": 10,
      "targets": [
        {"name": "sleep process",
         "pattern": ".*sleep.*",
         "min": 1,
         "max": 1}
      ]
    }),
    CommandOutputVarMonitor({
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
  ]
}

