#!/usr/bin/env python
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
import subprocess
import threading
import signal
import time
import logging
import sqlite3
import codecs
from datetime import datetime

from compat import *

# module globals {{{
STOP_THREAD = "STOP_THREAD"
FILE_PATH = os.path.abspath(__file__)
if os.path.islink(FILE_PATH):
  FILE_PATH = os.readlink(FILE_PATH)
PATH = os.path.dirname(FILE_PATH)
LOGGER = logging.getLogger("thistle")
KERNEL = None
def with_defaults(default, values, copy=True):
  options = copy and default.copy() or default
  options.update(values)
  return options

def p_out(cmd):
  return subprocess.check_output(cmd, shell=(not isinstance(cmd, (list, tuple))))
# }}}

class Event(object): # {{{
  CRIT = logging.CRITICAL
  ERROR = logging.ERROR
  WARN  = logging.WARNING
  INFO  = logging.INFO
  logging.addLevelName(WARN, "WARN")
  logging.addLevelName(CRIT, "CRIT")

  @classmethod
  def as_string(cls, level):
    return logging.getLevelName(level)

  @classmethod
  def add_new_level(cls, name, value):
    setattr(cls, name, value)
    logging.addLevelName(value, name)

  @classmethod
  def define_levels(cls, levels):
    for key, value in iter_items(levels):
      cls.add_new_level(key, value)
# }}}

class BaseThread(threading.Thread): # {{{
  def __init__(self):
    threading.Thread.__init__(self)
    self.queue = queue.Queue()

  def stop(self):
    self.queue.put(STOP_THREAD)
    self.queue.join()
# }}}

class EventThread(BaseThread): # {{{
  def execute(self, obj, args):
    self.queue.put((obj, args))

  def run(self):
    while True:
      try:
        next_item = self.queue.get()
        if next_item is STOP_THREAD: 
          self.queue.task_done()
          break
        try:
          next_item[0]._callback(*next_item[1])
        except Exception as e:
          LOGGER.error("Failed to execute a callback: {}".format(u_(e)))

        self.queue.task_done()
      except queue.Empty:
        pass
# }}}

class DBThread(BaseThread): # {{{
  db_file = os.path.join(PATH, "dat", "thistle.db")

  def execute(self, f, sync=True):
    func = f
    if sync:
      q = queue.Queue()
      def func(conn):
        result = None
        try:
          result = f(conn)
        finally:
          q.put(result)
    self.queue.put(func)
    if sync:
      return q.get()
    
  def run(self):
    LOGGER.info("DB file: {}.".format(self.__class__.db_file))
    if not os.path.exists(self.__class__.db_file):
      LOGGER.info("Create new db: {}.".format(self.__class__.db_file))
      conn = sqlite3.connect(self.__class__.db_file)
      cur = conn.cursor()
      cur.execute('''create table file_stat (file text, seek int, header text)''')
      conn.commit()
      conn.close()
    self.conn = sqlite3.connect(self.__class__.db_file)

    while True:
      try:
        next_item = self.queue.get()
        if next_item is STOP_THREAD: 
          self.conn.close()
          self.queue.task_done()
          break
        next_item(self.conn)
        self.queue.task_done()
      except queue.Empty:
        pass
      except Exception as e:
        LOGGER.error("Error in DBThread: {}".format(u_(e)))
# }}}

class Target(object): # {{{
  __slots__ = ("monitor", "monitor_name", "attrs")

  DEFAULT_ATTRS = {
    "downtime": None,
    "level":    Event.ERROR
  }

  def __init__(self, monitor, attrs):
    self.monitor = monitor
    self.monitor_name = self.monitor.__class__.__name__
    self.attrs = with_defaults(Target.DEFAULT_ATTRS, attrs)
    self["__state__"] = "normal"

  def __getitem__(self, key): return self.attrs.get(key)
  def __setitem__(self, key, value): self.attrs[key] = value
  def __contains__(self, key): return key in self.attrs
  def get(self, key, default=None): return self.attrs.get(key, default)

  def downtime(self):
    downtime = self["downtime"]
    if downtime is None:
      return False
    if callable(downtime):
      return downtime()

  def change_state(self, state, level, check_state = True):
    if self.downtime():
      return

    pre_state = self["__state__"]
    if pre_state == state and check_state:
      return
    self["__state__"] = state
    message = "["+ self.monitor_name + "] " + self.monitor.attrs["messages"][state].format(**self.attrs)
    self.monitor.callback(level, message, self)
