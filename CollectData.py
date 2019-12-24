import httplib2
import json
import datetime
import time
import numpy as np
import networkx as nx
import config
import threading


class DataCollector:
    graph = nx.Graph()
    port_count = 4
    odlNodes = {}
    odlEdges ={}
    hosts = []
    switches = []
#   THE UTILIZATION OF PORTS OVER EACH SWITCH
    Bytes_port_utilization = np.array([],dtype=float)
    Bytes_port_utilization_tx = np.array([],dtype=float)
    Bytes_port_utilization_rx = np.array([],dtype=float)
    packet_port_utilization = np.array([], dtype=float)
    packet_port_utilization_tx = np.array([], dtype=float)
    packet_port_utilization_rx = np.array([], dtype=float)

    Congested_port_utilization = np.array([], dtype=float)

#   THE nxn UTILIZATION MATRIC OF ALL HOSTS
    Bytes_traffic_utilization = np.array([],dtype=float)
    packet_traffic_utilization = np.array([],dtype=float)

    # elephant_traffic_utilization = np.array([],dtype=float)


    Adjaceny_utilization_Matrix =np.array([],dtype=float)

    edge_switch_list = ['openflow:7','openflow:8','openflow:11','openflow:12','openflow:15','openflow:16','openflow:19','openflow:20']

    adjacent_switch_matrix = []
    Byte_link_utilization = []

    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    def __init__(self):
        self.odlNodes = config.odlNodes
        self.odlEdges = config.odlEdges
        self.graph = config.graph
        self.switches = config.switches
        self.hosts = config.hosts
        Count_switches = len(self.switches)
        Count_hosts = len(self.hosts)
        self.adjacent_switch_matrix = self.get_adjacent_switch_matrix(self)
        self.Bytes_link_utilization = -1 * np.ones([Count_switches + 1, Count_switches + 1])
        self.Bytes_port_utilization = -1 * np.ones([Count_switches + 1, self.port_count + 1])
        self.Congested_port_utilization = -1 * np.ones([Count_switches + 1, self.port_count + 1])
        self.elephant_traffic_utilization = -1 * np.ones([17, 17])
    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def getIndex(sw):
            sw_id = int(sw.split(":")[1])
            try:
                port_ID = int(sw.split(":")[2])
            except:
                port_ID = -1
            return sw_id,port_ID
    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    def get_graph(self):
        return self.graph
    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    def get_switches(self):
        return self.switches
    #######################################################################################################
    # Link status Matrix MXM average byte utilization
    #------------------------------------------------------------------------------------------------------
    def update_Byte_packet_port_utilization(self):
        Byte_port_file = open("Byte_port_file.txt", "a+")
        packet_port_file = open("packet_port_file.txt", "a+")
        a,b,c = self.get_Bytes_PortStats_Matrix()
        # print a
        time.sleep(4)
        a1,b1,c1 = self.get_Bytes_PortStats_Matrix()
        self.Bytes_port_utilization = a1-a
        self.Bytes_port_utilization_rx = b1-b
        self.Bytes_port_utilization_tx = c1-c
        # b,b_rx,b_tx = self.get_Bytes_PortStats_Matrix()
        # packet_b,packet_b_rx,packet_b_tx = self.get_Packets_PortStats_Matrix()
        # time.sleep(4)
        # packet_a,packet_a_rx,packet_a_tx = self.get_Packets_PortStats_Matrix()
        # # a,a_rx,a_tx = self.get_Bytes_PortStats_Matrix()
        # self.Bytes_port_utilization1 = a - b
        # self.Bytes_port_utilization_rx1 = a_rx - b_rx
        # self.Bytes_port_utilization_tx1 = a_tx - b_tx
        # print self.Bytes_port_utilization1
        # print self.Bytes_port_utilization_rx1
        # print self.Bytes_port_utilization_tx1
        # self.packet_port_utilization = packet_a - packet_b
        # self.packet_port_utilization_rx = packet_a_rx - packet_b_rx
        # self.packet_port_utilization_tx = packet_a_tx - packet_b_tx
        # # print self.packet_port_utilization
        # print self.packet_port_utilization_rx
        # print self.packet_port_utilization_tx
        Byte_port_file.write(datetime.datetime.now().strftime("%a, %d %B %Y %I:%M:%S"))
        Byte_port_file.write(str(self.Bytes_port_utilization))
        # config.comon_byte_port_utilization = self.Bytes_port_utilization

        packet_port_file.write(datetime.datetime.now().strftime("%a, %d %B %Y %I:%M:%S"))
        packet_port_file.write(str(self.packet_port_utilization))

    #######################################################################################################
    #Traffic  Matrix MXP average byte utilization
    #------------------------------------------------------------------------------------------------------
    def update_Byte_packet_Traffic_Matrix(self):
        Byte_Traffic_file = open("Byte_Traffic_file.txt", "a+")
        packet_Traffic_file = open("packet_Traffic_file.txt", "a+")
        try:
            byte_b, packets_b, priority_b = self.get_Bytes_packet_traffic_Matrix()
            time.sleep(4)
            byte_a, packets_a, priority_a = self.get_Bytes_packet_traffic_Matrix()
            self.Bytes_traffic_utilization = byte_a - byte_b
            self.packet_traffic_utilization = packets_a - packets_b
        except:
            pass
        # need to check for negative values if exists
        # if a negative value exists replace with value from array_a
        # in the reciving function if negative value recived call update byte packet or wait

        Byte_Traffic_file.write(datetime.datetime.now().strftime("%a, %d %B %Y %I:%M:%S"))
        packet_Traffic_file.write(datetime.datetime.now().strftime("%a, %d %B %Y %I:%M:%S"))
        Byte_Traffic_file.write(str(self.Bytes_traffic_utilization))
        packet_Traffic_file.write(str(self.packet_traffic_utilization))

    def update_traffic_elephant_flow_Matrix(self,threshold= 0.05):
        time.sleep(5)
        for i in range(1, 16):
            for j in range(1,16):
                if ((self.Bytes_traffic_utilization[i][j]*8)/(100000000*5) > threshold):
                    self.elephant_traffic_utilization[i][j]=1
                else:
                    self.elephant_traffic_utilization[i][j] = 0


    def update_Byte_Congested_links_Matrix(self, threshold = 1300):
        # time.sleep(5)
        # print self.Bytes_port_utilization
        x= (len(self.Bytes_port_utilization[0]) - 1)
        for i in range(1,(len(self.Bytes_port_utilization[0]))):
            for j in range(1,len(self.Bytes_port_utilization)):
                # print (i,j)
                # print (float(self.Bytes_port_utilization[j][i]*8)/(100000000*5))
                if (self.Bytes_port_utilization[j][i] > threshold):
                # if (float(self.Bytes_port_utilization[j][i]*8)/(100000000*5) > threshold):
                    self.Congested_port_utilization[j][i]=1
                else:
                    self.Congested_port_utilization[j][i] = 0

    def update_metric_Matrices(self):
        self.update_Byte_packet_Traffic_Matrix()
        self.update_Byte_packet_port_utilization()
        # self.update_Byte_packet_Traffic_Matrix()
        # self.update_Byte_packet_port_utilization()
        # thread1 = threading.Thread(target = self.update_Byte_packet_Traffic_Matrix, args=())
        # thread2 = threading.Thread(target = self.update_Byte_packet_port_utilization(), args=())
        # thread3 = threading.Thread(target=self.update_Byte_Congested_links_Matrix(), args=())
        # thread4 = threading.Thread(target=self.update_traffic_elephant_flow_Matrix(), args=())
        # thread1.start()
        # thread2.start()
        # thread3.start()
        # thread4.start()
        # thread3.join()
        # thread4.join()
        # thread1.join()
        # thread2.join()

    #######################################################################################################
    #Link status Matrix MXM average byte utilization (UT)
    #------------------------------------------------------------------------------------------------------
    def get_Byte_port_utilization(self):
        # print self.Bytes_port_utilization
        return self.Bytes_port_utilization
    def get_Bytes(self):
        return self.Bytes_port_utilization,self.Bytes_traffic_utilization
    # def get_pkt_port_utilization(self):
    #     # print self.packet_port_utilization
    #     return self.packet_port_utilization
    def get_Byte_port_utilization_rx(self):
        # print self.Bytes_port_utilization_rx
        return self.Bytes_port_utilization_rx
    def get_Byte_port_utilization_tx(self):
        # print self.Bytes_port_utilization_tx
        return self.Bytes_port_utilization_tx

    def get_host_traffic(self,src,dst):
        return self.Bytes_traffic_utilization[src][dst]


    #######################################################################################################
    #Traffic  Matrix MXP average byte utilization (UT)
    #------------------------------------------------------------------------------------------------------
    def get_Byte_traffic_status_utilization_matrix(self):
        # print self.Bytes_traffic_utilization
        return self.Bytes_traffic_utilization

    def get_packet_traffic_status_utilization_matrix(self):
        return self.packet_traffic_utilization

    # def get_Congested_port_utilization_matrix(self):
    #     return self.Congested_port_utilization

    # def get_packet_traffic_avg_size(self):
    #     a = np.array(self.Bytes_traffic_utilization,dtype=float)
    #     b = np.array(self.packet_traffic_utilization,dtype=float)
    #     return (a/b)

    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    def get_Byte_link_utilization_value(self,x,y):
        return self.Bytes_link_utilization[x][y]
    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    def update_Byte_link_utilization(self):
        byte_port_matrix_b = self.get_Bytes_PortStats_Matrix()
        # print byte_port_matrix_b
        time.sleep(4)
        byte_port_matrix_a = self.get_Bytes_PortStats_Matrix()
        linkstatusMatrix_b = self.getLinkStatMatrix(byte_port_matrix_b)
        linkstatusMatrix_a = self.getLinkStatMatrix(byte_port_matrix_a)
        self.Bytes_link_utilization = np.array((linkstatusMatrix_a - linkstatusMatrix_b),dtype=float)
    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    def get_Byte_link_utilization(self):
        return self.Bytes_link_utilization
    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    def get_Bytes_PortStats_Matrix(self):
        resp = None
        flowStats = None
        h3 = httplib2.Http(".cache")
        h3.add_credentials('admin', 'admin')

        while not (resp):
            try:
                resp, content = h3.request('http://' + config.controllerIP + '/restconf/operational/opendaylight-inventory:nodes',"GET")
                # print resp
                # print content
                allFlowStats = json.loads(content)
                flowStats = allFlowStats['nodes']['node']
                # time.sleep(1)
                # write port ID, Pkt rx, Pkt tx, bytes rx, bytes tx, drop tx, drop rx

                Count_switches = len(self.switches)
                Bytes_port_status = -1 * np.ones([Count_switches + 1, self.port_count + 1])
                Bytes_port_status_rx = -1 * np.ones([Count_switches + 1, self.port_count + 1])
                Bytes_port_status_tx = -1 * np.ones([Count_switches + 1, self.port_count + 1])
                for fs in flowStats:
                    for f in fs['node-connector']:
                        index, port = self.getIndex(f['id'])
                        if port != -1 and port != 5:
                            Bytes_port_status_rx[index][port] = int(
                                f['opendaylight-port-statistics:flow-capable-node-connector-statistics']['bytes']['received'])
                            Bytes_port_status_tx[index][port] = int(f['opendaylight-port-statistics:flow-capable-node-connector-statistics']['bytes']['transmitted'])
                            Bytes_port_status[index][port] = int(f['opendaylight-port-statistics:flow-capable-node-connector-statistics']['bytes']['received']) + int(f['opendaylight-port-statistics:flow-capable-node-connector-statistics']['bytes'][
                                    'transmitted'])
                return Bytes_port_status.astype(int), Bytes_port_status_rx.astype(int), Bytes_port_status_tx.astype(int)
            except:
                resp = None
            # print allFlowStats

    #######################################################################################################
    # get Port-Status array - packets
    #------------------------------------------------------------------------------------------------------
    def get_Packets_PortStats_Matrix(self):
        h4 = httplib2.Http(".cache")
        h4.add_credentials('admin', 'admin')
        resp, content = h4.request('http://' + config.controllerIP + '/restconf/operational/opendaylight-inventory:nodes',"GET")
        allFlowStats = json.loads(content)
        flowStats = allFlowStats['nodes']['node']
        Count_switches = len(self.switches)
        Packets_port_status = -1 * np.ones([Count_switches + 1, self.port_count +1 ])
        Packets_port_status_tx = -1 * np.ones([Count_switches + 1, self.port_count +1 ])
        Packets_port_status_rx = -1 * np.ones([Count_switches + 1, self.port_count +1 ])
        # write port ID, Pkt rx, Pkt tx, bytes rx, bytes tx, drop tx, drop rx
        for fs in flowStats:
            for f in  fs['node-connector']:
                index, port = self.getIndex(f['id'])
                if port != -1 and port !=5:
                    Packets_port_status_rx[index][port] = int(f['opendaylight-port-statistics:flow-capable-node-connector-statistics']['packets']['received'])
                    Packets_port_status_tx[index][port] = int(f['opendaylight-port-statistics:flow-capable-node-connector-statistics']['packets']['transmitted'])
                    Packets_port_status[index][port] = int(f['opendaylight-port-statistics:flow-capable-node-connector-statistics']['packets']['received'] +
                                                                      f['opendaylight-port-statistics:flow-capable-node-connector-statistics']['packets']['transmitted'])
        return Packets_port_status_rx.astype(int),Packets_port_status_tx.astype(int), Packets_port_status.astype(int)
    #######################################################################################################
    # get rule statistics-for each flow entry in a table query all flow statistics
    #------------------------------------------------------------------------------------------------------
    def get_Bytes_packet_traffic_Matrix(self):
        h2 = httplib2.Http(".cache")
        h2.add_credentials('admin', 'admin')
        resp, content = h2.request('http://' + config.controllerIP + '/restconf/operational/opendaylight-inventory:nodes',"GET")
        allFlowStats = json.loads(content)
        flowStats = allFlowStats['nodes']['node']
        rule_file = open("rules.txt", "a+")
        count_hosts = len(self.hosts)
        byte_traffic_status = np.zeros([17, 17])
        packets_traffic_status = np.zeros([17, 17])
        priority = np.zeros([17, 17])
        for fs in flowStats:
            for aFlow in fs['flow-node-inventory:table']:
                if (aFlow['opendaylight-flow-table-statistics:flow-table-statistics']['active-flows'] != 0 and (fs["id"] in self.edge_switch_list) ):
                    rule_file.write("\nSwitch ID = " + fs["id"] + "\tactive-flows = " + str(aFlow['opendaylight-flow-table-statistics:flow-table-statistics']['active-flows']))
                    for f in aFlow['flow']:
                        try:
                            rule_priority = int(f['priority'])
                            packet_count = int(f['opendaylight-flow-statistics:flow-statistics']['packet-count'])
                            byte_count = int(f['opendaylight-flow-statistics:flow-statistics']['byte-count'])
                            src = str(f['match']['ethernet-match']['ethernet-source']['address'])
                            src_IP = self.getIP_from_Mac(src)
                            traffic_src_ID = int(src_IP.split(".")[3])
                            dst = str(f['match']['ethernet-match']['ethernet-destination']['address'])
                            dst_IP = self.getIP_from_Mac(dst)
                            traffic_dst_ID = int(dst_IP.split(".")[3])
                            byte_traffic_status[traffic_src_ID][traffic_dst_ID] = byte_count
                            packets_traffic_status[traffic_src_ID][traffic_dst_ID] = packet_count
                            priority[traffic_src_ID][traffic_dst_ID] = rule_priority
                            rule_file.write(str(fs["id"]) + "   " + str(packet_count) +"   " + str(byte_count) +"   " + str(src_IP) +"   " + str(dst_IP))
                        except:
                            pass

        rule_file.write(str(byte_traffic_status))
        rule_file.write(str(packets_traffic_status))
        rule_file.write(str(priority))
            # rule_file.write("\t\t")
            # rule_file.write(str(time.time()))
            # rule_file.write("\t")
            # rule_file.write(datetime.datetime.now().strftime("%a, %d %B %Y %I:%M:%S"))
            # rule_file.write("\n")
        rule_file.write("############################################################################\n")
        rule_file.close()
        return byte_traffic_status.astype(int),packets_traffic_status.astype(int), priority.astype(int)
    #######################################################################################################
    #helper function get-packets for two edge nodes
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def get_packet_count(route_ports,port_matching):
       list =[]
       for r in route_ports:
           if (r[0]==port_matching):
               list.append(r)
       return list
    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def get_adjacent_switch_matrix(self):
        # write port ID, Pkt rx, Pkt tx, bytes rx, bytes tx, drop tx, drop rx
        Count_switches = len(self.switches)
        Connection_array = -1 * np.ones([Count_switches + 1, self.port_count+1])
        for s in self.graph.edges:
            if (str(s[0]).find("host") != 0) and (str(s[1]).find("host") != 0):
                x = self.graph.get_edge_data(s[0],s[1])
                y = list(x.items())
                sw_1,port_1 = self.getIndex(y[0][1])
                sw_2,port_2 = self.getIndex(y[1][1])
                Connection_array[sw_1][port_1]=sw_2
                Connection_array[sw_2][port_2]=sw_1
        return Connection_array.astype(int)
    #######################################################################################################
    #
    #------------------------------------------------------------------------------------------------------
    def getLinkStatAdjaencyMatrix(self):
        Count_switches = len(self.switches)
        LinkStatus_Array = -1 * np.ones([Count_switches + 1, Count_switches + 1])
        for s in range(1,Count_switches+1,1):
            for i in range(1,self.port_count+1,1):
                index_switch_colon = int(self.adjacent_switch_matrix[s][i])
                if index_switch_colon != -1:
                    LinkStatus_Array[s][index_switch_colon] =  self.Bytes_port_utilization[s][i]
        return LinkStatus_Array.astype(int)

    def getLinkErrorAdjaencyMatrix(self):
        Count_switches = len(self.switches)
        LinkStatus_Array_error = -1 * np.ones([Count_switches + 1, Count_switches + 1])
        for s in range(1,Count_switches+1,1):
            switch_src = s
            for i in range(1,self.port_count+1,1):
                switch_dst = int(self.adjacent_switch_matrix[s][i])
                switch_src_port = i
                for j in range(1,self.port_count+1,1):
                    if(self.adjacent_switch_matrix[s][j]==switch_dst):
                        switch_dst_port = j
                LinkStatus_Array_error[i][switch_dst]= self.Bytes_port_utilization_tx[s][i] - self.Bytes_port_utilization_rx[switch_dst][switch_dst_port]
        return LinkStatus_Array_error.astype(int)

    def getAdjaencyMatrix(self):
        Count_switches = len(self.switches)
        LinkStatus_Array = np.zeros([Count_switches + 1, Count_switches + 1])
        for s in range(1,Count_switches+1,1):
            for i in range(1,self.port_count+1,1):
                index_switch_colon = int(self.adjacent_switch_matrix[s][i])
                if index_switch_colon != -1:
                    LinkStatus_Array[s][index_switch_colon] = 1
        return LinkStatus_Array.astype(int)

    #######################################################################################################
    # find edge in a rout
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def find_edge(self, headNode, tailNode):
        for edge in self.odlEdges:
            if (edge['source']['source-node'] == headNode) and (edge['destination']['dest-node'] ==tailNode):
                return edge
    #######################################################################################################
    # get hostID from IP address
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def gethostID_from_IP(IP):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if node['host-tracker-service:addresses'][0]['ip'] == IP:
                    return node['node-id']
        return -1
    @staticmethod
    def gethostID_from_Mac(MAC):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if node['host-tracker-service:addresses'][0]['mac'] == MAC:
                    return node['node-id']
        return -1
    #######################################################################################################
    # get Mac from hostID
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def getMac_from_host_ID(hostID):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if  node['node-id'] == hostID:
                    return node['host-tracker-service:addresses'][0]['mac']
        return -1
    #######################################################################################################
    # get IP from hostID
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def getIP_from_host_ID(hostID):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if  node['node-id'] == hostID:
                    return node['host-tracker-service:addresses'][0]['ip']
        return -1
    @staticmethod
    def getIP_from_Mac(Mac):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if  node['host-tracker-service:addresses'][0]['mac'] == Mac:
                    return node['host-tracker-service:addresses'][0]['ip']
        return -1
    @staticmethod
    def getMac_from_IP(IP):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if  node['host-tracker-service:addresses'][0]['ip'] == IP:
                    return node['host-tracker-service:addresses'][0]['mac']
        return -1

    #######################################################################################################
    # get rule statistics-for each flow entry in a table query all flow statistics
    # ------------------------------------------------------------------------------------------------------
    def getRuleState(self,Switch_ID,port_ID):
        h5 = httplib2.Http(".cache")
        h5.add_credentials('admin', 'admin')
        print "sssssssssssssssssssssssssssssssss"
        # print Switch_ID
        # print config.controllerIP
        source = []
        dst = []
        out_port = []
        x = 0
        content = None
        while content == None:
            # print x
            x = x+1
            try:
                resp, content = h5.request('http://' + config.controllerIP + '/restconf/operational/opendaylight-inventory:nodes/node/openflow:'+str(Switch_ID)+'/flow-node-inventory:table/0',"GET")
                # print resp
            except:
                time.sleep(1)

        allFlowStats = json.loads(content)
        # print allFlowStats
        flowStats = allFlowStats['flow-node-inventory:table'][0]['flow']
        # print flowStats
        for fs in flowStats:
            try:
                source.append(fs['match']['ethernet-match']['ethernet-source']['address'])
                dst.append(fs['match']['ethernet-match']['ethernet-destination']['address'])
                out_port.append(fs['instructions']['instruction'][0]['apply-actions']['action'][0]['output-action']['output-node-connector'])
            except:
                pass
        return source,dst,out_port

    def get_edge_Matrix(self):
        Count_switches = len(self.switches)
        edge_Switch_port_array = np.zeros([Count_switches + 1, self.port_count + 1])
        for s in self.graph.edges:
            if (str(s[0]).find("host") == 0) or (str(s[1]).find("host") == 0):
                x = self.graph.get_edge_data(s[0], s[1])
                y =list(x.items())
                if (str(y[0][1]).find("host") == 0):
                    s = self.getIndex(y[1][1])
                    edge_Switch_port_array[s[0]][s[1]] = 1
                else:
                    s = self.getIndex(y[0][1])
                    edge_Switch_port_array[s[0]][s[1]] = 1
        return edge_Switch_port_array
    def Data_file_write(self):
        Portfile = open("/home/haitham/PycharmProjects/QoS/port-utilization-matrix.txt", "w+")
        # linkfile = open("/home/haitham/ODL-python/results/link-utilization-matrix.txt", "w+")
        while 1:
            print ("collectData")
            self.update_Byte_port_utilization()
            byte_port_utilization = self.get_Byte_port_utilization()
            # print byte_port_utilization
            Portfile.write(datetime.datetime.now().strftime("%a, %d %B %Y %I:%M:%S"))
            Portfile.write(str(byte_port_utilization))
            # c.update_Byte_link_utilization()
            # byte_link_utilization = c.get_Byte_link_utilization()
            # linkfile.write(datetime.datetime.now().strftime("%a, %d %B %Y %I:%M:%S"))
            # linkfile.write(str(byte_link_utilization))
            # print "collectData"
