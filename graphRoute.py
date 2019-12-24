# Python program for Dijkstra's
# single source shortest
# path algorithm. The program
# is for adjacency matrix
# representation of the graph

from collections import defaultdict

# Class to represent a graph


class GraphRoute:

    def __init__(self):
        self.route = []
    # A utility function to find the
    # vertex with minimum dist value, from
    # the set of vertices still in queue
    def minDistance(self, dist,hopcount, queue):
        # print dist
        # print hopcount
        # Initialize min value and min_index as -1
        minimum = float("Inf")
        minimum_hop = float("Inf")

        min_hop_index = -1
        min_indicies = []
        # from the dist array,pick one which
        # has min value and is till in queue
        for i in range(len(dist)):
            if dist[i] < minimum and i in queue:
                minimum = dist[i]
        # print minimum

        for index, element in enumerate(dist):
            if minimum == element:  # check if this element is the minimum_value
                min_indicies.append(index)  # add the index to the list if it is

        # print min_indicies

        for i in min_indicies:
            if hopcount[i] < minimum_hop and i in queue:
                minimum_hop = hopcount[i]
                min_hop_index = i
        return min_hop_index

        # print min_hop_index

        # Function to print shortest path

    # from source to j
    # using parent array
    def printPath(self, parent, j):
        # Base Case : If j is source
        if parent[j] == -1:
            # print j,
            self.route.append(j)
            # route.append(j)
            return
        self.printPath(parent, parent[j])
        self.route.append(j)
        # print j,

        # A utility function to print

    # the constructed distance
    # array
    def getSolution(self, dist, parent, src, dst):
        # print("Vertex \t\tDistance from Source\tPath")
        # print dist
        # print("\n%d --> %d \t\t%d \t\t\t\t\t" % (src, dst, dist[dst])),
        self.printPath(parent, dst)
        # print dist
        # print("Vertex \t\tDistance from Source\tPath")
        # for i in range(1, len(dist)):
        #     print("\n%d --> %d \t\t%d \t\t\t\t\t" % (src, i, dist[i])),
        #     self.printPath(parent,i)



    '''Function that implements Dijkstra's single source shortest path 
    algorithm for a graph represented using adjacency matrix 
    representation'''

    def dijkstra(self, graph, src, dst):
        self.route=[]
        row = len(graph)
        col = len(graph[0])
        # The output array. dist[i] will hold
        # the shortest distance from src to i
        # Initialize all distances as INFINITE
        dist = [float("Inf")] * row
        hopcount = [float("Inf")] * row
        # Parent array to store
        # shortest path tree
        parent = [-1] * row
        # Distance of source vertex
        # from itself is always 0
        dist[src] = 0
        hopcount[src] = 0
        # Add all vertices in queue
        queue = []
        for i in range(row):
            queue.append(i)
            # Find shortest path for all vertices
        while queue:
            # print "quee"
            # print queue
            # print parent
            # Pick the minimum dist vertex
            # from the set of vertices
            # still in queue
            u = self.minDistance(dist,hopcount, queue)
            # print "u"
            # print u
            # remove min element
            queue.remove(u)
            # Update dist value and parent
            # index of the adjacent vertices of
            # the picked vertex. Consider only
            # those vertices which are still in
            # queue col is 9
            for i in range(col):
                # print i
                '''Update dist[i] only if it is in queue, there is 
                an edge from u to i, and total weight of path from 
                src to i through u is smaller than current value of 
                dist[i]'''
                if graph[u][i] and i in queue:
                    # print "graph"
                    # print graph[u][i]
                    # print queue
                    # print dist[u]
                    if graph[u][i] < dist[i] and dist[u] < dist[i]:
                        if (dist[u] > graph[u][i]):
                            dist[i] = dist[u]
                        else:
                            dist[i] =  graph[u][i]
                        parent[i] = u
                        hopcount[i] = hopcount[u] + 1
                        # print the constructed distance array
        self.getSolution(dist, parent,src,dst)
        return self.route, dist[dst]


# g = GraphRoute()
# # #
# graphMatrix = [[0, 4, 0, 0, 0, 0, 0, 8, 0],
#          [4, 0, 8, 0, 0, 0, 0, 11, 0],
#          [0, 8, 0, 7, 0, 4, 0, 0, 2],
#          [0, 0, 7, 0, 9, 14, 0, 0, 0],
#          [0, 0, 0, 9, 0, 10, 0, 0, 0],
#          [0, 0, 4, 14, 10, 0, 2, 0, 0],
#          [0, 0, 0, 0, 0, 2, 0, 1, 6],
#          [8, 11, 0, 0, 0, 0, 1, 0, 7],
#          [0, 0, 2, 0, 0, 0, 6, 7, 0]
#          ]
# graphMatrix = [[0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
#  [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
#  [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
#  [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
#  [1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#  [0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#  [0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#  [0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#  [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
#  [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
#  [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#  [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
#  [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
#  [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
#  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0],
#  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0],
#  [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
#  [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
#  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0],
#  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0]]
#
# [[0, 4, 0, 0, 0, 0, 0, 8, 0],
#          [4, 0, 8, 0, 0, 0, 0, 11, 0],
#          [0, 8, 0, 7, 0, 4, 0, 0, 2],
#          [0, 0, 7, 0, 9, 14, 0, 0, 0],
#          [0, 0, 0, 9, 0, 10, 0, 0, 0],
#          [0, 0, 4, 14, 10, 0, 2, 0, 0],
#          [0, 0, 0, 0, 0, 2, 0, 1, 6],
#          [8, 11, 0, 0, 0, 0, 1, 0, 7],
#          [0, 0, 2, 0, 0, 0, 6, 7, 0]
#          ]

# Print the solution src & dst
# print g.dijkstra(graphMatrix, 2,6)
# print "dddddddd"
# print x