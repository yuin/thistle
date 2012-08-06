from __future__ import print_function
import os.path
from thistle import *

log_file=os.path.join(PATH, "dat", "thistle.log")
def log_message(message, *args):
  with open(log_file, "a") as io:
   io.write(message+"\n")

Monitor.DEFAULT_CONFIG.update({
  "callback": {
    Monitor.EVENT_ERROR: [log_message],
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
    })
  ]
}

