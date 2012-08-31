#!/usr/bin/env python
#vim: fileencoding=utf8
from __future__ import print_function
import os, os.path, sys, re
import unittest

FILE_PATH = os.path.abspath(__file__)
if os.path.islink(FILE_PATH):
  FILE_PATH = os.readlink(FILE_PATH)
TEST_DIR = os.path.dirname(FILE_PATH)
sys.path.insert(0, os.path.dirname(TEST_DIR))

from thistle import *
thistle = sys.modules["thistle"]

# BASE_CONFIG {{{ 
thistle.DBThread.db_file = TEST_DIR+"/thistle.db"
def setup_logger():
  log_file = TEST_DIR + "/thistle.log"
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

Monitor.DEFAULT_ATTRS.update({
  "callback": {
    Event.ERROR: [log_message],
    Event.WARN:  [log_message],
    Event.INFO:  [log_message]
  }
})

BASE_CONFIG = {
  "pid_file": TEST_DIR + "/thistle.pid",
  "waiting_time_on_boot": 0
}

# }}}

Match = re.compile("").__class__
def line_contains(lines, pattern):
  result = []
  for line in lines:
    if pattern.__class__ == Match and pattern.match(line):
      result.append(line)
    elif pattern in line:
      result.append(line)
  return result

def read_logcontent():
  return p_out("cat "+TEST_DIR+"/thistle.log").splitlines()

def test_with(setup, teardown):
  def _(f):
    def __(self):
      setup(self)
      try:
        f(self)
      except:
        teardown(self)
        raise
    __.__name__ = f.__name__
    return __
  return _

def remove_file_without_exc(file):
  try:
    os.remove(file)
  except:
    pass

class BaseTestCase(unittest.TestCase):
  def setUp(self):
    remove_file_without_exc(TEST_DIR + "/thistle.log")
    setup_logger()

  def tearDown(self):
    remove_file_without_exc(TEST_DIR + "/thistle.log")
    remove_file_without_exc(TEST_DIR + "/thistle.pid")
    remove_file_without_exc(thistle.DBThread.db_file)
    remove_file_without_exc(TEST_DIR + "/monitor.log")

# Event {{{
class TestEvent(unittest.TestCase):
  def test_level_names(self):
    self.assertTrue("CRIT" == Event.as_string(Event.CRIT))
    self.assertTrue("ERROR" == Event.as_string(Event.ERROR))
    self.assertTrue("WARN" == Event.as_string(Event.WARN))
    self.assertTrue("INFO" == Event.as_string(Event.INFO))

  def test_add_new_level(self):
    Event.add_new_level("MAJOR", Event.ERROR+1)
    self.assertTrue(Event.MAJOR == Event.ERROR+1)
    self.assertTrue("MAJOR" == Event.as_string(Event.MAJOR))

  def test_define_levels(self):
    Event.define_levels({
      "LEVEL1": Event.ERROR+2, 
      "LEVEL2": Event.ERROR+3, 
    })
    self.assertTrue(Event.LEVEL1 == Event.ERROR+2)
    self.assertTrue("LEVEL1" == Event.as_string(Event.LEVEL1))
    self.assertTrue(Event.LEVEL2 == Event.ERROR+3)
    self.assertTrue("LEVEL2" == Event.as_string(Event.LEVEL2))
# }}}

# ProcessMonitor {{{
class DummyProcessMonitorSleep2(ProcessMonitor):
  def get_process_list(self): return ["sleep", "sleep"]
class DummyProcessMonitorSleep1(ProcessMonitor):
  def get_process_list(self): return ["sleep"]

class DummyProcessMonitorSleepIncrement(ProcessMonitor):
  def __init__(self, *args):
    ProcessMonitor.__init__(self, *args)
    self.__count = 0
  def get_process_list(self): 
    self.__count += 1
    return ["sleep"] * self.__count