# }}}

class Monitor(BaseThread): # {{{
  DEFAULT_ATTRS = {
      "interval": 300,
      "messages": {},
      "callback": {
        Event.CRIT : [], Event.ERROR : [], Event.WARN  : [], Event.INFO  : []
      }
  }

  def __init__(self, attrs):
    BaseThread.__init__(self)
    self.attrs = with_defaults(self.default_attrs(), attrs, copy=False)
    self.init_attrs()

  def default_attrs(self):
    return Monitor.DEFAULT_ATTRS.copy()

  def init_attrs(self):
    self.attrs["targets"] = [Target(self, v) for v in self.attrs["targets"]]

  def _callback(self, *args):
    for callback in self.attrs["callback"][args[0]]:
      callback(*args)

  def callback(self, *args):
    KERNEL.event_thread.execute(self, args)

  def monitor(self): raise NotImplementedError()

  def run(self):
    time.sleep(KERNEL.attrs["waiting_time_on_boot"])
    while True:
      started_at = time.time()
      try:
        self.monitor()
        t = time.time() - started_at
        next_item = self.queue.get(timeout=self.attrs["interval"] - t)
        if next_item is STOP_THREAD: 
          self.queue.task_done()
          break
        self.queue.task_done()
      except queue.Empty:
        pass
      except Exception as e:
        LOGGER.error("Error in {}: {}".format(self.__class__.__name__, u_(e)))

# }}}

class ProcessMonitor(Monitor): # {{{
  def default_attrs(self):
    attrs = Monitor.default_attrs(self)
    attrs["messages"]["min"] = "{name}: {__count__:d} process(< {min:d})."
    attrs["messages"]["max"] = "{name}: {__count__:d} process(> {max:d})."
    attrs["messages"]["normal"] = "{name}: Resume normal operations."
    return attrs

  def init_attrs(self):
    Monitor.init_attrs(self)
    for target in self.attrs["targets"]:
      target["__pattern__"] = re.compile(target["pattern"])
      target["__count__"] = 0

  def get_process_list(self):
    return p_out(["ps", "-ef"]).splitlines()

  def monitor(self):
    processes = self.get_process_list()
    for target in self.attrs["targets"]:
      target["__count__"] = 0
      for process in processes:
        if target["__pattern__"].search(process):
          target["__count__"] += 1
      if target["__count__"] < target.get("min", -1):
        target.change_state("min", target["level"])
      elif target["__count__"] > target.get("max",99999):
        target.change_state("max", target["level"])
      else:
        target.change_state("normal", Event.INFO)
# }}}

class CommandOutputVarMonitor(Monitor): # {{{
  def default_attrs(self):
    attrs = Monitor.default_attrs(self)
    attrs["logger"] = None
    attrs["messages"]["gt"] = "{name}: {__value__} (> {gt})."
    attrs["messages"]["lt"] = "{name}: {__value__} (< {lt})."
    attrs["messages"]["ne"] = "{name}: {__value__} (!= {ne})"
    attrs["messages"]["command_e"] = "{__command__} : Invalid output. var {name} not found."
    attrs["messages"]["normal"] = "{name}: Resume normal operations."
    return attrs

  def init_attrs(self):
    Monitor.init_attrs(self)
    for target in self.attrs["targets"]:
      target["__value__"] = 0

  def log_values(self, values):
    buf = []
    for varname in sorted(iter_keys(values)):
      buf.append("{}:{}".format(varname, values[varname]))
    log = "{} {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), " ".join(buf))
    self.attrs["logger"](log)

  def get_values(self):
    output = p_out(self.attrs["command"]).splitlines()
    values = {}
    for line in output:
      m = re.match("([^=]+)=([\-\+]?\d+\.\d+)", line)
      if m:
        values[m.group(1)] = float(m.group(2))
      else:
        m = re.match("([^=]+)=([\-\+]?\d+)", line)
        if m:
          values[m.group(1)] = int(m.group(2))
    return values

  def monitor(self):
    values = self.get_values()
    if self.attrs["logger"]:
      self.log_values(values)
    for target in self.attrs["targets"]:
      target["__command__"] = self.attrs["command"]
      if target["name"] not in values:
        target.change_state("command_e", Event.ERROR)
        continue
      value = values[target["name"]]
      target["__value__"] = value

      if "lt" in target and value < target["lt"]:
        target.change_state("lt", target["level"])
      elif "gt" in target and value > target["gt"]:
        target.change_state("gt", target["level"])
      elif "ne" in target and value != target["ne"]:
        target.change_state("ne", target["level"])
      else:
        target.change_state("normal", Event.INFO)
