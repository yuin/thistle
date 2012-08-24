#vim: fileencoding=utf8
import sys, os
import socket
import subprocess
import math

from pyjqplot import *


class ThistleChart(object):
  def __init__(self, title, log_file, output_path):
    self.log_file = log_file
    self.output_path = output_path
    self.lines = open(self.log_file).read().splitlines()
    first_time  = " ".join(self.lines[0].split(" ")[0:2])
    last_time  = " ".join(self.lines[-1].split(" ")[0:2])
    self.page = Page(title="Thistle {}({}: {} to {})".format(title, socket.gethostname(), first_time, last_time))
    self.varnames = [v.split(":")[0] for v in self.lines[0].split(" ")[2:]]
    
  def append_chart(self, names, title, ylabel, ymin, ymax, series):
    data = self.grep_field_with_time(names)
    if ymax is None:
      tmp_data = []
      for ss in data:
        tmp_data.extend(v[1] for v in ss)
      ymax = sorted(tmp_data)[-1]
      if ymax == 0:
        ymax = 10
      else:
        l = int(math.log(ymax, 10))
        ymax = (int(ymax/(10**l))+1) * 10**l
  
    self.page.charts.append(Chart(900, 400, data,
    {
      "title": title,
      "axes": {
        "yaxis": {
          "labelRenderer":"OBJECT:$.jqplot.CanvasAxisLabelRenderer",
          "min": ymin, 
          "max": ymax,
          "label": ylabel,
          "labelOptions":{"angle":90}
        },
        "xaxis": {
          "renderer": "OBJECT:$.jqplot.DateAxisRenderer",
          "tickRenderer": "OBJECT:$.jqplot.CanvasAxisTickRenderer",
          "min": data[0][0][0],
          "max": data[0][-1][0],
          "tickInterval": "30 minute",
          "tickOptions": {
            "formatString": "%H:%M",
            "angle": 60
          }
        }
      },
      "seriesDefaults": {
        "lineWidth": 1,
        "markerOptions": {
          "style": "diamond",
          "lineWidth": 1,
          "size": 3
        }
      },
      "series": series,
      "legend": {
        "show": True, 
        "location": 'ne',
        "placement": "outsideGrid",
        "renderer": "OBJECT:$.jqplot.EnhancedLegendRenderer"
      }
    }
    ))
  
  def grep_field_with_time(self, fields_to_select):
    result = []
    for line in self.lines:
      time = " ".join(line.split(" ")[0:2])
      for i, field_to_select in enumerate(fields_to_select):
        m = re.search("\s{}:(\w+)".format(field_to_select), line)
        if not m: continue
        if len(result) == i: result.append([])
        result[i].append([time, eval(m.group(1))])
    return result

  def save(self):
    self.page.render(self.output_path)
