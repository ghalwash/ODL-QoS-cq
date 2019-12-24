#!/usr/bin/python

import socket
import sys
import re
import datetime
from subprocess import Popen, PIPE
from threading import Thread
import queue
# from netcat import Netcat
# import commands
# import os
# import time
# import subprocess
# import threading
# import urlparse

def check_time(until_when):
    if until_when < datetime.datetime.now():
        input('Task has been finished.\nPress any key to quit\n')
        sys.exit()

def ping(port,ip):
    print ("thread is pinging", port, '-',ip)
    p = Popen(['paping', '-p', port, '-c', '4', '--nocolor', ip], stdout=PIPE)
    ping_out_1 = p.stdout.read()
    print ("this is ",ping_out_1)
    min_1 = re.search('Minimum = (.*)ms, Maximum',ping_out_1)
    max_1 = re.search('Maximum = (.*)ms, Average',ping_out_1)
    avg_1 = re.search('ms, Average = (.*)ms',ping_out_1)
    loss_1 = re.search('Failed = (.*)',ping_out_1)

    min_result = min_1.group(1)
    max_result = max_1.group(1)
    avg_result = avg_1.group(1)
    loss_result = loss_1.group(1)

    print ('Round Trip min Time: %s ms - ' % min_result, port)
    print ('Round Trip max Time: %s ms - ' % max_result,port)
    print ('Round Trip avg Time: %s ms - ' % avg_result,port)
    print ('Round Trip loss: %s  - ' % loss_result,port)

    avg.update({port:avg_result})
    min.update({port:min_result})
    max.update({port:max_result})
    loss_percent.update({port:loss_result})


#######################################################################################################
# main program
#######################################################################################################

num_threads = 15
ips_q = queue.Queue()
out_q = queue.Queue()
HOST = ''   # Symbolic name, meaning all available interfaces
ODL_ListenPort = 5000
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print ('Socket created')
#Bind socket to local host and port
print ("host",HOST)

try:
    s.bind((HOST, ODL_ListenPort))
except socket.error as msg:
    print ('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
    sys.exit()
print ('Socket bind complete')
#Start listening on socket
s.listen(5)
print ('Socket now listening')

while 1:
    conn, addr = s.accept()
    dstIP =conn.recv(2048).decode()

    Item_send = ''
    print ('Connected with ' + addr[0] + ':' + str(addr[1]))
    print ('Dst IP = ',dstIP)

    ports = ['5001','5002','5003','5004']
    # for i in range(0,len(ips),1):
    #     print ips[i]
    # # ips = ['10.0.0.101','10.0.0.102','10.0.0.103','10.0.0.104']
    avg = {}
    min = {}
    max = {}
    loss_percent = {}
    threads = []
    # start the thread pool
    for i in ports:
        # print i
        # print type(i)
        worker = Thread(target=ping, args=(i,dstIP,))
        threads.append(worker)
        worker.setDaemon(True)
        worker.start()
        # print "pinging ip =", i
    # wait until worker threads are done to exits
    for x in threads:
        x.join()
    # print "#######################################"
    # print "min", min
    # print "max", max
    # print "avg", avg
    # print "loss", loss_percent
    # print "#######################################"

    for i in range (0,len(ports),1):
        Item_send = Item_send+' ' + str(min[ports[i]]) + ' ' + str(max[ports[i]]) + ' ' + str(avg[ports[i]]) + ' ' + str(loss_percent[ports[i]])
        # print (Item_send)
    conn.send(Item_send)

    print (Item_send)

    conn.close()

# the ping process need to be threaded
# http://blog.boa.nu/2012/10/python-threading-example-creating-pingerpy.html
#https://stackoverflow.com/questions/12101239/multiple-ping-script-in-python