class TestProcessMonitor(BaseTestCase):
  def test_max_error(self):
    config = BASE_CONFIG.copy()
    config.update({
      "monitors": [
        (DummyProcessMonitorSleep2, {
          "interval": 3,
          "targets": [
            {"name": "sleep process",
             "pattern": ".*sleep.*",
             "min": 1,
             "max": 1}
          ]
        }),
      ]
    })
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(1)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "ERROR: [DummyProcessMonitorSleep2] sleep process: 2 process(> 1)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

  def test_max_warn(self):
    config = BASE_CONFIG.copy()
    config.update({
      "monitors": [
        (DummyProcessMonitorSleep2, {
          "interval": 3,
          "targets": [
            {"name": "sleep process",
             "pattern": ".*sleep.*",
             "min": 1,
             "max": 1,
             "level": Event.WARN
             }
          ]
        }),
      ]
    })
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(1)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "WARN: [DummyProcessMonitorSleep2] sleep process: 2 process(> 1)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

  def test_max_ok(self):
    config = BASE_CONFIG.copy()
    config.update({
      "monitors": [
        (DummyProcessMonitorSleep1, {
          "interval": 3,
          "targets": [
            {"name": "sleep process",
             "pattern": ".*sleep.*",
             "min": 1,
             "max": 1}
          ]
        }),
      ]
    })
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(1)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "ERROR"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 0)

  def test_min_warn(self):
    config = BASE_CONFIG.copy()
    config.update({
      "monitors": [
        (DummyProcessMonitorSleep2, {
          "interval": 3,
          "targets": [
            {"name": "sleep process",
             "pattern": ".*sleep.*",
             "min": 3,
             "max": 10,
             "level": Event.WARN}
          ]
        }),
      ]
    })
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(1)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "WARN: [DummyProcessMonitorSleep2] sleep process: 2 process(< 3)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

  def test_resume_normal_operations(self):
    config = BASE_CONFIG.copy()
    config.update({
      "monitors": [
        (DummyProcessMonitorSleepIncrement, {
          "interval": 3,
          "targets": [
            {"name": "sleep process",
             "pattern": ".*sleep.*",
             "min": 2,
             "max": 10,
             "level": Event.WARN}
          ]
        }),
      ]
    })
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(10)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "WARN: [DummyProcessMonitorSleepIncrement] sleep process: 1 process(< 2)."
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    expected_log = "INFO: [DummyProcessMonitorSleepIncrement] sleep process: Resume normal operations."
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

# }}}

# CommandOutputVarMonitor {{{
class DummyCommandOutputVarMonitor100(CommandOutputVarMonitor):
  def get_values(self): return {"CPU_USAGE":100, "MEM_USAGE": 90}

class DummyCommandOutputVarMonitor100to90(CommandOutputVarMonitor):
  def __init__(self, *args): 
    self.__count = 0
    CommandOutputVarMonitor.__init__(self, *args)

  def get_values(self): 
    self.__count += 1
    if self.__count < 3:
      return {"CPU_USAGE":100, "MEM_USAGE": 90}
    else:
      return {"CPU_USAGE":90, "MEM_USAGE": 80}

