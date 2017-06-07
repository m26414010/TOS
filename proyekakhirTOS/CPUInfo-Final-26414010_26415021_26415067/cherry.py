
import os, os.path
import cherrypy
from cherrypy.lib.static import serve_file

import pymysql
import pymysql.cursors as cur
import json

import psutil
import _thread
import platform

import schedule
import time
import datetime

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


curdir = os.getcwd()
config = {
  'global': {
    'server.socket_host': '127.0.0.1',
    'server.socket_port': 12345,
    'server.thread_pool': 8
  },
  '/': {
    'tools.staticdir.root': curdir,
  },
  '/static': {
    'tools.staticdir.on': True,
    'tools.staticdir.dir': "static"
  }
}

memLimit = 40
cpuLimit = 50
mem_over = False
cpu_over = False
receiver = 'm26414035@john.petra.ac.id'
counter = -1
mem = 0
cpu = 0
mpercent = 0

def CheckWarning(meml, cpul):
    global counter
    global mem_over
    global cpu_over

    if(meml > memLimit):
        mem_over = True
    else:
        mem_over = False

    if(cpul > cpuLimit):
        cpu_over = True
    else:
        cpu_over = False

    if mem_over or cpu_over:
        counter += 1

    if mem_over and cpu_over:
        counter = -1

    if counter % 5 == 0:
        SendMailWarning(mem_over, cpu_over)


def SendMailWarning(memover, cpuover):
    global cpu, mpercent, memLimit, cpuLimit

    sender = 'm26414035@john.petra.ac.id'
    receivers = receiver

    msg = MIMEMultipart('alternative')
    text2 = ""
    if memover and cpuover:
        msg['Subject'] = "Server Memory and CPU Usage Overlimit"
        text = "Memory Usage: " + str(mpercent) + "%,  with a limit of " + str(memLimit) + "% || " + "CPU Usage: " + str(cpu) + "% with a limit of " + str(cpuLimit) + "%"
    elif memover:
        print("memory")
        msg['Subject'] = "Server Memory Usage Overlimit"
        text = "Memory Usage: " + str(mpercent) + " with a limit of " + str(memLimit)

    elif cpuover:
        msg['Subject'] = "Server CPU Usage Overlimit"
        text = "CPU Usage: " + str(cpu) + " with a limit of " + str(cpuLimit)

    msg['From'] = sender
    msg['To'] = receivers

    part1 = MIMEText(text, 'plain')

    msg.attach(part1)

    s = smtplib.SMTP('smtp.gmail.com:587')
    s.ehlo()
    s.starttls()
    s.login('warningbot123', 'warningbot123WOWDude123')
    s.sendmail(sender, receivers, msg.as_string())
    s.quit()


def GetCPUInfo():
    global cpu, mem, mpercent

    cpu = psutil.cpu_percent(1)
    mem = psutil.virtual_memory().used / 1024 ** 3
    mpercent = int(psutil.virtual_memory().used * 100 / psutil.virtual_memory().total)

    CheckWarning(mpercent, cpu)

    ts = time.time()
    timeres = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    connection = pymysql.connect(host='127.0.0.1', user='root', passwd='', db='test', charset='utf8mb4',
                                 cursorclass=cur.DictCursor)

    with connection.cursor() as cursor:
        sql = "INSERT INTO dummy VALUES(null, %s, %s, %s, %s)"
        cursor.execute(sql, (str(mem), str(mpercent), str(cpu), str(timeres)))
        connection.commit()

        sql = "SELECT COUNT(*) FROM dummy"
        cursor.execute(sql)
        rowcount = json.loads(json.dumps(cursor.fetchall()))
        if rowcount[0]["COUNT(*)"] > 10:
            sql = "DELETE FROM dummy LIMIT 1"
            cursor.execute(sql)
            connection.commit()
        connection.close()

schedule.every(5).seconds.do(GetCPUInfo)


def RefreshInfo():
    while 1:
        schedule.run_pending()

_thread.start_new_thread(RefreshInfo, ())


def GetData():
    connection = pymysql.connect(host='127.0.0.1', user='root', passwd='', db='test', charset='utf8mb4', cursorclass=cur.DictCursor)
    with connection.cursor() as cursor:

        sql = "SELECT COUNT(*) FROM dummy"
        cursor.execute(sql)
        rowcount = json.loads(json.dumps(cursor.fetchall()))

        if rowcount[0]["COUNT(*)"] > 10:
            sql = "DELETE FROM dummy LIMIT 1"
            cursor.execute(sql)
            connection.commit()

        sql = "SELECT * FROM dummy"
        cursor.execute(sql)
        result = json.dumps(cursor.fetchall())
        connection.close()

    return result


def GetSystemInfo():
    cpuInfo = platform.processor()
    memInfo = round(psutil.virtual_memory().total / 1024 ** 3)
    osInfo = platform.system()

    result = {}
    result['cpu'] = cpuInfo
    result['memory'] = memInfo
    result['os'] = osInfo
    return json.dumps(result)


class View(object):
    @cherrypy.expose
    def index(self):
        return serve_file(os.path.join(curdir, "index.html"))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def PassData(self):
        return GetData()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def PassSystemInfo(self):
        return GetSystemInfo()

    @cherrypy.expose
    def SetCPULimit(self, limit):
        global cpuLimit
        cpuLimit = int(limit)
        result = {}
        result['limit'] = cpuLimit
        return json.dumps(result)

    @cherrypy.expose
    def SetMemLimit(self, limit):
        global memLimit
        memLimit = int(limit)
        result = {}
        result['limit'] = memLimit
        return json.dumps(result)

    @cherrypy.expose
    def SetReceiver(self, addr):
        global receiver
        receiver = str(addr)
        print(receiver)
        result = {}
        result['addr'] = receiver
        return json.dumps(result)


#cherrypy.engine.stop()
cherrypy.quickstart(View(), '/', config)