#!/usr/bin/python
import glob
import os
import time
import argparse
import humanize
import datetime
import jinja2
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


SEC_IN_MIN = 60
MIN_IN_HOUR = 60
HOURS_IN_DAY = 24

TEMPLATES = {'htmlemail': """
<p><h3>Outdated backups</h3></p> 
{% for age in age_list -%}
{%- set comma = joiner(", ") -%}
  Last updated {{age[0]}}:{{" "}}
  {%- for dirname in age[1] -%}
    {{comma()}}{{dirname|basename}}
  {%- endfor -%}
  <br />
{% endfor -%}

{% for dirname in data.keys() %}
  <p><h3>{{dirname|basename}}</h3></p>
  <table>
  {%- if data[dirname]|length > 0 -%}
    {%- for fileinfo in data[dirname] %}
    <tr><td>{{fileinfo['name']}}</td><td>{{fileinfo['size']|humansize}}</td><td>{{fileinfo['date']|timeago}}</td></tr>
    {%- endfor %}
  {%- else %}
    &lt;empty directory&gt;<br />
  {%- endif -%}
  </table>
{%- endfor -%}
""",
'textemail': """
---Outdated backups--- 
{% for age in age_list -%}
{%- set comma = joiner(", ") -%}
  Last updated {{age[0]}}:{{" "}}
  {%- for dirname in age[1] -%}
    {{comma()}}{{dirname|basename}}
  {%- endfor %}
{% endfor -%}

{% for dirname in data.keys() %}
  ---{{dirname|basename}}---
  {%- if data[dirname]|length > 0 -%}
    {%- for fileinfo in data[dirname] %}
    {{fileinfo['name']}}, {{fileinfo['size']|humansize}}, {{fileinfo['date']|timeago}}
    {%- endfor %}
  {%- else %}
    <empty directory>
  {% endif -%}
{%- endfor -%}"""}


def is_outdated(dir, days):
    if not os.path.isdir(dir):
        return False
    if len(os.listdir(dir)) < 1:
        return True
    files = glob.glob(os.path.join(dir, '*'))
    latest_file = max(files, key=os.path.getmtime)
    return time.time() - os.path.getmtime(latest_file) > (days * HOURS_IN_DAY * MIN_IN_HOUR * SEC_IN_MIN)


def fmt_timeago(timestamp):
    return humanize.naturaltime(datetime.timedelta(seconds=time.time()-timestamp))


def fmt_humansize(size_in_bytes):
    return humanize.naturalsize(size_in_bytes)


def basename(fullpath):
    return os.path.basename(fullpath)


def gather_data(dir_to_scan, days):
    data = {}
    if not os.path.isdir(dir_to_scan):
        raise Exception("Invalid directory to scan: %s" % dir_to_scan)
    outdated_dirs = [x for x in glob.glob(os.path.join(dir_to_scan, '*')) if is_outdated(x, days)]
    for dir in outdated_dirs:
        if len(os.listdir(dir)) < 1:
            data[dir] = []
        data[dir] = sorted([{'name': x, 'date': os.path.getmtime(x), 'humandate': fmt_timeago(os.path.getmtime(x)),
                             'size': os.path.getsize(x), 'humansize': fmt_humansize(os.path.getsize(x))}
                            for x in glob.glob(os.path.join(dir, '*'))], key=lambda k: k['date'], reverse=True)[:5]
    return data


def render(data, age_list):
    loader = jinja2.DictLoader(mapping=TEMPLATES)
    jenv = jinja2.Environment(loader=loader)
    jenv.filters['timeago'] = fmt_timeago
    jenv.filters['humansize'] = fmt_humansize
    jenv.filters['basename'] = basename
    template = jenv.get_template("htmlemail")
    html = template.render({"data": data, "age_list": age_list})
    template = jenv.get_template("textemail")
    text = template.render({"data": data, "age_list": age_list})
    return html, text


def main(args):
    data = gather_data(args["dir"], args["age"])
    sorted_dirs = sorted([(x, data[x][0]['date'], data[x][0]['humandate']) if len(data[x]) > 0 else (x, 0, 'never')
                          for x in data.keys()], key=lambda k: k[1])
    age_list = []
    for item in sorted_dirs:
        if len(age_list) == 0 or age_list[-1][0] != item[2]:
            age_list.append((item[2], []))
        age_list[-1][1].append(item[0])
    html, text = render(data, age_list)
    #print("html: %s" % html)
    #print("text: %s" % text)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Backups out of date"
    msg['From'] = args["from"]
    msg['To'] = args["to"]
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    srv = smtplib.SMTP('localhost')
    srv.sendmail(msg['From'], msg['To'], msg.as_string())
    srv.quit()


if __name__ == "__main__":
    cmdParser = argparse.ArgumentParser(prog="backupnotify.py")
    cmdParser.add_argument("-d", "--dir", required=True,
                           help="The directory to scan for backups")
    cmdParser.add_argument("-a", "--age", default=1,
                           help="Alert when no backups newer than X days are present")
    cmdParser.add_argument('-t', '--to', required=True,
                           help="The email address to send reports to")
    cmdParser.add_argument('-f', '--from', default="test@example.com",
                           help="The email address to send reports from")
    parsed_args = vars(cmdParser.parse_args())
    main(parsed_args)
