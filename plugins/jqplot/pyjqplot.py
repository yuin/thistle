#vim: fileencoding=utf8
import sys
import os
import codecs
import json
import os.path
import re
from string import Template

# compatibility stuff {{{
if sys.version_info >= (3,0,0):
  unicode = str
  string_types = (unicode, bytes)
  def n_(s):
    if isinstance(s, unicode): return s
    elif isinstance(s, bytes): return s.decode("latin1")
    return unicode(s)
else:
  bytes = str
  string_types = basestring
  def n_(s):
    if isinstance(s, bytes): return s
    elif isinstance(s, unicode): return s.encode("latin1")
    return bytes(s)

def b_(s, encoding='utf8'):
  if isinstance(s, unicode): return s.encode(encoding)
  elif isinstance(s, (integer_types + (float,))): return b_(repr(s))
  return bytes(s)
def u_(s, encoding='utf8', errors='strict'):
  return s.decode(encoding, errors) if isinstance(s, bytes) else unicode(s)
# }}}

PATH = os.path.dirname(os.path.abspath(__file__))
ASSETS_PATH = os.path.join(PATH, "jqplot_assets")

# HTML_TEMPLATE {{{
HTML_TEMPLATE=u_("""<!DOCTYPE html>
<html lang="ja-JP">
  <head>
    <meta charset="utf-8">
    <title>${page_title}</title>
    ${scripts}
    <link rel="stylesheet" type="text/css" href="./jqplot_assets/jquery.jqplot.min.css" />
  </head>
  <body>
    ${chart}
  </body>
</html>
""")
# }}}

class Page(object): # {{{
  def __init__(self, title = ""):
    self.charts = []
    self.title = title or "Chart"

  def render(self, output_path):
    chart_html = u_("\n").join(c.render() for c in self.charts)
    scripts = u_("\n").join("<script src=\"./jqplot_assets/{}\"></script>".format(file) for file in sorted(os.listdir(ASSETS_PATH)) if file.endswith(".js"))
    with codecs.open(output_path, "w", encoding="utf8") as io:
      io.write(Template(HTML_TEMPLATE).substitute(page_title = self.title, scripts = scripts, chart = chart_html))
# }}}

class Chart(object): # {{{
  def __init__(self, width, height, data, options = None):
    self.width =width
    self.height = height
    self.data = data
    self.options = options or {}

  def dump_json_with_object_support(self, obj):
    return re.sub('"OBJECT:([^"]+)"', "\\1", json.dumps(obj))

  def render(self):
    chart_id = "chart_"+u_(id(self))
    buf = ['<div id="', chart_id , '" style="height:', u_(self.height), ';width:', u_(self.width), 'px; "></div><script>']
    buf.extend(['$.jqplot("', chart_id, '", ', json.dumps(self.data), ', ', self.dump_json_with_object_support(self.options) ,');</script>'])
    #buf.extend(['<img id="image_', chart_id, '" />'])
    #buf.extend(["""<input type="button" value="convert to png image" onclick="$('#image_""", chart_id, "').attr('src', $('#", chart_id, "').jqplotToImage(50, 0).toDataURL('image/png'));\" />"])
    return u_("").join(buf)
# }}}

