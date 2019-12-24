import httplib2

import CollectData
from threading import Thread
import threading
import json
import networkx as nx
import datetime
import numpy as np
import difflib
import socket
import time
import sys
import WebSocketclient
import config
from multiprocessing import Process
from collections import OrderedDict
import graphRoute

data_collected = CollectData.DataCollector()
g = graphRoute.GraphRoute()
# track_flow = {}
lock = threading.Lock()
thread_list = []

# Print the solution src & dst
class calculateRoute:
    def __init__(self, d):
        self.paping_path_list = {}
        self.port_count = 4
        self.hosts = []
        self.switches = []
        self.routes_dij = []
        self.routes_short_path = []
        self.route_ports_db = []
        self.controllerIP = config.controllerIP
        self.graph = nx.Graph()
        self.source_agent_HOST_listenPort = 5000

    #######################################################################################################
    # get Switch Index flow statistics- for each node query all port statistics
    def getIndex(self, sw):
        sw_id = int(sw.split(":")[1])
        try:
            port_ID = int(sw.split(":")[2])
        except:
            port_ID = -1
        return sw_id, port_ID

    #######################################################################################################
    # helper function get-packets for two edge nodes
    def get_packet_count(self, route_ports, port_matching):
        list = []
        for r in route_ports:
            if (r[0] == port_matching):
                list.append(r)
        return list

    #######################################################################################################
    # all diskstra rout between two hosts
    def getDijkRoute(self, Src, Dst):
        route = nx.dijkstra_path(config.graph, Src, Dst)
        return route

    #######################################################################################################
    # shorted path for all
    def getShortestPath(self, g, Src, Dst):
        routes = []
        for m in (nx.all_shortest_paths(g, source=Src, target=Dst)):
            routes.append(m)
        return routes

    def getCaditatePaths(self, srcHost, dstHost):
        # print "****************starting getCaditatePaths Function******************"
        # hx1 = self.gethostID_from_IP(srcIP)
        # hx2 = self.gethostID_from_IP(dstIP)
        path = self.getShortestPath(config.graph, srcHost, dstHost)
        return path

    def set_congested_path(self, SrcMAC, DstMAC, path):
        # print "****************starting set_Shortest_path Function******************"
        # SrcIP = self.getIP_from_Mac(SrcMAC)
        # DstIP = self.getIP_from_Mac(DstMAC)
        SrcIP = config.MACtoIP_maplist1[SrcMAC]
        DstIP = config.MACtoIP_maplist1[DstMAC]
        if (SrcIP != None and DstIP != None):
            x = str(SrcIP).split(".")
            y = str(DstIP).split(".")
            flowID = str(x[3]) + str(y[3])
        # print flowID
        # print path
        self.push_path(path, SrcMAC, DstMAC, flowID, 70)

    #######################################################################################################
    # set shortest path rules
    # ------------------------------------------------------------------------------------------------------
    def set_Shortest_path(self, SrcMAC, DstMAC):
        # print "****************starting set_Shortest_path Function******************"
        SrcHost = self.gethostID_from_Mac(SrcMAC)
        DstHost = self.gethostID_from_Mac(DstMAC)
        SrcIP = self.getIP_from_Mac(SrcMAC)
        DstIP = self.getIP_from_Mac(DstMAC)
        path = self.getDijkRoute(SrcHost, DstHost)
        x = str(SrcIP).split(".")
        y = str(DstIP).split(".")
        flowID = str(x[3]) + str(y[3])
        # print flowID
        self.push_path(path, SrcMAC, DstMAC, flowID, 20)
        # self.push_path(reversed(path), DstMAC,SrcMAC, flowID, 20)

    #######################################################################################################
    # set shortest path rules
    # ------------------------------------------------------------------------------------------------------
    def set_Shortest_path_FlowID(self, SrcMAC, DstMAC,flowID):
        print "****************starting set_Shortest_path ID******************"
        SrcHost = "host:"+SrcMAC
        DstHost = "host:"+DstMAC
        path = self.getDijkRoute(SrcHost, DstHost)
        print type(path)
        print SrcHost, "-", DstHost, "---", path
        self.push_path(path, SrcMAC, DstMAC, flowID, 20)
        # print path.reverse()
        path.reverse()
        self.push_path(path, DstMAC,SrcMAC, "".join(reversed(flowID)), 20)

    #######################################################################################################
    # get candidate shortest path QoS paper 3
    # ------------------------------------------------------------------------------------------------------
    def get_dissimilar_paths(self, path):
        similarity = 1
        if type(path[0]) != list:
            return None, None
        for i in range(len(path)):
            for j in range(i + 1, len(path)):
                sm = difflib.SequenceMatcher(None, path[i], path[j])
                if sm.ratio() < similarity:
                    similarity = sm.ratio()
                    canditate1 = path[i]
                    canditate2 = path[j]
        return canditate1, canditate2

    def load_balance(self, vip_ip, dstPort, srcIP, dstIP, flowID, rvflowID):
        i = 0
        single_path = 1
        tableID = '0'
        ethTypeIp = 0x800
        ipTypeTcp = 0x6
        ipTypeUdp = 0x11
        path = self.getCaditatePaths(srcIP, dstIP)
        path_file = open("path.txt", "a+")
        if type(path[0]) != list or (dstPort == 0):
            path_file.write('Src-IP =' + srcIP + 'to dst-IP = ' + dstIP)
            # print path[0]
            path_file.write(str(path[0]))
            self.push_path_port(path[0], 0, srcIP, dstIP, str(flowID), str(rvflowID), 10)
        else:
            # get the cadidate paths
            path1, path2 = self.get_dissimilar_paths(path)
            path_file.write('Src-IP =' + srcIP + 'to dst-IP = ' + dstIP)
            path_file.write(str(path1))
            path_file.write(str(path2))
            # if dst port is -1 distinguish based n the IP addtess, VIP goes to one path and there on the other
            # if dst port is specified push the specified dstination to a path and all other to diffrent path
            if dstPort == -1:
                if vip_ip == 1:
                    # print 'vip = 1'
                    # print srcIP
                    # print path1
                    self.push_path_port(path1, 0, srcIP, dstIP, str(flowID), str(rvflowID), 10)
                else:
                    # print 'vip = 0'
                    # print srcIP
                    # print path2
                    self.push_path_port(path2, 0, srcIP, dstIP, str(flowID), str(rvflowID), 20)
            # if dst port is specified push the specified dstination to a path and all other to diffrent path

            else:
                self.push_path_port(path1, 0, srcIP, dstIP, str(flowID), str(rvflowID), 10)
                x = flowID + 1000
                y = rvflowID + 1000
                self.push_path_port(path2, dstPort, srcIP, dstIP, str(x), str(y), 20)

    #######################################################################################################
    # set shortest path QoS paper 4
    # ------------------------------------------------------------------------------------------------------
    def set_Shortest_path_QoS_proactive_active(self, SrcMAC, DstMAC):
        port_path_list = []
        port_list = []
        path_list = []
        Src_IP = self.getIP_from_Mac(SrcMAC)
        SrcIP = str(Src_IP)
        Dst_IP = self.getIP_from_Mac(DstMAC)
        DstIP = str(Dst_IP)
        # print ('paping', self.paping_path_list)
        # print paping_path_list.get(SrcIP,None)
        temp_key_1 = SrcIP + '-' + DstIP
        temp_key_2 = DstIP + '-' + SrcIP
        # print temp_key_1
        # print 'path-list before if', paping_path_list
        # print 'paping before if', paping_path_list.get(temp_key_1,None)
        if (self.paping_path_list.get(temp_key_1, None) == None):
            # print "papingpatj-----------"
            port_list, path_list = self.set_paping_path(SrcMAC, DstMAC, str(SrcIP), str(DstIP))
            # print "papingpatj"
            port_path_list.append(port_list)
            port_path_list.append(path_list)
            self.paping_path_list.update({temp_key_1: port_path_list})
            self.paping_path_list.update({temp_key_2: port_path_list})
        else:
            port_path_list = self.paping_path_list.get(temp_key_1, None)
            # print 'else statmement', self.paping_path_list
        string_ports = str(port_list[0]) + ' ' + str(port_list[1]) + ' ' + str(port_list[2]) + ' ' + str(port_list[3])
        # print 'string of ports to be sent', string_ports
        paping_values = str(self.get_delay_loss_paping(SrcIP, DstIP))
        paping = paping_values.split(' ')
        avg_array_paping_temp = [paping[3], paping[8], paping[13], paping[18]]
        # print avg_array_paping_temp
        x = np.array(avg_array_paping_temp)
        avg_array_paping = x.astype(np.float)
        avg_array_paping = avg_array_paping.tolist()
        # tmp = min(values);
        # values.index(tmp)
        # [5001,5002,5003,5004] ordered array of min values for each path
        portlist_temp = [5001, 5002, 5003, 5004]
        candidate_index_port = 5001
        while (len(avg_array_paping) > 0):
            # print len(avg_array_paping)
            # print len(portlist_temp)
            if (float(min(avg_array_paping)) != 0):
                # print min(avg_array_paping)
                # print avg_array_paping
                candidate_index_temp = avg_array_paping.index(min(avg_array_paping))
                # print "candidate temp", candidate_index_temp
                break
            else:
                zero_index = avg_array_paping.index(min(avg_array_paping))
                del avg_array_paping[zero_index]
                del portlist_temp[zero_index]
                # print "minimum is zero"
        if (len(avg_array_paping) != 0):
            candidate_index_port = portlist_temp[candidate_index_temp]
        # print candidate_index_port
        list_1 = self.paping_path_list.get(temp_key_1, None)
        # print list_1
        # print
        cadidate_path_index = list_1[0].index(candidate_index_port)
        # print cadidate_path_index
        candidate_path = list_1[1][cadidate_path_index]
        # print candidate_path
        x = str(SrcIP).split(".")
        y = str(DstIP).split(".")
        flowID = str(x[3]) + str(y[3])
        rvflowID = str(y[3]) + str(x[3])
        priority = 40
        # print "list -1", candidate_path, SrcMAC, DstMAC, priority
        self.push_path(candidate_path, SrcMAC, DstMAC, flowID, priority)
        candidate_path_rev = list(reversed(candidate_path))
        # print "list -1", candidate_path_rev, DstMAC, SrcMAC, priority
        self.push_path(candidate_path_rev, DstMAC, SrcMAC, rvflowID, priority)
        # print candidate_path, candidate_index

        # p1 = getBestPath(SrcMAC,DstMAC, str(SrcIP),str(DstIP),d,j,l,u)
        # print p1

    def set_paping_path(self, SrcMAC, DstMAC, srcIP, dstIP):
        # print "set paping path"
        tableID = '0'
        path_list = []
        port_list = []
        path_list_dictionary = {}
        x = str(srcIP).split(".")
        y = str(dstIP).split(".")
        flowID = str(x[3]) + str(y[3])
        rvflowID = str(y[3]) + str(x[3])
        priority = 20
        paths = self.getCaditatePaths(srcIP, dstIP)
        count = 0
        # print paths
        for p in paths:
            if str(p[3]) == 'openflow:1':
                count = 5001
                port_list.append(count)
                path_list.append(p)
            elif str(p[3]) == 'openflow:2':
                count = 5002
                port_list.append(count)
                path_list.append(p)
            elif str(p[3]) == 'openflow:3':
                count = 5003
                port_list.append(count)
                path_list.append(p)
            elif str(p[3]) == 'openflow:4':
                count = 5004
                port_list.append(count)
                path_list.append(p)
            flowID_new = str(int(flowID) * 10 + count)
            rvflowID_new = str(int(rvflowID) * 10 + count)
            self.push_path_port(p, count, SrcMAC, DstMAC, srcIP, dstIP, flowID_new, rvflowID_new, priority)
        # print port_list
        # print path_list
        # print type(p)
        return port_list, path_list

    def get_delay_jitter(self, srcIP, dstIP):
        path = self.getCaditatePaths(srcIP, dstIP)
        case = len(path)
        list_ip_ping = ''
        list_ID_ping = ''
        src_dst_ID = ''
        if case == 1:
            print ("only one hop")
            print (path)
            src_sw_id_, port_1 = self.getIndex(path[0][1])
            mid_sw_id_ = src_sw_id_
            mid_sw_ip_ = '10.0.0.' + str(mid_sw_id_ + 100)
            dst_sw_id_ = src_sw_id_
            list_ip_ping = mid_sw_ip_
            list_ID_ping = str(mid_sw_id_)
            rtt_src = 0
            rtt_dst = 0
            src_dst_ID = src_sw_id_ + ' ' + src_sw_id_
        elif case == 2:
            print ("pod level0")
            src_sw_id_ = [0, 0]
            mid_sw_id_ = [0, 0]
            mid_sw_ip_ = ['', '']
            dst_sw_id_ = [0, 0]
            for i in 0, 1:
                # print path[i]
                src_sw_id_[i], port_1 = self.getIndex(path[i][1])
                # print src_sw_id_[i]
                mid_sw_id_[i], port_1 = self.getIndex(path[i][2])
                mid_sw_ip_[i] = '10.0.0.' + str(mid_sw_id_[i] + 100)
                # print '10.0.0.'+str(mid_sw_id_[i])
                dst_sw_id_[i], port_1 = self.getIndex(path[i][3])
                # print dst_sw_id_[i]
                src_dst_ID = str(src_sw_id_[0]) + ' ' + str(dst_sw_id_[0])
            list_ip_ping = mid_sw_ip_[0] + ' ' + mid_sw_ip_[1]
            list_ID_ping = str(mid_sw_id_[0]) + ' ' + str(mid_sw_id_[1])
            # print list_ip_ping
            rtt_src, rtt_dst = self.get_avg_mdev(srcIP, dstIP, list_ip_ping)
        else:
            # print "core level"
            src_sw_id_ = [0, 0, 0, 0]
            mid_sw_id_ = [0, 0, 0, 0]
            mid_sw_ip_ = ['', '', '', '']
            dst_sw_id_ = [0, 0, 0, 0]
            for i in 0, 1, 2, 3:
                # print "path-through-core", path[i]
                src_sw_id_[i], port_1 = self.getIndex(path[i][1])
                mid_sw_id_[i], port_1 = self.getIndex(path[i][3])
                mid_sw_ip_[i] = '10.0.0.' + str(mid_sw_id_[i] + 100)
                dst_sw_id_[i], port_1 = self.getIndex(path[i][5])
            src_dst_ID = str(src_sw_id_[0]) + ' ' + str(dst_sw_id_[0])
            list_ip_ping = mid_sw_ip_[0] + ' ' + mid_sw_ip_[1] + ' ' + mid_sw_ip_[2] + ' ' + mid_sw_ip_[3]
            list_ID_ping = str(mid_sw_id_[0]) + ' ' + str(mid_sw_id_[1]) + ' ' + str(mid_sw_id_[2]) + ' ' + str(
                mid_sw_id_[3])
            rtt_src, rtt_dst = self.get_avg_mdev(srcIP, dstIP, list_ip_ping)
        return rtt_src, rtt_dst, list_ID_ping, src_dst_ID

    def get_avg_mdev(src_host, dst_host, ip_list):
        listenPort = 5000
        s1 = socket.socket()
        s2 = socket.socket()
        print ('get average', ip_list)
        print ('Socket created')
        try:
            s1.connect((src_host, listenPort))
            s2.connect((dst_host, listenPort))
        except socket.error as msg:
            # print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
            sys.exit()
        # print 'get average', ip_list
        s1.send(ip_list)
        s2.send(ip_list)
        rtt_src = s1.recv(1024).decode()
        s1.close()
        rtt_dst = s2.recv(1024).decode()
        s2.close()
        return rtt_src, rtt_dst

    def get_delay_loss_paping(src_host, dst_host):
        listenPort = 5000
        send_message = dst_host
        s1 = socket.socket()
        print('Socket created')
        print(src_host)
        try:
            s1.connect((src_host, listenPort))
        except socket.error as msg:
            print ('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()
        s1.send(send_message)
        paping_src_value = s1.recv(1024).decode()
        s1.close()
        return paping_src_value

    #######################################################################################################
    # set shortest path QoS paper 5
    # ------------------------------------------------------------------------------------------------------
    def set_Shortest_path_QoS_Utilization(self, SrcMAC, DstMAC, flowID, rvflowID):
        print "calculate short path"
        linkCost = []
        priority = 40
        SrcMAC_1 = "host:" + SrcMAC
        DstMAC_1 = "host:" + DstMAC
        item_1 = str(SrcMAC + ',' + DstMAC)
        # lock.acquire(True)
        paths = self.getCaditatePaths(SrcMAC_1, DstMAC_1)
        LinkstateMatrix = data_collected.getLinkStatAdjaencyMatrix().astype(int)
        # errorMatrix = data_collected.getLinkerrAdjaencyMatrix()
        # lock.release()
        for i in paths:
            linkCost.append(self.calculatePathCost(i, LinkstateMatrix))
        selectedPathIndex = linkCost.index(min(linkCost))
        selected_path = paths[selectedPathIndex]
        i=0
        resp1 = False
        # lock.acquire(True)
        print selected_path
        self.push_path(selected_path, SrcMAC, DstMAC, flowID, priority)
        # print resp
        # selected_rev_path = list(reversed(selected_path))
        # resp2 = self.push_path(selected_rev_path, DstMAC, SrcMAC, rvflowID, priority)
        # track_flow[item_1] = time.time()
        # lock.release()

    def calculatePathCost(self, path, LinkStatMatrix):
        linkCost = 0
        for i in range(1, len(path) - 2):
            edge = self.find_edge(path[i], path[i + 1])
            sw_edge_src, port_src = self.getIndex(edge['source']['source-tp'])
            sw_edge_dst, port_dst = self.getIndex(edge['destination']['dest-tp'])
            tempLinkcost = (LinkStatMatrix[sw_edge_src][sw_edge_dst] + LinkStatMatrix[sw_edge_src][sw_edge_dst]) / 2
            if tempLinkcost > linkCost:
                linkCost = tempLinkcost
        return linkCost

    def get_elephant_flows(self, Threshold):
        elephant_flows = []
        a = data_collected.get_Byte_traffic_status_utilization_matrix()
        for i, j in range(0, len(a) - 1, 1):
            if a[i][j] > Threshold:
                elephant_flows.append((i, j))
        return elephant_flows

    def get_large_avg_pkt(self, Threshold):
        elephant_pkt = []
        a = data_collected.get_Byte_traffic_status_utilization_matrix()
        b = data_collected.get_packet_traffic_status_utilization_matrix()
        for i, j in range(0, len(a) - 1, 1):
            if a[i][j] / b[i][j] > Threshold:
                elephant_pkt.append((i, j))
        return elephant_pkt

    #######################################################################################################
    # set shortest path Congestion control paper 6
    # ------------------------------------------------------------------------------------------------------
    def fix_congested_flows(self, priority = 50):
        set_path = 0
        adjMatrix = []
        OnesMatrix = np.ones([len(data_collected.getLinkStatAdjaencyMatrix()[0]),len(data_collected.getLinkStatAdjaencyMatrix()[0])])
        graphMatrix = data_collected.getLinkStatAdjaencyMatrix().astype(int) + data_collected.getAdjaencyMatrix().astype(int) + OnesMatrix.astype(int)
        graph = np.delete(graphMatrix, [0], 0)
        for i in graph:
            j = (np.delete(i, [0])).tolist()
            adjMatrix.append(j)
        utilization = data_collected.get_Byte_port_utilization()
        # indices = np.where(utilization >= 1300)
        ind = np.unravel_index(np.argmax(utilization, axis=None), utilization.shape)
        # M = data_collected.get_Congested_port_utilization_matrix()
        current_link_cost_congested_path = utilization[ind[0]][ind[1]]
        switch_ID = str(ind[0])
        port_ID = str(ind[1])
        x = data_collected.getRuleState(switch_ID, port_ID)
        size_x_traffic = []
        flowID = []
        rvflowID = []
        for item in x:
            # src_MAC = item[0]
            # dst_MAC = item[1]
            a = str(data_collected.getIP_from_Mac(item[0])).split(".")
            src_ID = a[3]
            b = str(data_collected.getIP_from_Mac(item[1])).split(".")
            Dst_ID = b[3]
            flowID.append(str(src_ID) + str(Dst_ID) + "1")
            rvflowID.append(str(Dst_ID) + str(src_ID) + "1")
            data_collected.update_Byte_packet_Traffic_Matrix()
            traffic_cost = data_collected.get_Byte_traffic_status_utilization_matrix()
            size_x_traffic.append(traffic_cost[src_ID][Dst_ID])
        while (x):
            traffic_value = max(size_x_traffic)
            rerouting_flow_index = size_x_traffic.index(max(size_x_traffic))
            temp = x[rerouting_flow_index]
            SrcMAC = temp[0]
            DstMAC = temp[1]
            SrcMAC_1 = "host:" + SrcMAC
            DstMAC_1 = "host:" + DstMAC
            Src_switch = [n for n in config.graph.neighbors(SrcMAC_1)]
            Dst_switch = [n for n in config.graph.neighbors(DstMAC_1)]
            Src_sw_id = int((str(Src_switch).split(":")[1])[:-2])
            Dst_sw_id = int((str(Dst_switch).split(":")[1])[:-2])
            temp_new_path, cost = g.dijkstra(adjMatrix, (Src_sw_id - 1), (Dst_sw_id - 1))
            if (cost + traffic_value) < current_link_cost_congested_path:
                best_path = [x + 1 for x in temp_new_path]
                best_path_name = []
                for i in best_path:
                    x = ('openflow:' + str(i))
                    best_path_name.append(x)
                best_path_name.insert(0, SrcMAC_1)
                best_path_name.append(DstMAC_1)
                # print "list -1", best_path_name, SrcMAC, DstMAC, priority
                self.push_path(best_path_name, SrcMAC, DstMAC, flowID[rerouting_flow_index], priority)
                best_path_name_rev = list(reversed(best_path_name))
                # # print "list -1", best_path_name_rev, DstMAC, SrcMAC, priority
                self.push_path(best_path_name_rev, DstMAC, SrcMAC, rvflowID[rerouting_flow_index], priority)
                set_path = 1
                break
            else:
                size_x_traffic.remove(size_x_traffic[rerouting_flow_index])
                x.remove(x[rerouting_flow_index])
                flowID.remove(flowID[rerouting_flow_index])
                rvflowID.remove(rvflowID[[rerouting_flow_index]])

    # caclulate the path based on the utilization matrix and a modified dijkstra algorithm
    def set_dijkstra_Utilization_QoS(self, SrcMAC, DstMAC, flowID,rvflowID):
        adjMatrix = []
        priority = 50
        SrcMAC_1 = "host:" + SrcMAC
        DstMAC_1 = "host:" + DstMAC
        Src_switch = [n for n in config.graph.neighbors(SrcMAC_1)]
        Dst_switch = [n for n in config.graph.neighbors(DstMAC_1)]
        Src_sw_id = int((str(Src_switch).split(":")[1])[:-2])
        Dst_sw_id = int((str(Dst_switch).split(":")[1])[:-2])
        # get the graph Matrix
        # graphMatrix = data_collected.getAdjaencyMatrix()
        OnesMatrix = np.ones(
            [len(data_collected.getLinkStatAdjaencyMatrix()[0]), len(data_collected.getLinkStatAdjaencyMatrix()[0])])
        graphMatrix = data_collected.getLinkStatAdjaencyMatrix().astype(
            int) + data_collected.getAdjaencyMatrix().astype(int) + OnesMatrix.astype(int)
        graph = np.delete(graphMatrix, [0], 0)
        for i in graph:
            j = (np.delete(i, [0])).tolist()
            adjMatrix.append(j)
        temp_best_path, cost = g.dijkstra(adjMatrix, (Src_sw_id - 1), (Dst_sw_id - 1))
        best_path = [x + 1 for x in temp_best_path]
        best_path_name = []
        for i in best_path:
            x = ('openflow:' + str(i))
            best_path_name.append(x)
        best_path_name.insert(0, SrcMAC_1)
        best_path_name.append(DstMAC_1)
        # print "list -1", best_path_name, SrcMAC, DstMAC, priority
        self.push_path(best_path_name, SrcMAC, DstMAC, flowID, priority)
        best_path_name_rev = list(reversed(best_path_name))
        # # print "list -1", best_path_name_rev, DstMAC, SrcMAC, priority
        self.push_path(best_path_name_rev, DstMAC, SrcMAC, rvflowID, priority)

    # calculate the path based on the lowest utilizaed shorted path

    ######################################################################################################
    # push path and build URLs
    # -----------------------------------------------------------------------------------------------------
    def push_path(self, path, SrcMAC, DstMAC, flowID, priority):
        status = False
        ix = str(SrcMAC + ',' + DstMAC)
        try:
            for i in range(1, len(path) - 1, 1):
                # print path[i], path[i + 1]
                edge_egress = self.find_edge(path[i], path[i + 1])
                port_egress = self.getIndex(edge_egress['source']['source-tp'])
                nodeID = path[i]
                print ("nodeID", nodeID)
                # edge_ingress = self.find_edge(path[i - 1], path[i])
                # # print edge_ingress
                # port_ingress = self.getIndex(edge_ingress['destination']['dest-tp'])
                newFlow = self.build_flow_src_dst_MAC('ip-1', str(port_egress[1]), str(SrcMAC), str(DstMAC), flowID, priority)
                # print newFlow
                Url = self.build_flow_url(nodeID, "0", flowID)
                # lock.acquire(True)
                resp, content = self.post_dict(Url, newFlow)
                # lock.release()
                print resp
        except:
            print "except"
            if ix in track_flow:
                print "remove -----",ix
                track_flow.remove(ix)
        print "$$$$$$$$$$$$$$$installed flow------------", ix
        # print SrcMAC, "   and  ",DstMAC, "\n*****OK*********"

    def push_path_port(self, path, dstPort, SrcMAC, DstMAC, srcIP, dstIP, flowID, rvflowID, priority):
        for i in range(1, len(path) - 1, 1):
            edge_egress = self.find_edge(path[i], path[i + 1])
            port_egress = self.getIndex(edge_egress['source']['source-tp'])
            nodeID = path[i]
            edge_ingress = self.find_edge(path[i - 1], path[i])
            port_ingress = self.getIndex(edge_ingress['destination']['dest-tp'])
            if dstPort == 0:
                newFlow = self.build_flow_srcdst('foward-port-2', port_ingress[1], port_egress[1], dstPort, SrcMAC,
                                                 DstMAC, srcIP + "/32", dstIP + "/32", flowID, priority)
                revFlow = self.build_flow_srcdst('reverse-port-2', port_egress[1], port_ingress[1], dstPort, DstMAC,
                                                 SrcMAC, dstIP + "/32", srcIP + "/32", rvflowID, priority)
            else:
                newFlow = self.build_flow_srcdstIP_dstport('foward-port-2', port_ingress[1], port_egress[1], dstPort,
                                                           SrcMAC, DstMAC, srcIP + "/32", dstIP + "/32", flowID,
                                                           priority)
                revFlow = self.build_flow_srcdstIP_srcport('reverse-port-2', port_egress[1], port_ingress[1], dstPort,
                                                           DstMAC, SrcMAC, dstIP + "/32", srcIP + "/32", rvflowID,
                                                           priority)
            # print nodeID
            # print newFlow
            # print revFlow
            Url = self.build_flow_url(nodeID, "0", flowID)
            rvUrl = self.build_flow_url(nodeID, "0", rvflowID)
            resp, content = self.post_dict(rvUrl, revFlow)
            resp, content = self.post_dict(Url, newFlow)

    ###################################################################################################
    # build a URL
    # ---------------------------------------------------------------------------------------------------
    def build_flow_src_dst_MAC(self, flowName, EgressPort, srcMAC, dstMAC, flowID, priority):
        newFlow = {
            "flow": {
                "instructions": {
                    "instruction": {
                        "order": "0",
                        "apply-actions": {
                            "action": {
                                "order": "0",
                                "output-action": {
                                    "output-node-connector": EgressPort,
                                }
                            }
                        }
                    }
                },
                "table_id": "0",
                "id": flowID,
                "match": {
                    "ethernet-match": {
                        # "ethernet-type": {"type": "45"},
                        "ethernet-destination": {"address": dstMAC},
                        "ethernet-source": {"address": srcMAC}
                    }
                },
                # "hard-timeout": "30",
                "cookie": "4",
                "idle-timeout": "1600",
                "flow-name": flowName,
                "priority": priority,
            }
        }
        return newFlow

    def build_flow_url(self, nodeID, tableID, flowID):
        url = "http://" + self.controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + nodeID + "/table/" + tableID + "/flow/" + flowID
        return url

    def build_flow_srcdstIP_dstport(self, flowName, inport, EgressPort, dstPort, SrcMAC, DstMAC, srcIP, dstIP, flowID,
                                    priority):
        # print EgressPort, "--", dstPort,SrcMAC,DstMAC,srcIP,dstIP,flowID
        newFlow = {"flow":
            {
                "id": flowID,
                "instructions": {
                    "instruction": {
                        "order": "0",
                        "apply-actions": {
                            "action": [
                                {"order": "0",
                                 "output-action": {"output-node-connector": EgressPort, "max-length": "65535"}}
                            ]
                        }
                    }
                },
                "flow-name": flowName,
                "match": {
                    "ethernet-match": {
                        "ethernet-type": {"type": "2048"},
                        "ethernet-destination": {"address": DstMAC},
                        "ethernet-source": {"address": SrcMAC}
                    },
                    "ipv4-source": srcIP,
                    "ipv4-destination": dstIP,
                    "ip-match": {
                        "ip-protocol": "6"
                    },
                    "tcp-destination-port": dstPort,
                    "in-port": inport

                    # "udp-source-port": srcPort,
                    # "udp-destination-port":dstPort,
                },
                "priority": priority,
                "table_id": "0",
                "idle-timeout": "80"
        }
        }
        return newFlow

    def build_flow_srcdstIP_srcport(self, flowName, inport, EgressPort, srcPort, SrcMAC, DstMAC, srcIP, dstIP, flowID,
                                    priority):
        # print EgressPort, "--", srcPort,SrcMAC,DstMAC,srcIP,dstIP,flowID
        newFlow = {"flow":
            {
                "id": flowID,
                "instructions": {
                    "instruction": {
                        "order": "0",
                        "apply-actions": {
                            "action": [
                                {"order": "0",
                                 "output-action": {"output-node-connector": EgressPort, "max-length": "65535"}}
                            ]
                        }
                    }
                },
                "flow-name": flowName,
                "match": {
                    "ethernet-match": {
                        "ethernet-type": {"type": "2048"},
                        "ethernet-destination": {"address": DstMAC},
                        "ethernet-source": {"address": SrcMAC}
                    },
                    "ipv4-source": srcIP,
                    "ipv4-destination": dstIP,
                    "ip-match": {
                        "ip-protocol": "6"
                    },
                    "tcp-source-port": srcPort,
                    "in-port": inport

                    # "udp-source-port": srcPort,
                    # "udp-destination-port":dstPort,
                },
                "priority": priority,
                "table_id": "0"
            }
        }
        return newFlow

    # #######################################################################################################
    # Delete all flows in a node
    # ------------------------------------------------------------------------------------------------------
    def delete_all_flows_node(self, node, tableID):
        print (node)
        url = "http://" + config.controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + node
        resp, content = config.h.request(url, "GET")
        allFlows = json.loads(content)
        # print(allFlows)
        try:
            for m in allFlows['node'][0]['flow-node-inventory:table'][0]['flow']:
                # print(m['id'])
                delurl = "http://" + config.controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + node + "/table/" + str(tableID) + "/flow/" + str(m['id'])
                # delurl = "http://" + config.controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + node + "/table/" + tableID + "/flow/" + flowID
                resp, content = config.h.request(delurl, "DELETE")
        except:
            pass
            #
    # #######################################################################################################
    # Delete specific flow specified by nodeid and flowname
    # ------------------------------------------------------------------------------------------------------
    # def delete_spec_flow_node(node, tableID, flowID):
    #     delurl = "http://" + controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + node + "/table/" + tableID + "/flow/" + flowID
    #     resp, content = h.request(delurl, "DELETE")
    #     print 'resp %s content %s', resp, content
    # ######################################################################################################
    # post the using URL and flow in json
    # ---------------------------------------------------------------------------------------------
    def post_dict(self, url, d):
        resp, content = config.h.request(
            uri=url,
            method='PUT',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(d)
        )
        return resp, content

    #######################################################################################################
    # get flow cost
    # ------------------------------------------------------------------------------------------------------
    def find_edge(self, headNode, tailNode):
        for edge in config.odlEdges:
            if (edge['source']['source-node'] == headNode) and (edge['destination']['dest-node'] == tailNode):
                return edge

    def gethostID_from_IP(self, IP):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if node['host-tracker-service:addresses'][0]['ip'] == IP:
                    return node['node-id']
        return -1

    def gethostID_from_Mac(self, MAC):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if node['host-tracker-service:addresses'][0]['mac'] == MAC:
                    return node['node-id']
        return -1

    def getMac_from_host_ID(self, hostID):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if node['node-id'] == hostID:
                    return node['host-tracker-service:addresses'][0]['mac']
        return -1

    def getIP_from_host_ID(self, hostID):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if node['node-id'] == hostID:
                    return node['host-tracker-service:addresses'][0]['ip']
        return -1

    def getIP_from_Mac(self, Mac):
        for node in config.odlNodes:
            # print node
            if node['node-id'].find("openflow") != 0:
                # print node['host-tracker-service:addresses'][0]['mac']
                # print type(node['host-tracker-service:addresses'][0]['mac'])
                if node['host-tracker-service:addresses'][0]['mac'] == Mac:
                    return node['host-tracker-service:addresses'][0]['ip']
        return -1

    def getMac_from_IP(self, IP):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if node['host-tracker-service:addresses'][0]['ip'] == IP:
                    return node['host-tracker-service:addresses'][0]['mac']
        return -1

c = calculateRoute(data_collected)
track_flow = []
process_flow = []
list_traffic_utilization_pairs = []
list_traffic_pairs_ID =[]
list_traffic_pairs_MAC = []
lock = threading.Lock()

# lock = threading.Lock()
def get_congested_port_candidate(port_utilization):
    max_switch_ID = -1
    max_port_ID = -1
    max_utilized_port_value = -1
    for i in config.agregation_switch_list:
        print i, '--', port_utilization[i]
        for y in port_utilization[i]:
            if max_utilized_port_value < y:
                max_utilized_port_value = y
                max_port_ID = port_utilization[i].tolist().index(y)
                max_switch_ID = i
    return max_utilized_port_value, max_switch_ID, max_port_ID

def get_list_communicating_nodes(switch_ID, port_ID):
    list_source, list_dst, list_port = data_collected.getRuleState(switch_ID, port_ID)
    print list_source
    print list_dst
    print list_port
    for i in range(0, len(list_dst), 1):
        # print config.maplist1
        src_id = int(str(config.maplist1[list_source[i]]).split(".")[3])
        dst_id = int(str(config.maplist1[list_dst[i]]).split(".")[3])
        print src_id, 'is talking to', dst_id, "on switch", switch_ID, 'port number', list_port[i]
        set_ID_pairs = {src_id, dst_id}
        set_MAC_pairs = {list_source[i], list_dst[i]}
        traffic_hosts = data_collected.Bytes_traffic_utilization
        if set_ID_pairs not in list_traffic_pairs_ID:
            list_traffic_pairs_ID.append(set_ID_pairs)
            list_traffic_utilization_pairs.append(traffic_hosts[src_id][dst_id])
            list_traffic_pairs_MAC.append(set_MAC_pairs)
        else:
            list_traffic_utilization_pairs[list_traffic_pairs_ID.index(set_ID_pairs)] = max(
                traffic_hosts[src_id][dst_id], traffic_hosts[dst_id][src_id])
            pass
    return list_traffic_pairs_ID, list_traffic_pairs_MAC, list_traffic_utilization_pairs

def get_best_utilization_path_cadidates(SrcMAC_1, DstMAC_1,LinkstateMatrix):
    linkCost = []
    paths = c.getCaditatePaths(SrcMAC_1, DstMAC_1)
    LinkstateMatrix = data_collected.getLinkStatAdjaencyMatrix().astype(int)
    # errorMatrix = data_collected.getLinkerrAdjaencyMatrix()
    # lock.release()
    for i in paths:
        linkCost.append(c.calculatePathCost(i, LinkstateMatrix))
    return paths, linkCost

def compute_dijsktra_adj_Matrix(port_utilization):
    adjMatrix = np.zeros([config.Count_switches, config.Count_switches])
    for s in range(0, config.Count_switches, 1):
        for i in range(0, config.port_count, 1):
            index_switch_colon = int(config.Connection_array[s + 1][i + 1]) - 1
            if index_switch_colon != -2:
                if port_utilization[s + 1][i + 1] != 0:
                    adjMatrix[s][index_switch_colon] = port_utilization[s + 1][i + 1]
                else:
                    adjMatrix[s][index_switch_colon] = 1

    return adjMatrix

def set_dij_new_path(priority, flowID,rvflowID,SrcMAC,DstMAC,temp_best_path):
    SrcMAC_1 = "host:" + SrcMAC
    DstMAC_1 = "host:" + DstMAC
    best_path = [x + 1 for x in temp_best_path]
    best_path_name = []
    for i in best_path:
        x = ('openflow:' + str(i))
        best_path_name.append(x)
    best_path_name.insert(0, SrcMAC_1)
    best_path_name.append(DstMAC_1)
    # print "list -1", best_path_name, SrcMAC, DstMAC, priority
    c.push_path(best_path_name, SrcMAC, DstMAC, flowID, priority)
    best_path_name_rev = list(reversed(best_path_name))
    # # print "list -1", best_path_name_rev, DstMAC, SrcMAC, priority
    c.push_path(best_path_name_rev, DstMAC, SrcMAC, rvflowID, priority)

def set_new_path(priority, flowID,rvflowID,SrcMAC,DstMAC,temp_best_path):
    c.push_path(temp_best_path, SrcMAC, DstMAC, flowID, priority)
    best_path_name_rev = list(reversed(temp_best_path))
    # # print "list -1", best_path_name_rev, DstMAC, SrcMAC, priority
    c.push_path(best_path_name_rev, DstMAC, SrcMAC, rvflowID, priority)


def monitor_aggregation_old():
    priority = 50
    adjMatrix = []
    h1 = httplib2.Http(".cache")
    h1.add_credentials('admin', 'admin')
    while 1:
        lock.acquire()
        port_utilization = data_collected.get_Byte_port_utilization()
        lock.release()
        Congestion_Threshold = 15000000
        # if BW  = 50 Mbit per second the utilization is 60%      ===    100 MBit per second 70% 35000000
        # 15000000
        # 37856402
        max_utilized_port_value, max_switch_ID, max_port_ID = get_congested_port_candidate(port_utilization)

        if max_port_ID != -1 and max_switch_ID != -1 and (max_utilized_port_value> Congestion_Threshold):
            print "max switch", max_switch_ID
            print "max port", max_port_ID
            list_traffic_pairs_ID, list_traffic_pairs_MAC, list_traffic_utilization_pairs = get_list_communicating_nodes(max_switch_ID,max_port_ID)

            print 'traffic ID', list_traffic_pairs_ID
            print 'traffic MAC', list_traffic_pairs_MAC
            print 'traffic Utilization', list_traffic_utilization_pairs


            if len(list_traffic_utilization_pairs) != 0:
                max_traffic_communication_pair = max(list_traffic_utilization_pairs)
                if max_traffic_communication_pair != 0:
                    print "max_traffic_communication_pair", max_traffic_communication_pair
                    max_traffic_set_index = list_traffic_utilization_pairs.index(max_traffic_communication_pair)

                    if (max_utilized_port_value > Congestion_Threshold) and (len(list_traffic_pairs_ID)!= 0):
                        dijsktra_pairs_id = list_traffic_pairs_ID.pop(max_traffic_set_index)
                        dijsktra_pairs = list_traffic_pairs_MAC.pop(max_traffic_set_index)
                        dijsktra_pairs_traffic_utilization = list_traffic_utilization_pairs.pop(max_traffic_set_index)
                        dijsktra_pairs = list(dijsktra_pairs)
                        dijsktra_pairs_id = list(dijsktra_pairs_id)
                        SrcMAC, DstMAC = dijsktra_pairs[0], dijsktra_pairs[1]
                        ID1 , ID2 = dijsktra_pairs_id[0], dijsktra_pairs_id[1]
                        flowID = str(ID1) + str(ID2)
                        rvflowID = str(ID2) + str(ID1)
                        # get the edge switch attached to the host Mac, to be used in Dijkstra route calculation
                        SrcMAC_1 = "host:" + SrcMAC
                        DstMAC_1 = "host:" + DstMAC
                        Src_switch = [n for n in config.graph.neighbors(SrcMAC_1)]
                        Dst_switch = [n for n in config.graph.neighbors(DstMAC_1)]

                        print "edgeSwitches    ", Src_switch, "------", Dst_switch

                        Src_sw_id = int((str(Src_switch).split(":")[1])[:-2])
                        Dst_sw_id = int((str(Dst_switch).split(":")[1])[:-2])
                        print "edgeSwitchesID    ", Src_sw_id , "--sw--", Dst_sw_id

                        adjMatrix = np.zeros([config.Count_switches, config.Count_switches])
                        for s in range(0, config.Count_switches, 1):
                            for i in range(0, config.port_count, 1):
                                index_switch_colon = int(config.Connection_array[s+1][i+1])-1
                                if index_switch_colon != -2:
                                    if port_utilization[s+1][i+1] != 0:
                                        adjMatrix[s][index_switch_colon] = port_utilization[s+1][i+1]
                                    else:
                                        adjMatrix[s][index_switch_colon] = 1
                        temp_best_path, cost = g.dijkstra(adjMatrix, (Src_sw_id - 1), (Dst_sw_id - 1))

                        print "temp-path", temp_best_path, "   cost", cost

                        while cost < float('inf') and (len(list_traffic_utilization_pairs) != 0):
                            if cost + dijsktra_pairs_traffic_utilization < max_utilized_port_value:
                                print "cost + dijsktra_pairs_traffic_utilization < max_utilized_port_value", cost , dijsktra_pairs_traffic_utilization, max_utilized_port_value
                                break
                            elif config.Connection_array[max_switch_ID][max_port_ID] in config.edge_Switch_list:
                                print "config.Connection_array[max_switch_ID][max_port_ID]", config.Connection_array[max_switch_ID][max_port_ID]
                                # need a new cadidate path
                                for i in range(0,len(temp_best_path)-1,1):
                                    print i, "   temp_path", temp_best_path[i], temp_best_path[i+1]
                                    adjMatrix[temp_best_path[i]][temp_best_path[i+1]] = float('inf')
                                print (adjMatrix)
                                max_traffic_communication_pair = max(list_traffic_utilization_pairs)
                                max_traffic_set_index = list_traffic_utilization_pairs.index(max_traffic_communication_pair)
                                # problems
                                dijsktra_pairs_id = list_traffic_pairs_ID.pop[max_traffic_set_index]
                                dijsktra_pairs = list_traffic_pairs_MAC.pop[max_traffic_set_index]
                                dijsktra_pairs_traffic_utilization = list_traffic_utilization_pairs.pop[max_traffic_set_index]
                                dijsktra_pairs = list(dijsktra_pairs)
                                dijsktra_pairs_id = list(dijsktra_pairs_id)
                                SrcMAC = dijsktra_pairs[0]
                                DstMAC = dijsktra_pairs[1]
                                ID1 = dijsktra_pairs_id[0]
                                ID2 = dijsktra_pairs_id[1]
                                flowID = str(ID1) + str(ID2)
                                rvflowID = str(ID2) + str(ID1)
                                # get the edge switch attached to the host Mac, to be used in Dijkstra route calculation
                                SrcMAC_1 = "host:" + SrcMAC
                                DstMAC_1 = "host:" + DstMAC
                                Src_switch = [n for n in config.graph.neighbors(SrcMAC_1)]
                                Dst_switch = [n for n in config.graph.neighbors(DstMAC_1)]
                                Src_sw_id = int((str(Src_switch).split(":")[1])[:-2])
                                Dst_sw_id = int((str(Dst_switch).split(":")[1])[:-2])
                                temp_best_path, cost = g.dijkstra(adjMatrix, (Src_sw_id - 1), (Dst_sw_id - 1))
                            elif cost < max_utilized_port_value and (cost == adjMatrix[temp_best_path[-1]][temp_best_path[-2]]):
                                break
                            else:
                                continue

                        if cost < float('inf') and cost < max_utilized_port_value:
                             best_path = [x + 1 for x in temp_best_path]
                             best_path_name = []
                             for i in best_path:
                                 x = ('openflow:' + str(i))
                                 best_path_name.append(x)
                             best_path_name.insert(0, SrcMAC_1)
                             best_path_name.append(DstMAC_1)
                             # print "list -1", best_path_name, SrcMAC, DstMAC, priority
                             c.push_path(best_path_name, SrcMAC, DstMAC, flowID, priority)
                             best_path_name_rev = list(reversed(best_path_name))
                             # # print "list -1", best_path_name_rev, DstMAC, SrcMAC, priority
                             c.push_path(best_path_name_rev, DstMAC, SrcMAC, rvflowID, priority)
                             time.sleep(2)
        time.sleep(3)

def monitor_aggregation():
    priority = 50
    adjMatrix = []
    h1 = httplib2.Http(".cache")
    h1.add_credentials('admin', 'admin')

    while 1:
        cost = -1
        lock.acquire()
        port_utilization = data_collected.get_Byte_port_utilization()
        lock.release()
        Congestion_Threshold = 15000000
        # if BW  = 50 Mbit per second the utilization is 60%      ===    100 MBit per second 70% 35000000
        # 15000000
        # 37856402
        max_utilized_port_value_temp, max_switch_ID_temp, max_port_ID_temp = get_congested_port_candidate(port_utilization)
        time.sleep(2)
        max_utilized_port_value, max_switch_ID, max_port_ID = get_congested_port_candidate(port_utilization)
        print max_utilized_port_value
        print max_utilized_port_value_temp
        print max_port_ID
        print max_port_ID_temp
        print max_switch_ID
        print max_switch_ID_temp


        if  (max_switch_ID != max_switch_ID_temp) or (max_port_ID != max_port_ID_temp):
            print "condition not equal "
            max_switch_ID = -1
            max_port_ID = -1

        print max_switch_ID
        print max_port_ID

        if max_port_ID != -1 and max_switch_ID != -1 and (max_utilized_port_value > Congestion_Threshold):
            print "max switch", max_switch_ID
            print "max port", max_port_ID
            list_traffic_pairs_ID, list_traffic_pairs_MAC, list_traffic_utilization_pairs = get_list_communicating_nodes(max_switch_ID,max_port_ID)
            print 'traffic ID', list_traffic_pairs_ID
            print 'traffic MAC', list_traffic_pairs_MAC
            print 'traffic Utilization', list_traffic_utilization_pairs

            if len(list_traffic_utilization_pairs) != 0:
                max_traffic_communication_pair = max(list_traffic_utilization_pairs)
                if max_traffic_communication_pair != 0:
                    print "max_traffic_communication_pair", max_traffic_communication_pair
                    max_traffic_set_index = list_traffic_utilization_pairs.index(max_traffic_communication_pair)
                    if (max_utilized_port_value > Congestion_Threshold) and (len(list_traffic_pairs_ID)!= 0):
                        adjMatrix = compute_dijsktra_adj_Matrix(port_utilization)
                        print adjMatrix
                        next_to_max_sw = config.Connection_array[max_switch_ID][max_port_ID]
                        print next_to_max_sw
                        print max_switch_ID

                        adjMatrix[max_switch_ID - 1][int(next_to_max_sw) - 1] = float('inf')
                        adjMatrix[int(next_to_max_sw) - 1][max_switch_ID - 1] = float('inf')

                        # temp_best_paths, linkCost = get_best_utilization_path_cadidates(SrcMAC_1, DstMAC_1, port_utilization)
                        # cost = min(linkCost)

                        while cost < float('inf') and (len(list_traffic_utilization_pairs) != 0):


                            dijsktra_pairs_id = list_traffic_pairs_ID.pop(max_traffic_set_index)
                            dijsktra_pairs = list_traffic_pairs_MAC.pop(max_traffic_set_index)
                            dijsktra_pairs_traffic_utilization = list_traffic_utilization_pairs.pop(max_traffic_set_index)
                            dijsktra_pairs = list(dijsktra_pairs)
                            dijsktra_pairs_id = list(dijsktra_pairs_id)
                            SrcMAC, DstMAC = dijsktra_pairs[0], dijsktra_pairs[1]
                            ID1 , ID2 = dijsktra_pairs_id[0], dijsktra_pairs_id[1]
                            flowID = str(ID1) + str(ID2)
                            rvflowID = str(ID2) + str(ID1)
                            # get the edge switch attached to the host Mac, to be used in Dijkstra route calculation
                            SrcMAC_1 = "host:" + SrcMAC
                            DstMAC_1 = "host:" + DstMAC

                            # selectedPathIndex = linkCost.index(min(linkCost))
                            # temp_best_path = temp_best_paths.pop(selectedPathIndex)
                            # cost = linkCost.pop(selectedPathIndex)
                            #
                            # dijsktra path calculated
                            Src_switch = [n for n in config.graph.neighbors(SrcMAC_1)]
                            Dst_switch = [n for n in config.graph.neighbors(DstMAC_1)]
                            print "edgeSwitches    ", Src_switch, "------", Dst_switch

                            Src_sw_id = int((str(Src_switch).split(":")[1])[:-2])
                            Dst_sw_id = int((str(Dst_switch).split(":")[1])[:-2])
                            print "edgeSwitchesID    ", Src_sw_id , "--sw--", Dst_sw_id

                            temp_best_path, cost = g.dijkstra(adjMatrix, (Src_sw_id - 1), (Dst_sw_id - 1))

                            print "temp-path", temp_best_path, "   cost", cost

                            # base case if the cost is good to go either ways
                            if len(temp_best_path) <= 5:

                                if cost + dijsktra_pairs_traffic_utilization < max_utilized_port_value:
                                    set_dij_new_path(priority, flowID, rvflowID, SrcMAC, DstMAC, temp_best_path)
                                    # set_new_path(priority, flowID, rvflowID, SrcMAC, DstMAC, temp_best_path)
                                    cost = float('inf')
                                # if the congestion in the core layer with a change of having the cost of the link the same as the cost of the last piece of the temp that already includes the routed traffic

                                elif (config.Connection_array[max_switch_ID][max_port_ID] in config.Core_switch_list) and cost < max_utilized_port_value and (cost == adjMatrix[temp_best_path[-1]][temp_best_path[-2]]):
                                    set_dij_new_path(priority, flowID, rvflowID, SrcMAC, DstMAC, temp_best_path)
                                    # set_new_path(priority, flowID, rvflowID, SrcMAC, DstMAC, temp_best_path)
                                    cost = float('inf')

                                # the remaining case is having congestion twards the edge swtiches or having a temp path not fullfilling the condition will the congestion is in the core layer
                                else:
                                    i = len(temp_best_path)//2
                                    adjMatrix[temp_best_path[i]][temp_best_path[i+1]] = float('inf')
                                    adjMatrix[temp_best_path[+i+1]][temp_best_path[i]] = float('inf')
                                    if len(list_traffic_utilization_pairs) != 0 and max_traffic_communication_pair != 0:
                                        max_traffic_communication_pair = max(list_traffic_utilization_pairs)
                                        max_traffic_set_index = list_traffic_utilization_pairs.index(max_traffic_communication_pair)
                                    else:
                                        cost = cost = float('inf')
                            time.sleep(2)


def monitor_edge_port_events():
    # print "thread events"
    ws = WebSocketclient.WebSockettracker()
    TTL = time.time()
    # print "TTL time"
    # print TTL
    while 1:
        e = ws.events.get()
        print e
        # srcIP = c.getIP_from_Mac(e[0])
        # dstIP = c.getIP_from_Mac(e[1])
        srcIP = config.maplist[e[0]]
        dstIP = config.maplist[e[1]]

        item = str(e[0] + ',' + e[1])
        item_2 = str(e[1] + ',' + e[0])
        # print flowID
        print srcIP, '----------------------------', dstIP
        # print "track+++++++++++++++++++++++", track_flow
        # print "pass@@@@@@@@@@@@@@@@@@@@@@",process_flow
        if (item not in track_flow) and (item_2 not in track_flow) and srcIP != '10.0.0.19' and dstIP != '10.0.0.19' and srcIP != '10.0.0.100' and dstIP != '10.0.0.100':
            if srcIP == -1 or dstIP == -1:
                # x = str(e[0]).split(":")
                # y = str(e[1]).split(".")
                x = int(sum([int(_, 16) for _ in e[0].split(':')]) / 10)
                y = int(sum([int(_, 16) for _ in e[1].split(':')]) / 10)
                flowID = str(x) + str(y)
                rvflowID = str(y) + str(x)
                # print flowID
            else:
                x = str(srcIP).split(".")
                y = str(dstIP).split(".")
                flowID = str(x[3]) + str(y[3])
                rvflowID = str(y[3]) + str(x[3])
                # print flowID
            print srcIP, 'is talking to', dstIP, "flowID", flowID
            # try:
            # lock.acquire(True)
            track_flow.append(item)
            track_flow.append(item_2)
            c.set_Shortest_path_FlowID(e[0], e[1], flowID)
            # t = Thread(target=c.set_Shortest_path_FlowID, args=(e[0], e[1], flowID,))
            # c.set_Shortest_path_QoS_Utilization(str(e[0]), str(e[1]), flowID, rvflowID)
            # t = Thread(target=c.set_Shortest_path_QoS_Utilization, args=(str(e[0]), str(e[1]),flowID,rvflowID))
            # thread_list.append(t)
            # t.setDaemon(True)
            # t.start()
            # t.join()
            # process_flow.append(str(item+','+flowID+','+rvflowID))
            # finally:
            #     pass
                # lock.release()

def compute_path_rules(c):
    while 1:
        # print "print compute path000000000000000000000000000000000000000000000000000000000000", len(process_flow)
        # print process_flow
        while len(process_flow):
            print "flow-process$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$"
            # lock.acquire(True)
            print "process----------------------------",process_flow
            flow = process_flow.pop(0)
            # print flow
            Nodes = flow.split(',')
            src,dst,flowID,rvflowID = Nodes[0],Nodes[1],Nodes[2],Nodes[3]
            # c.set_Shortest_path_QoS_Utilization(src, dst,flowID,rvflowID)
            # c.set_Shortest_path_FlowID(src, dst,flowID)
            # lock.release()
            # # print "calculate short path for", item_1
            # # track_flow[item_2] = time.time()
            # t = Thread(target=c.set_Shortest_path_FlowID, args=(src, dst,flowID,))
            # t.start()
            # t.join()
            # # c.set_Shortest_path_QoS_Utilization(str(e[0]), str(e[1]), flowID, rvflowID)
            # # p = Process(target=c.set_Shortest_path_QoS_Utilization, args=(str(e[0]), str(e[1]),flowID,rvflowID))
            # # p.start()
            # # p.join()
            # # t = Thread(target=c.set_Shortest_path_QoS_Utilization, args=(str(e[0]), str(e[1]),flowID,rvflowID))
            # # t.start()
            # # # t.join()
            # # t = Thread(target=c.set_dijkstra_Utilization_QoS, args=(str(e[0]), str(e[1]), flowID, rvflowID))
            # # t.start()
            #
            # c.set_Shortest_path_FlowID(str(e[0]), str(e[1]),flowID)
            #  set_Shortest_path_QoS(e[0],e[1],d,j,l,u)
            #  set_Shortest_path_QoS_proactive(str(e[0]),str(e[1]))
            # Object_c.set_dijkstra_Utilization_QoS_proactive_passive(str(e[0]), str(e[1]),srcIP,dstIP, 1, 0, 0)
            #  calculateRoute.set_Shortest_path_QoS_Utilization(Object_c,str(e[0]),str(e[1]),srcIP,dstIP,1,0,0)
            # set_Shortest_path(str(e[0]), str(e[1]))
            # calculateRoute.set_Shortest_path_QoS_proactive_passive(Object_c, str(e[0]), str(e[1]), 1, 0, 0)

def metric_matrices(Object_d):
    while 1:
        data_collected.update_metric_Matrices()

#######################################################################################################
# main program
#######################################################################################################
def main():
    # # this thread is continuously updating the the link utilization matrix
    # threads = []
    # worker_1 = Thread(target=monitor_link_utlization, args=())
    # worker_1.setDaemon(True)
    # threads.append(worker_1)
    # worker_1.start()
    # time.sleep(5)

    W1 = Thread(target=metric_matrices, args=(data_collected,))
    # W1.daemon =True
    W1.setDaemon(True)
    W1.start()
    print("next thread")
    # time.sleep(5)

    # #******************************
    # # clean all flows
    # #******************************
    # # switch_list = ['openflow:1','openflow:2','openflow:3','openflow:4','openflow:5','openflow:6','openflow:7',
    # #                'openflow:8','openflow:9','openflow:10','openflow:11','openflow:12','openflow:13','openflow:14',
    # #                'openflow:15','openflow:16','openflow:17','openflow:18','openflow:19','openflow:20']
    # # for n in switch_list:
    # #     c.delete_all_flows_node(n,'0')
    #
    # # print config.odlEdges
    #
    # # time.sleep(20)
    # # # utilization_matrix = collectObject.get_Byte_link_utilization()
    # # ws.start_listening()
    #
    # # a,b,c = d.get_Bytes_PortStats_Matrix()
    # # time.sleep(4)
    # # a1,b1,c1 = d.get_Bytes_PortStats_Matrix()
    #
    # # print a1-a
    # # print b1-b
    # # print c1-c
    # # d.update_Byte_packet_port_utilization()
    #
    # # print d.get_Byte_port_utilization()
    # # print d.get_Byte_port_utilization_rx()
    # # print d.get_Byte_port_utilization_tx()
    # # c.fix_congested_flows()
    #
    # # l = data_collected.getLinkStatAdjaencyMatrix()
    # # x,y,z = data_collected.get_Bytes_PortStats_Matrix()
    # # print x
    # # print y
    # # print z
    # #
    # # Congsrc = data_collected.getMac_from_IP("10.0.0.17")
    # # Congdst = data_collected.getMac_from_IP("10.0.0.18")
    # #
    # # path1 = ["host:" + Congsrc, u'openflow:16', u'openflow:14', u'openflow:4', u'openflow:18', u'openflow:20', "host:" + Congdst]
    # # rpath1 = list(reversed(path1))
    # # c.set_congested_path(Congsrc, Congdst, path1)
    # # c.set_congested_path(Congdst, Congsrc, rpath1)
    #
    SrcBG = -1
    DstBG2 = -1
    DstBG3 = -1
    DstBG4 = -1
    DstBG5 = -1
    DstBG6 = -1
    DstBG7 = -1
    DstBG8 = -1
    #
    time.sleep(5)

    while SrcBG==-1:
        SrcBG = data_collected.getMac_from_IP("10.0.0.1")
    while DstBG2 == -1:
        DstBG2 = data_collected.getMac_from_IP("10.0.0.2")
    while DstBG3 == -1:
        DstBG3 = data_collected.getMac_from_IP("10.0.0.3")
    while DstBG4 == -1:
        DstBG4 = data_collected.getMac_from_IP("10.0.0.4")
    while DstBG5 == -1:
        DstBG5 = data_collected.getMac_from_IP("10.0.0.5")
    while DstBG6 == -1:
        DstBG6 = data_collected.getMac_from_IP("10.0.0.6")
    while DstBG7 == -1:
        DstBG7 = data_collected.getMac_from_IP("10.0.0.7")
    while DstBG8 == -1:
        DstBG8 = data_collected.getMac_from_IP("10.0.0.8")

    c.set_Shortest_path_FlowID(SrcBG, DstBG2,'12')
    c.set_Shortest_path_FlowID(SrcBG, DstBG3,'13')
    c.set_Shortest_path_FlowID(SrcBG, DstBG4,'14')
    c.set_Shortest_path_FlowID(SrcBG, DstBG5,'15')
    c.set_Shortest_path_FlowID(SrcBG, DstBG6,'16')
    c.set_Shortest_path_FlowID(SrcBG, DstBG7,'17')
    c.set_Shortest_path_FlowID(SrcBG, DstBG8,'18')

    # time.sleep(5)

    # SrcBG1 = data_collected.getMac_from_IP("10.0.0.1")
    # print SrcBG1
    # DstBG11 = data_collected.getMac_from_IP("10.0.0.8")
    # print DstBG11
    # #
    # #
    # path1 = ["host:" + SrcBG1, u'openflow:7', u'openflow:5', u'openflow:1', u'openflow:17', u'openflow:20', "host:" + DstBG11]
    # rpath1 = list(reversed(path1))
    # c.set_congested_path(SrcBG1, DstBG11, path1)
    # c.set_congested_path(DstBG11,SrcBG1, rpath1)
    #
    #
    #
    # SrcBG2 = data_collected.getMac_from_IP("10.0.0.9")
    # DstBG21 = data_collected.getMac_from_IP("10.0.0.2")
    # DstBG22 = data_collected.getMac_from_IP("10.0.0.3")
    # DstBG23 = data_collected.getMac_from_IP("10.0.0.10")
    # path1 = ["host:" + SrcBG2, u'openflow:7', u'openflow:5', u'openflow:8', "host:" + DstBG21]
    # rpath1 = list(reversed(path1))
    # path1 = ["host:" + SrcBG2, u'openflow:7', u'openflow:5', u'openflow:1', u'openflow:17', u'openflow:20', "host:" + DstBG22]
    # rpath1 = list(reversed(path1))
    # path1 = ["host:" + SrcBG2, u'openflow:7', u'openflow:5', u'openflow:8', "host:" + DstBG23]
    # rpath1 = list(reversed(path1))
    #
    # SrcBG3 = data_collected.getMac_from_IP("10.0.0.16")
    # DstBG31 = data_collected.getMac_from_IP("10.0.0.4")
    # DstBG32 = data_collected.getMac_from_IP("10.0.0.6")
    # DstBG33 = data_collected.getMac_from_IP("10.0.0.7")
    #
    #
    # # SrcBGlog = data_collected.getMac_from_IP("10.0.0.3")
    # # SrcBG = data_collected.getMac_from_IP("10.0.0.1")
    # # SrcBG = data_collected.getMac_from_IP("10.0.0.9")
    # # DstBG1 = data_collected.getMac_from_IP("10.0.0.11")
    # # DstBG2 = data_collected.getMac_from_IP("10.0.0.12")
    # # DstBG3 = data_collected.getMac_from_IP("10.0.0.13")
    # # DstBG4 = data_collected.getMac_from_IP("10.0.0.6")
    # # DstBG5 = data_collected.getMac_from_IP("10.0.0.15")
    # # DstBG6 = data_collected.getMac_from_IP("10.0.0.8")
    # # #
    # # path1 = ["host:" + SrcBG, u'openflow:8', u'openflow:5', u'openflow:1', u'openflow:9', u'openflow:11', "host:" + DstBG1]
    # # path2 = ["host:" + SrcBG, u'openflow:8', u'openflow:5', u'openflow:1', u'openflow:9', u'openflow:12', "host:" + DstBG2]
    # # path3 = ["host:" + SrcBG, u'openflow:8', u'openflow:5', u'openflow:1', u'openflow:13', u'openflow:15', "host:" + DstBG3]
    # # path4 = ["host:" + SrcBG, u'openflow:8', u'openflow:5', u'openflow:1', u'openflow:13', u'openflow:16', "host:" + DstBG4]
    # # path5 = ["host:" + SrcBG, u'openflow:8', u'openflow:5', u'openflow:1', u'openflow:17', u'openflow:19', "host:" + DstBG5]
    # # path6 = ["host:" + SrcBG, u'openflow:8', u'openflow:5', u'openflow:1', u'openflow:17', u'openflow:20', "host:" + DstBG6]
    # # rpath1 = list(reversed(path1))
    # # rpath2 = list(reversed(path2))
    # # rpath3 = list(reversed(path3))
    # # rpath4 = list(reversed(path4))
    # # rpath5 = list(reversed(path5))
    # # rpath6 = list(reversed(path6))
    # # #
    # # path11 = ["host:" + SrcBGlog, u'openflow:7', u'openflow:5', u'openflow:1', u'openflow:9', u'openflow:11', "host:" + DstBG1]
    # # path12 = ["host:" + SrcBGlog, u'openflow:7', u'openflow:5', u'openflow:1', u'openflow:9', u'openflow:12', "host:" + DstBG2]
    # # path13 = ["host:" + SrcBGlog, u'openflow:7', u'openflow:5', u'openflow:1', u'openflow:13', u'openflow:15', "host:" + DstBG3]
    # # path14 = ["host:" + SrcBGlog, u'openflow:7', u'openflow:5', u'openflow:1', u'openflow:13', u'openflow:16', "host:" + DstBG4]
    # # path15 = ["host:" + SrcBGlog, u'openflow:7', u'openflow:5', u'openflow:1', u'openflow:17', u'openflow:19', "host:" + DstBG5]
    # # path16 = ["host:" + SrcBGlog, u'openflow:7', u'openflow:5', u'openflow:1', u'openflow:17', u'openflow:20', "host:" + DstBG6]
    # # rpath11 = list(reversed(path11))
    # # rpath12 = list(reversed(path12))
    # # rpath13 = list(reversed(path13))
    # # rpath14 = list(reversed(path14))
    # # rpath15 = list(reversed(path15))
    # # rpath16 = list(reversed(path16))
    # # #
    # # c.set_congested_path(SrcBG, DstBG1, path1)
    # # c.set_congested_path(DstBG1, SrcBG, rpath1)
    # # c.set_congested_path(SrcBG, DstBG2, path2)
    # # c.set_congested_path(DstBG2, SrcBG, rpath2)
    # # c.set_congested_path(SrcBG, DstBG3, path3)
    # # c.set_congested_path(DstBG3, SrcBG, rpath3)
    # # c.set_congested_path(SrcBG, DstBG4, path4)
    # # c.set_congested_path(DstBG4, SrcBG, rpath4)
    # # c.set_congested_path(SrcBG, DstBG5, path5)
    # # c.set_congested_path(DstBG5, SrcBG, rpath5)
    # # c.set_congested_path(SrcBG, DstBG6, path6)
    # # c.set_congested_path(DstBG6, SrcBG, rpath6)
    # #
    # # c.set_congested_path(SrcBGlog, DstBG1, path11)
    # # c.set_congested_path(DstBG1, SrcBGlog, rpath11)
    # # c.set_congested_path(SrcBGlog, DstBG2, path12)
    # # c.set_congested_path(DstBG2, SrcBGlog, rpath12)
    # # c.set_congested_path(SrcBGlog, DstBG3, path13)
    # # c.set_congested_path(DstBG3, SrcBGlog, rpath13)
    # # c.set_congested_path(SrcBGlog, DstBG4, path14)
    # # c.set_congested_path(DstBG4, SrcBGlog, rpath14)
    # # c.set_congested_path(SrcBGlog, DstBG5, path15)
    # # c.set_congested_path(DstBG5, SrcBGlog, rpath15)
    # # c.set_congested_path(SrcBGlog, DstBG6, path16)
    # c.set_congested_path(DstBG6, SrcBGlog, rpath16)

    # # # c.set_Shortest_path(SrcBG, DstBG1)
    # c.set_Shortest_path(SrcBG, DstBG2)
    # c.set_Shortest_path(SrcBG, DstBG3)
    # c.set_Shortest_path(SrcBG, DstBG4)
    # c.set_Shortest_path(SrcBG, DstBG5)
    # c.set_Shortest_path(SrcBG, DstBG6)
    # c.set_Shortest_path(DstBG1,SrcBG)
    # c.set_Shortest_path(DstBG2,SrcBG)
    # c.set_Shortest_path(DstBG3,SrcBG)
    # c.set_Shortest_path(DstBG4,SrcBG)
    # c.set_Shortest_path(DstBG5,SrcBG)
    # c.set_Shortest_path(DstBG6,SrcBG)
    print("start sleep")
    # time.sleep(5)
    print("wake up")

    # # # c.set_dijkstra_Utilization_QoS_proactive_passive(u'host:2e:5b:09:32:3c:76',u'host:56:21:bf:cd:2f:0f',3,4,5)
    # #
    # # #       ls.pop
    # # #    ls.insert(0, "new")
    # #
    # # #
    # # print "SSSSSSSSSSSSSSSSSSSSSS"
    # #
    # W2 = Thread(target=monitor_edge_port_events, args=(c,))
    # # W2.daemon =True
    # W2.setDaemon(True)
    # W2.start()
    # # print("next thread")
    # # print "###################"
    time.sleep(5)
    W5 = Thread(target=monitor_aggregation)
    # # # W2.daemon =True
    W5.setDaemon(True)
    W5.start()
    # print("next thread")
    # print "###################"

    # W3 = Thread(target=compute_path_rules, args=(c,))
    # # W2.daemon =True
    # W3.setDaemon(True)
    # W3.start()

    # worker_2 = Thread(target=monitor_edge_port_events(), args=())
    # threads.append(worker_2)
    # worker_2.setDaemon(True)
    # worker_2.start()
    # P2 = Process(target=monitor_edge_port_events(), args=())
    # P2.start()
    # P3.join()
    # for x in threads:
    #     x.join()
    W1.join()
    W5.join()
    # W2.join()


if __name__ == '__main__':
    main()