#!/usr/bin/env python
#vim: fileencoding=utf8
import sys
from thistlechart import *
import subprocess

if len(sys.argv) < 2:
  print("Usage: sysinfo_chart.py LOG_FILE OUTPUT_PATH")
  sys.exit(1)

chart = ThistleChart("sysinfo", sys.argv[1], sys.argv[2])

# CPU & Memory usage
chart.append_chart(["CPU_USAGE", "MEM_USAGE", "SWAP_USAGE"], 
  series=[{"label": "cpu"}, {"label": "memory"}, {"label": "swap"}],
  title="CPU & Memory usage",
  ylabel="Usage(%)", 
  ymin=0, 
  ymax=100)

# Load average
chart.append_chart(["LOAD_AVERAGE_1", "LOAD_AVERAGE_5", "LOAD_AVERAGE_15"],
  series=[{"label": "1min"}, {"label":"5min"}, {"label":"15min"}],
  title="Load average",
  ylabel="Load average", 
  ymin=0, 
  ymax=None)

# Devices
devices = subprocess.check_output("ls /dev/ | grep -E '^(hd|mmc|sd)'", shell=True).splitlines()
devices = [v for v in devices if "DEV_UTIL_{}".format(v) in chart.varnames]
chart.append_chart(
  ["DEV_RKBS_{}".format(v) for v in devices] + ["DEV_WKBS_{}".format(v) for v in devices],
  series=[{"label":"kbs read({})".format(v)} for v in devices] + [{"label":"kbs written({})".format(v)} for v in devices],
  title="Devices",
  ylabel="KB/S", 
  ymin=0, 
  ymax=None)
chart.append_chart(
  ["DEV_UTIL_{}".format(v) for v in devices],
  series=[{"label":"utilization({})".format(v)} for v in devices],
  title="Devices",
  ylabel="Utilization(%)", 
  ymin=0, 
  ymax=100)

chart.save()
