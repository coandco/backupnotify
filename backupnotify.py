import glob
import os
import time
import humanize
import datetime
import jinja2


SEC_IN_MIN = 60
MIN_IN_HOUR = 60
HOUR_IN_DAY = 24

TEMPLATES = {'email': """
{%- set comma = joiner(", ") -%}
<p><h3>Outdated backups: 
{%- for dirname in data.keys() -%}
  {{comma()}}{{dirname|basename}}
{%- endfor -%}
</h3></p>
{% for dirname in data.keys() %}
  <p><h3>{{dirname}}</h3></p>
  <table>
  {%- for fileinfo in data[dirname] %}
    <tr><td>{{fileinfo['name']}}</td><td>{{fileinfo['size']|humansize}}</td><td>{{fileinfo['date']|timeago}}</td></tr>
  {%- endfor %}
  </table>
{%- endfor -%}
"""}


def is_outdated(dir, days):
    if not os.path.isdir(dir):
        return False
    files = glob.glob(os.path.join(dir, '*'))
    latest_file = max(files, key=os.path.getmtime)
    return time.time() - os.path.getmtime(latest_file) > (days * SEC_IN_MIN * MIN_IN_HOUR * HOUR_IN_DAY)


def fmt_timeago(timestamp):
    return humanize.naturaltime(datetime.timedelta(seconds=time.time()-timestamp))


def fmt_humansize(size_in_bytes):
    return humanize.naturalsize(size_in_bytes)


def basename(fullpath):
    return os.path.basename(fullpath)


def gather_data(dir_to_scan, days):
    data = {}
    outdated_dirs = [x for x in glob.glob(os.path.join(dir_to_scan, '*')) if is_outdated(x, days)]
    for dir in outdated_dirs:
        data[dir] = sorted([{'name': x, 'date': os.path.getmtime(x), 'size': os.path.getsize(x)}
                            for x in glob.glob(os.path.join(dir, '*'))], key=lambda k: k['date'], reverse=True)[:5]
    return data


dir_to_test = r'C:\temp\git\bn_test'
data = gather_data(dir_to_test, 1)

print("data: %r" % data)

loader = jinja2.DictLoader(mapping=TEMPLATES)
jenv = jinja2.Environment(loader=loader)
jenv.filters['timeago'] = fmt_timeago
jenv.filters['humansize'] = fmt_humansize
jenv.filters['basename'] = basename
template = jenv.get_template("email")
html = template.render({"data": data})

print("html: %s" % html)