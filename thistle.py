#vim: fileencoding=utf8
"""
thistle - A minimal server monitoring tool set for small systems.
===================================================================

Licence (MIT)
-------------

Copyright (c) 2012, Yusuke Inuzuka.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
from __future__ import print_function

__author__ = "Yusuke Inuzuka"
__version__ = "0.1.0"
__license__ = 'MIT'

import os
import os.path
import sys
import re
import codecs
import subprocess
import threading
import signal
import time
import logging

from compat import *

# module globals {{{
STOP_THREAD = "STOP_THREAD"
PATH = os.path.dirname(os.path.abspath(__file__))
LOGGER = logging.getLogger("thistle")
# }}}

class EventThread(threading.Thread): # {{{
  def __init__(self, monitor):
    threading.Thread.__init__(self)
    self.monitor = monitor
    self.queue = queue.Queue()

  def stop(self):
    self.queue.put(STOP_THREAD)
    self.queue.join()

  def run(self):
    while True:
      try:
        next_item = self.queue.get(timeout=10)
        if next_item is STOP_THREAD: 
          self.queue.task_done()
          break
        self.monitor._callback(*next_item)
        self.queue.task_done()
      except queue.Empty:
        pass
# }}}

class Monitor(threading.Thread): # {{{
  EVENT_CRIT  = logging.CRITICAL
  EVENT_ERROR = logging.ERROR
  EVENT_WARN  = logging.WARNING
  EVENT_INFO  = logging.INFO
  DEFAULT_CONFIG = {
      "interval": 300,
      "messages": {},
      "callback": {
        EVENT_CRIT  : [],
        EVENT_ERROR : [],
        EVENT_WARN  : [],
        EVENT_INFO  : []
      }
  }

  def __init__(self, configs):
    threading.Thread.__init__(self)
    self.config = self.default_config()
    for k,v in iter_items(configs):
      self.config[k] = v
    self.init_config()
    self.queue = queue.Queue()
    self.event_thread = EventThread(self)

  def default_config(self):
    return Monitor.DEFAULT_CONFIG.copy()

  def init_config(self): raise NotImplementedError()

  def change_state(self, dct, state, callback_args):
    pre_state = dct["__state__"]
    if pre_state == state:
      return
    dct["__state__"] = state
    message = "["+self.__class__.__name__ + "] " + self.config["messages"][state].format(**dct)
    callback_args.insert(1, message)
    self.callback(*callback_args)

  def init_state(self, dct, value="normal"):
    dct["__state__"] = value

  def _callback(self, *args):
    event_type = args[0]
    for callback in self.config["callback"][event_type]:
      callback(*args)

  def callback(self, *args):
    self.event_thread.queue.put(args)

  def monitor(self): raise NotImplementedError()

  def stop(self):
    self.queue.put(STOP_THREAD)
    self.event_thread.stop()
    self.queue.join()

  def run(self):
    self.event_thread.start()

    while True:
      self.monitor()
      try:
        next_item = self.queue.get(timeout=self.config["interval"])
        if next_item is STOP_THREAD: 
          self.queue.task_done()
          break
        self.queue.task_done()
      except queue.Empty:
        pass

# }}}

class ProcessMonitor(Monitor): # {{{
  def default_config(self):
    config = Monitor.default_config(self)
    config["targets"] = []
    config["messages"]["min"] = "{name}: {__count__:d} process(< {min:d})."
    config["messages"]["max"] = "{name}: {__count__:d} process(> {max:d})."
    config["messages"]["normal"] = "{name}: resume normal operation."
    return config

  def init_config(self):
    for target in self.config["targets"]:
      target["__pattern__"] = re.compile(target["pattern"])
      target["__count__"] = 0
      self.init_state(target)

  def monitor(self):
    processes = subprocess.check_output(["ps", "-ef"]).splitlines()
    for target in self.config["targets"]:
      target["__count__"] = 0
      for process in processes:
        if target["__pattern__"].search(process):
          target["__count__"] += 1
      if target["__count__"] < target["min"]:
        self.change_state(target, "min", [Monitor.EVENT_ERROR, target])
      elif target["__count__"] > target["max"]:
        self.change_state(target, "max", [Monitor.EVENT_ERROR, target])
      else:
        self.change_state(target, "normal", [Monitor.EVENT_INFO, target])
# }}}

class CommandOutputVarMonitor(Monitor): # {{{
  def default_config(self):
    config = Monitor.default_config(self)
    config["vars"] = []
    config["messages"]["gt_e"] = "{name}: {__value__:d} (> {lt_e:d})."
    config["messages"]["lt_e"] = "{name}: {__value__:d} (< {gt_e:d})."
    config["messages"]["gt_w"] = "{name}: {__value__:d} (> {lt_w:d})."
    config["messages"]["lt_w"] = "{name}: {__value__:d} (< {gt_w:d})."
    config["messages"]["ne"] = "{name}: {__value__:d} (!= {ne:d})"
    config["messages"]["command_e"] = "{command} : invalid output. var {name} not found."
    config["messages"]["normal"] = "{name}: resume normal operation."
    return config

  def init_config(self):
    for var in self.config["vars"]:
      self.init_state(var)
      var["__value__"] = 0

  def monitor(self):
    output = subprocess.check_output(self.config["command"]).splitlines()
    values = {}
    for line in output:
      m = re.match("([^=]+)=(\d+)", line)
      if m:
        values[m.group(1)] = int(m.group(2))

    for var in self.config["vars"]:
      var["command"] = self.config["command"]
      if var["name"] not in values:
        self.change_state(var, "command_e", [Monitor.EVENT_ERROR, var])
        continue
      value = values[var["name"]]
      var["__value__"] = value

      if "lt_e" in var and value < var["lt_e"]:
        self.change_state(var, "lt_e", [Monitor.EVENT_ERROR, var])
      elif "gt_e" in var and value > var["gt_e"]:
        self.change_state(var, "gt_e", [Monitor.EVENT_ERROR, var])
      elif "lt_w" in var and value < var["lt_w"]:
        self.change_state(var, "lt_w", [Monitor.EVENT_WARN, var])
      elif "gt_w" in var and value > var["gt_w"]:
        self.change_state(var, "gt_w", [Monitor.EVENT_WARN, var])
      elif "ne" in var and value != var["ne"]:
        self.change_state(var, "ne", [Monitor.EVENT_ERROR, var])
      else:
        self.change_state(var, "normal", [Monitor.EVENT_INFO, var])


# }}}

class Kernel(object): # {{{
  def __init__(self, config):
    self.config = config

  def signal_handler(self, sig, frame):
    LOGGER.info("==== Receive SIGINT signal......... ====")
    for monitor in self.config["monitors"]:
      monitor.stop()
    LOGGER.info("==== Shutting down thistle: success ====")
    sys.exit(0)

  def start(self):
    LOGGER.info("==== Starting up thistle......... ====")
    with open(self.config["pid_file"], "w") as io:
      io.write(u_(os.getpid()))
    signal.signal(signal.SIGINT, self.signal_handler)

    for monitor in self.config["monitors"]:
      LOGGER.info("Starting up monitor: {}".format(monitor.__class__.__name__))
      monitor.start()

    LOGGER.info("==== Starting up thistle: success ====")
    while True:
      time.sleep(60)

  def stop(self):
    with open(self.config["pid_file"]) as io:
      pid = int(io.read())
    os.kill(pid, signal.SIGINT)
    os.remove(self.config["pid_file"])
# }}}

if __name__ == "__main__": # {{{
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument('-c', dest="config",
                      help="configuration file path", required=True)
  parser.add_argument('command', choices=["start", "stop"])
  args = parser.parse_args()
  sys.path.insert(0, os.path.join(PATH, "user"))
  sys.modules["thistle"] = sys.modules["__main__"]
  import plugins
  sys.modules["thistle.plugins"] = plugins
  config = __import__(re.sub("\.py$", "", os.path.basename(args.config)))
  kernel = Kernel(config.config)
  getattr(kernel, args.command)()
#  }}}

