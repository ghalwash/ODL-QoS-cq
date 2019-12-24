import websocket
import xml.etree.ElementTree as ET
from threading import Thread
import threading
import httplib2
import json
import Queue
import config
import datetime

# websocketfile = open("/home/haitham/PycharmProjects/QoS/ODL-qos/websocket.txt", "w+")
# https://docs.python.org/2/library/xml.etree.elementtree.html
class WebSockettracker:
    port_count = 4
    controllerIP = config.controllerIP
    h = httplib2.Http(".cache")
    h.add_credentials('admin', 'admin')
    threads = []
    ws = []
    addresstracks = [7,8,11,12,15,16,19,20]
    stream = []
    message_info_status = {}
    average_byte_change = {}
    # lock = threading.Lock()
    # HistoryEvents = open("history.txt", "w+")
    # averageEvents = open("average.txt", "w+")
    events = Queue.Queue()
    node = 1
    port = 1


    def __init__(self):
        print ("print started")
        # get all listed nodes in the address tracker node inventory data base
        # self.get_address_tracker()
        # get stream URLs by invoking create-data-change-event-subscription
        self.get_stream_url()
        # create the list of web sockets that need to be listened to
        self.get_web_socket_url()
        self.start_listening()

    def get_web_socket_url(self):
        for s_item in self.stream:
            resp, content = self.h.request('http://' + self.controllerIP + '/restconf/streams/stream/'+s_item, "GET")
            content = str(content)
            start = content.find("location\":\"")
            end = content.find("\"}")
            path = content[start + 11:end]
            self.ws.append(path)
        # print (self.ws)

    def start_listening(self):
        websocket.enableTrace(True)
        for ws_url in self.ws:
            worker = Thread(target=self.listen, args=(ws_url,))
            self.threads.append(worker)
            worker.setDaemon(True)
            worker.start()
        for x in self.threads:
            x.join()

    def getIndex(self,sw):
        sw_id = int(sw.split(":")[1])
        try:
            port_ID = int(sw.split(":")[2])
        except:
            port_ID = -1
        return sw_id,port_ID

    def create_data_change_event_subscription(self,d):
        h = httplib2.Http(".cache")
        h.add_credentials('admin', 'admin')
        # print
        resp, content = self.h.request(
            uri='http://'+self.controllerIP+'/restconf/operations/sal-remote:create-data-change-event-subscription',
            method='post',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(d)
        )
        return resp, content

    def get_stream_url(self):
        # print self.addresstracks
        for node in self.addresstracks:
            resp, content = self.create_data_change_event_subscription(self.build_event_subscription_body(node))
            content = str(content)
            start = content.find("stream-name\":\"")
            end = content.find("\"}}")
            path = content[start + 14:end]
            self.stream.append(path)
        # print (self.stream)

    def build_event_subscription_body(self, node):
        # print node
        body = {
            "input": {
                "path": "/opendaylight-inventory:nodes/opendaylight-inventory:node[opendaylight-inventory:id='openflow:"+str(node)+"']/flow-node-inventory:table[flow-node-inventory:id='0']",
                "sal-remote-augment:datastore": "OPERATIONAL",
                "sal-remote-augment:scope": "SUBTREE"
            }
        }
        # body = { "input": {
        #     "path": "/opendaylight-inventory:nodes/opendaylight-inventory:node[opendaylight-inventory:id='openflow:"+node+"']/opendaylight-inventory:node-connector[opendaylight-inventory:id='openflow:"+node+":"+port+"']/address-tracker:addresses[address-tracker:id='"+address_id+"']/last-seen",
        #     "sal-remote-augment:datastore": "OPERATIONAL",
        #     "sal-remote-augment:scope": "SUBTREE"
        #     }
        # }
        return body

    # def get_address_tracker(self):
    #     # print config.odlNodes
    #     g = config.graph
    #
    #     for s in g.edges:
    #         if (str(s[0]).find("host") == 0) or (str(s[1]).find("host") == 0):
    #             x = g.get_edge_data(s[0], s[1])
    #             y = list(x.items())
    #             if (str(y[0][1]).find("host") == 0):
    #                 # print y[1][1]
    #                 index,port = self.getIndex(y[1][1])
    #             else:
    #                 # print y[0][1]
    #                 index,port = self.getIndex(y[0][1])
    #             # print (index , '-', port)
    #             self.addresstracks.append(index)
    #     print self.addresstracks

    def on_message(self, message):
        # print(message)
        time =''
        port_id = ''
        byte_tx = 0
        byte_rx = 0
        time_str=''
        mytime=0
        src_node=''
        dst_node=''
        node_id=''
        # print "*********************************************"
        # print message
        elem = ET.fromstring(message)
        # print elem
        # print message
        # print "********************"
        for e in elem.iter():
            # print e
            if e.tag == '{urn:opendaylight:params:xml:ns:yang:controller:md:sal:remote}path':
                txt = e.text
                if txt == '':
                    continue
                start = txt.find("tory:node[opendaylight-inventory:id='")
                end = txt.find("']/flow-node-inventory:table")
                mySubString = txt[start+37:end]
                node_id = mySubString
            elif e.tag == '{urn:ietf:params:xml:ns:netconf:notification:1.0}eventTime':
                time = e.text
                time_str = time[time.find("T")+1:len(time)-6]
                h, m, s = time_str.split(':')
                mytime = float(h) * 3600 + float(m) * 60 + float(s)
            elif e.tag == '{urn:opendaylight:flow:inventory}ethernet-match':
                child = e.getchildren()
                if child[0].tag == '{urn:opendaylight:flow:inventory}ethernet-source':
                    src_child = child[0].getchildren()
                    src_node = src_child[0].text
                    dst_child = child[1].getchildren()
                    dst_node = dst_child[0].text
                    # print src_node , "-", dst_node
                elif child[0].tag == '{urn:opendaylight:flow:inventory}ethernet-destination':
                    dst_child = child[0].getchildren()
                    dst_node = dst_child[0].text
                    src_child = child[1].getchildren()
                    src_node = src_child[0].text
                    # print src_node , "--", dst_node
            if src_node != '' and dst_node != '' and src_node != dst_node:
                #
                # print "$$$$$$$$$$$$$$$$$"
                path_key = dst_node + '-' + src_node
                # print self.message_info_status.keys()
                if path_key not in self.message_info_status.keys():
                    # print "yes"
                    self.events.put([dst_node,src_node, time_str])
                    self.message_info_status.update({path_key: [node_id,time_str]})
                    # self.lock.acquire()
                    # self.averageEvents.write("---------------------------------")
                    # self.averageEvents.write(str({path_key: [node_id,time_str]}))
                    # self.lock.release()
                    # print self.message_info_status
        # print self.message_info_status

        t= datetime.datetime.now()
        st = str(t)
        time_str = st[st.find(" ") + 1:len(st) - 3]
        h, m, s = time_str.split(':')
        mytime = float(h) * 3600 + float(m) * 60 + float(s)
        for keys in self.message_info_status.keys():
            # print keys
            time_odl_str = self.message_info_status[keys][1]
            # print time_odl_str
            oh, om, os = time_odl_str.split(':')
            time_odl_float = float(oh) * 3600 + float(om) * 60 + float(os)
            # print time_odl_float
            # print mytime
            node_age = mytime - time_odl_float
            # print node_age
            if node_age > 600:
                self.message_info_status.pop(keys)
            # print time_odl_float
        # print self.message_info_status
        # x= self.events.get()
        # print "x", x

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws):
        print("### closed ###")
    # def on_open(ws):
    #     def run(*args):
    #         for i in range(3):
    #             time.sleep(1)
    #             ws.send("Hello %d" % i)
    #         time.sleep(1)
    #         ws.close()
    #         print("thread terminating...")
    #     thread.start_new_thread(run, ())
    def listen(self,ws_url):
        ws = websocket.WebSocketApp(ws_url, on_message = self.on_message, on_error = self.on_error, on_close = self.on_close)
        wst = threading.Thread(target=ws.run_forever)
        wst.start()
#--------------------------------------------------------------------------
# main program
#--------------------------------------------------------------------------