class TestCommandOuputVarMonitor(BaseTestCase):
  def test_gt_error(self):
    config = BASE_CONFIG.copy()
    def test_logger(log):
      self.assertTrue(re.search("CPU_USAGE:100 MEM_USAGE:90", log) is not None)

    config.update({
      "monitors": [
        (DummyCommandOutputVarMonitor100, {
          "interval": 3,
          "command": "none",
          "logger": test_logger,
          "targets": [
            {"name": "CPU_USAGE",
             "gt": 90},
            {"name": "MEM_USAGE",
             "gt": 80,
             "level": Event.WARN}
          ]
        }),
      ]
    })
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(1)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "ERROR: [DummyCommandOutputVarMonitor100] CPU_USAGE: 100 (> 90)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    expected_log = "WARN: [DummyCommandOutputVarMonitor100] MEM_USAGE: 90 (> 80)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

  def test_lt_error(self):
    config = BASE_CONFIG.copy()
    config.update({
      "monitors": [
        (DummyCommandOutputVarMonitor100, {
          "interval": 3,
          "command": "none",
          "targets": [
            {"name": "CPU_USAGE",
             "lt": 101},
            {"name": "MEM_USAGE",
             "lt": 91,
             "level": Event.WARN}
          ]
        }),
      ]
    })
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(1)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "ERROR: [DummyCommandOutputVarMonitor100] CPU_USAGE: 100 (< 101)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    expected_log = "WARN: [DummyCommandOutputVarMonitor100] MEM_USAGE: 90 (< 91)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

  def test_ne_error(self):
    config = BASE_CONFIG.copy()
    config.update({
      "monitors": [
        (DummyCommandOutputVarMonitor100, {
          "interval": 3,
          "command": "none",
          "targets": [
            {"name": "CPU_USAGE",
             "ne": 101},
            {"name": "MEM_USAGE",
             "ne": 91,
             "level": Event.WARN}
          ]
        }),
      ]
    })
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(1)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "ERROR: [DummyCommandOutputVarMonitor100] CPU_USAGE: 100 (!= 101)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    expected_log = "WARN: [DummyCommandOutputVarMonitor100] MEM_USAGE: 90 (!= 91)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

  def test_resume_normal_operations(self):
    config = BASE_CONFIG.copy()
    config.update({
      "monitors": [
        (DummyCommandOutputVarMonitor100to90, {
          "interval": 2,
          "command": "none",
          "targets": [
            {"name": "CPU_USAGE",
             "gt": 90},
            {"name": "MEM_USAGE",
             "gt": 80,
             "level": Event.WARN}
          ]
        }),
      ]
    })
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(8)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "ERROR: [DummyCommandOutputVarMonitor100to90] CPU_USAGE: 100 (> 90)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    expected_log = "WARN: [DummyCommandOutputVarMonitor100to90] MEM_USAGE: 90 (> 80)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    expected_log = "INFO: [DummyCommandOutputVarMonitor100to90] CPU_USAGE: Resume normal operations."
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    expected_log = "INFO: [DummyCommandOutputVarMonitor100to90] MEM_USAGE: Resume normal operations."
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

# }}}
    
# LogMonitor {{{
class TestLogMonitor(BaseTestCase):
  def test_log_monitor(self):
    config = BASE_CONFIG.copy()
    config.update({
      "monitors": [
        (LogMonitor, {
          "interval": 3,
          "file": TEST_DIR + "/monitor.log",
          "targets": [
            {"pattern": ".*hoge.*",
             "message": "hoge has occurred."},
            {"pattern": ".*warn.*",
             "message": "foo has occurred.",
             "level": Event.WARN}
          ]
        }),
      ]
    })

    with open(TEST_DIR+"/monitor.log", "w") as io:
      io.write("hoge\n")
      io.write("foo\n")
      io.write("bar\n")
      io.write("bar\n")

    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(3)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "hoge has occurred.(hoge)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    
    # seeks forward to our previous saved positions.
    #   => no more errors.
    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(3)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "hoge has occurred.(hoge)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

    # truncates the log file
    with open(TEST_DIR+"/monitor.log", "w") as io:
      io.write("warn1\n")
      io.write("warn2\n")
      io.write("bar\n")

    thistle.KERNEL = thistle.Kernel(config)
    thistle.KERNEL.start(loop=False)
    time.sleep(2)
    with open(TEST_DIR+"/monitor.log", "w") as io:
      io.write("warn3\n")
    time.sleep(4)
    thistle.KERNEL.shutdown()
    log_content = read_logcontent()
    expected_log = "truncated"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 2)
    expected_log = "foo has occurred.(warn1)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    expected_log = "foo has occurred.(warn2)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)
    expected_log = "foo has occurred.(warn3)"
    self.assertTrue(len(line_contains(log_content, expected_log)) == 1)

# }}}

if __name__ == '__main__':
  suite = unittest.TestLoader().loadTestsFromModule(sys.modules["__main__"])
  unittest.TextTestRunner(verbosity=2).run(suite)
