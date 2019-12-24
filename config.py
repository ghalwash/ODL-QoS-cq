import httplib2
import json
import networkx as nx
import numpy as np

port_count = 4
Count_switches = 20
hosts = []
switches = []
routes_short_path =[]
route_ports_db = []
natHost = "host:0e:9f:64:5e:83:97"
maplist = {}
maplist1 = {}
MACtoIP_maplist1={}
IPtoMAC_maplist1={}
controllerIP='127.0.0.1:8181'

# controllerIP='192.168.1.128:8181'
port_connecting = -1 * np.ones([Count_switches + 1, port_count+ 1])

h = httplib2.Http(".cache")
h.add_credentials('admin', 'admin')


def getIndex(sw):
    sw_id = int(sw.split(":")[1])
    try:
        port_ID = int(sw.split(":")[2])
    except:
        port_ID = -1
    return sw_id, port_ID

resp, content = h.request('http://' + controllerIP + '/restconf/operational/opendaylight-inventory:nodes',"GET")
allFlowStats = json.loads(content)
flowStats = allFlowStats['nodes']['node']

resp, content = h.request('http://'+controllerIP+'/restconf/operational/network-topology:network-topology/',"GET")
alltopology = json.loads(content)
odlNodes = alltopology['network-topology']['topology'][0]['node']
odlEdges = alltopology['network-topology']['topology'][0]['link']
graph = nx.Graph()
for node in odlNodes:
    # print node
    if (node['node-id']== natHost):
        # print node['node-id']
        continue
    graph.add_node(node['node-id'])
    if node['node-id'].find("openflow") == 0:
        switches.append(node['node-id'])
    else:
        maplist[node['host-tracker-service:addresses'][0]['mac']] =node['host-tracker-service:addresses'][0]['ip']


for node in odlNodes:
    if node['node-id'].find("openflow") != 0:
        maplist1[node['host-tracker-service:addresses'][0]['mac']]= node['host-tracker-service:addresses'][0]['ip']

for node in odlNodes:
    if node['node-id'].find("openflow") != 0:
        MACtoIP_maplist1[node['host-tracker-service:addresses'][0]['mac']]= node['host-tracker-service:addresses'][0]['ip']
        IPtoMAC_maplist1[node['host-tracker-service:addresses'][0]['ip']]=node['host-tracker-service:addresses'][0]['mac']

# print maplist
for edge in odlEdges:                                 #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$change here
    # print edge
    src_edge = edge['source']['source-node']
    dst_edge = edge['destination']['dest-node']
    if (src_edge == natHost or dst_edge == natHost):
        continue
    e = (src_edge, dst_edge)
    if str(src_edge).find("openflow") == 0 and str(dst_edge).find("openflow") == 0 :
        # print src_edge
        sw_src_id = int(str(src_edge).split(":")[1])
        # print sw_src_id
        # print '---'
        # print dst_edge
        sw_dst_id = int(str(dst_edge).split(":")[1])
        # print sw_dst_id
        src_port = edge['source']['source-tp']
        # print src_port
        sw_src_port = int(str(src_port).split(":")[2])
        port_connecting[sw_src_id][sw_src_port] = sw_dst_id
    graph.add_edge(*e,Src=edge['source']['source-tp'],Dst=edge['destination']['dest-tp'])
    if edge['source']['source-node'].find("host") == 0 :
        hosts.append(edge['source']['source-node'])

# print port_connecting

Count_switches = len(switches)


Connection_array = -1 * np.ones([Count_switches + 1, port_count + 1])
for s in graph.edges:
    if (str(s[0]).find("host") != 0) and (str(s[1]).find("host") != 0):
        x = graph.get_edge_data(s[0], s[1])
        y = list(x.items())
        sw_1, port_1 = getIndex(y[0][1])
        sw_2, port_2 = getIndex(y[1][1])
        Connection_array[sw_1][port_1] = sw_2
        Connection_array[sw_2][port_2] = sw_1

Core_switch_list = [1,2,3,4]
edge_Switch_list = [7,8,11,12,15,16,19,20]
agregation_switch_list = [5,6,9,10,13,14,17,18]

# comon_byte_port_utilization = -1 * np.ones([Count_switches + 1,port_count + 1])