# }}}

class LogMonitor(Monitor): # {{{
  def __init__(self, attrs):
    self.monitor_target = Target(self, attrs)
    Monitor.__init__(self, attrs)

  def default_attrs(self):
    attrs = Monitor.default_attrs(self)
    attrs["messages"]["not_readable_error"] = "File {file} is not readable or not exists."
    attrs["messages"]["truncated"] = "File {file} was truncated."
    attrs["messages"]["rewritten"] = "File {file} was rewritten."
    attrs["messages"]["opened"] = "Open the file {file}(position: {__seek__})."
    attrs["messages"]["error"] = "{__file__}: {message}({__line__})"
    attrs["messages"]["warn"] = "{__file__}: {message}({__line__})"
    attrs["messages"]["info"] = "{__file__}: {message}({__line__})"
    return attrs

  def update_seek(self, pos):
    def f(conn):
      cur = conn.cursor()
      cur.execute("BEGIN")
      cur.execute("update file_stat set seek = ?, header = ? where file=?", (pos, self.attrs["file"], self.monitor_target["__header__"]))
      conn.commit()
    KERNEL.db_thread.execute(f, sync=False)

  def close_file(self):
    if self.monitor_target["__io__"] is not None:
      self.monitor_target["__io__"].close()
      self.monitor_target["__io__"] = None

  def stop(self):
    Monitor.stop(self)
    self.close_file()

  def init_attrs(self):
    Monitor.init_attrs(self)
    for target in self.attrs["targets"]:
      target["__pattern__"] = re.compile(target["pattern"])
      target["__file__"] = self.attrs["file"]
    self.open_file()

  def open_file(self):
    self.close_file()
    try:
      self.monitor_target["__io__"] = codecs.open(self.attrs["file"], encoding=self.attrs.get("encoding", "utf8"))
      self.monitor_target["__size__"] = os.path.getsize(self.attrs["file"])
      self.monitor_target["__header__"] = self.monitor_target["__io__"].read(512)
      self.monitor_target["__io__"].seek(0)
    except:
      self.monitor_target.change_state("not_readable_error", Event.ERROR)
      return

    def f(conn):
      cur = conn.cursor()
      cur.execute("select * from file_stat where file=?", (self.attrs["file"],))
      row = list(cur.fetchone() or [])
      if not row:
        cur.execute("BEGIN")
        cur.execute("insert into file_stat values (?, ?, ?)", (self.attrs["file"], 0, u_("")))
        conn.commit()
        row = [self.attrs["file"], 0, u_("")]
      return row
    row = KERNEL.db_thread.execute(f)
    if self.monitor_target["__io__"]:
      if self.monitor_target["__size__"] < row[1]:
        self.monitor_target.change_state("truncated", Event.INFO)
        self.monitor_target["__io__"].seek(0)
        self.update_seek(0)
        row = [self.attrs["file"], 0]
      elif self.monitor_target["__header__"] != row[2]:
        self.monitor_target.change_state("rewritten", Event.INFO)
        self.monitor_target["__io__"].seek(0)
        self.update_seek(0)
        row = [self.attrs["file"], 0, self.monitor_target["__header__"]]
      else:
        self.monitor_target["__io__"].seek(row[1])
    self.monitor_target["__seek__"] = row[1]
    self.monitor_target.change_state("opened", Event.INFO)
    return self.monitor_target["__io__"]

  def monitor(self):
    io = self.monitor_target["__io__"]
    if io is None:
      io = self.open_file()
      if io is None:
        return
    else:
      try:
        new_size = os.path.getsize(self.attrs["file"])
      except:
        self.monitor_target.change_state("not_readable_error", Event.ERROR)
        self.monitor_target["__io__"] = None
        return
        
      if new_size < io.tell():
        self.monitor_target.change_state("truncated", Event.INFO)
        io = self.open_file()
        self.update_seek(0)
      else:
        where = io.tell()
        io.seek(0)
        if self.monitor_target["__header__"] != io.read(512):
          self.monitor_target.change_state("rewritten", Event.INFO)
          io = self.open_file()
          self.update_seek(0)
        else:
          io.seek(where)



    if io is None: return

    while True:
      where = io.tell()
      line = io.readline()

      if not line:
        io.seek(where)
        break

      for target in self.attrs["targets"]:
        if line:
          m = target["__pattern__"].match(line)
          if m:
            target["__line__"] = line.strip()
            target["__matchobj__"] = m
            level = target.get("level", Event.ERROR)
            target.change_state(Event.as_string(level).lower(), level, check_state=False)
      self.update_seek(io.tell())

