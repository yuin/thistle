from __future__ import print_function
import os.path
from thistle import *
import thistle.plugins.mailnotification

def setup_logger():
  log_file = "/var/log/thistle/thistle.log"
  import logging, logging.handlers, subprocess
  LOGGER.setLevel(logging.DEBUG)
  host=subprocess.check_output("hostname").strip()
  log_format="%(asctime)s "+host+" %(name)s[%(process)s]: %(levelname)s: %(message)s"
  formatter = logging.Formatter(log_format)
  trh = logging.handlers.TimedRotatingFileHandler(filename=log_file, when='W0', backupCount=10)
  trh.setFormatter(formatter)
  LOGGER.addHandler(trh)
setup_logger()

def command_logger(log_file):
  import logging, logging.handlers
  logger = logging.getLogger(log_file)
  logger.setLevel(logging.INFO)
  formatter = logging.Formatter("%(message)s")
  trh = logging.handlers.TimedRotatingFileHandler(filename=log_file, when='midnight', backupCount=10)
  trh.setFormatter(formatter)
  logger.addHandler(trh)
  return logger.info

def log_message(level, message, target):
  LOGGER.log(level, message)

email_notification = thistle.plugins.mailnotification.SmtpMailNotification(
  host="smtp.gmail.com",
  port=587,
  user="your address",
  password="your password",
  from_addr="from_addr",
  to_addr="to_addr"
)

Monitor.DEFAULT_ATTRS.update({
  "callback": {
    Event.ERROR: [log_message, email_notification],
    Event.WARN:  [log_message],
    Event.INFO:  [log_message]
  }
})

Event.define_levels({
  "MAJOR": Event.ERROR+1
})

config = {
  "pid_file": "/var/run/thistle.pid",
  "waiting_time_on_boot": 5,
  "monitors": [
    (ProcessMonitor, {
      "interval": 300,
      "targets": [
        {"name": "sleep process",
         "pattern": ".*sleep.*",
         "min": 1,
         "max": 1}
      ]
    }),
    (CommandOutputVarMonitor, {
      "interval": 300,
      "logger": command_logger("/var/log/thistle/sysinfo.log"),
      "command" : [os.path.join(PATH, "plugins", "sysinfo.sh")],
      "targets": [
        {"name" : "CPU_USAGE",
         "gt" : 95 },
        {"name" : "CPU_USAGE",
         "gt" : 85 ,
         "level": Event.WARN},
        {"name" : "MEM_USAGE",
         "gt" : 90 },
        {"name" : "MEM_USAGE",
         "gt" : 80 ,
         "level": Event.WARN},
      ]
    }),
    (LogMonitor, {
      "interval": 300,
      "file": "/home/foo/test.log",
      "encoding": "utf8",
      "targets": [
        {"pattern": ".*error.*",
         "message": "error has occurred."},
        {"pattern": ".*warn.*",
         "message": "warn has occurred.",
         "level": Event.WARN}
      ]
    }),
    (LogMonitor, {
      "interval": 300,
      "file": "/home/foo/test1.log",
      "encoding": "utf8",
      "targets": [
        {"pattern": ".*hoge.*",
         "message": "hoge has occurred."},
        {"pattern": ".*warn.*",
         "message": "foo has occurred.",
         "level": Event.WARN}
      ]
    })
  ]
}