# }}}

class Kernel(object): # {{{
  def __init__(self, attrs):
    self.attrs = attrs

  def signal_handler(self, sig, frame):
    self.shutdown()
    sys.exit(0)

  def shutdown(self):
    LOGGER.info("==== Receive SIGINT signal......... ====")
    for monitor in self.monitors:
      LOGGER.info("Stopping a monitor: {}".format(monitor.__class__.__name__))
      monitor.stop()
    LOGGER.info("Stopping an event thread.")
    self.event_thread.stop()
    LOGGER.info("Stopping a db thread.")
    self.db_thread.stop()
    LOGGER.info("==== Shutting down thistle: success ====")

  def start(self, loop=True):
    LOGGER.info("==== Starting up thistle......... ====")
    try:
      with open(self.attrs["pid_file"], "w") as io:
        io.write(u_(os.getpid()))
      signal.signal(signal.SIGINT, self.signal_handler)

      self.db_thread = DBThread()
      LOGGER.info("Starting up a db thread.")
      self.db_thread.start()
      self.event_thread = EventThread()
      LOGGER.info("Starting up an event thread.")
      self.event_thread.start()

      self.monitors = []
      for monitor_spec in self.attrs["monitors"]:
        monitor = monitor_spec[0](monitor_spec[1])
        self.monitors.append(monitor)
        LOGGER.info("Starting up monitor: {}".format(monitor.__class__.__name__))
        monitor.start()
    except Exception as e:
      LOGGER.info("==== Starting up thistle: failed ====")
      LOGGER.error(e)
      sys.exit(1)

    LOGGER.info("==== Starting up thistle: success ====")
    while loop:
      try:
        time.sleep(60)
      except KeyboardInterrupt:
        self.stop()

  def stop(self):
    with open(self.attrs["pid_file"]) as io:
      pid = int(io.read())
    os.kill(pid, signal.SIGINT)
    os.remove(self.attrs["pid_file"])
# }}}

if __name__ == "__main__": # {{{
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument('-c', dest="config",
                      help="configuration file path", required=True)
  parser.add_argument('command', choices=["start", "stop", "test"])
  args = parser.parse_args()
  sys.path.insert(0, os.path.join(os.path.dirname(args.config)))
  sys.modules["thistle"] = sys.modules["__main__"]
  import plugins
  sys.modules["thistle.plugins"] = plugins
  try:
    config = __import__(re.sub("\.py$", "", os.path.basename(args.config)))
    if args.command == "test":
      print("OK")
  except:
    if args.command == "test":
      import traceback
      print("NG:")
      traceback.print_exc()
      sys.exit(1)
    else:
      raise
  if args.command != "test":
    KERNEL = Kernel(config.config)
    getattr(KERNEL, args.command)()
#  }}}

