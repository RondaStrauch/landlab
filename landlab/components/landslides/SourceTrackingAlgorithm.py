
"""
26 Jan 2016 - SN & EI
Authors: Sai Nudurupati & Erkan Istanbulluoglu
HSD: Hydrologic Source Domain; MD: Model Domain

This algorithm is a customized variant of flow-accumulation algorithm.
This algorithm uses brute force method (will visit each MD node, sometimes
multiple times) to calculate all unique upstream contributing HSD nodes and
their fractions of contribution.
"""

# %%
# Import required libraries
import numpy as np
import copy
from collections import Counter

# %%
"""
 Convert Arc flow_directions file to be represented in node ids
 gives receiver of each node starting at right and going clockwise.
"""


def convert_arc_flow_directions_to_landlab_node_ids(grid, flow_dir_arc):
    r_arc_raw = np.log2(flow_dir_arc)
    r_arc_raw = r_arc_raw.astype('int')
    neigh_ = grid.neighbors_at_node
    diag_ = grid.diagonals_at_node
    neigh_ = np.fliplr(neigh_)
    diag_ = np.fliplr(diag_)
    a_n = np.hsplit(neigh_, 4)
    a_d = np.hsplit(diag_, 4)
    neighbors = np.hstack((a_n[-1], a_d[0], a_n[0], a_d[1], a_n[1], a_d[2],
                           a_n[2], a_d[3]))
    # Now neighbors has node ids of neighboring nodes in cw order starting at
    # right, hence the order of neighbors = [r, br, b, bl, l, tl, t, tr]
    r = np.zeros(grid.number_of_nodes, dtype=int)
    r[grid.core_nodes] = np.choose(r_arc_raw[grid.core_nodes],
                                   np.transpose(neighbors[grid.core_nodes]))
    return (r)


# %%
# Source Routing Algorithm
# Note 1: This algorithm works on core nodes only because core nodes
# have neighbors that are real values and not -1s.
# Note 2: Nodes in the following comments in this section refer to core nodes.
def track_source(grid, r, hsd_ids):
    z = grid.at_node['topographic__elevation']
    core_nodes = grid.core_nodes
    core_elev = z[core_nodes]
    # Sort all nodes in the descending order of elevation
    sor_z = core_nodes[np.argsort(core_elev)[::-1]]
    # Create a list to record all nodes that have been visited
    # To store nodes that have already been counted
    alr_counted = []
    flow_accum = np.zeros(grid.number_of_nodes, dtype=int)
    hsd_upstr = {}
    # Loop through all nodes
    for i in sor_z:
        # Check 1: Check if this node has been visited earlier. If yes,
        # then skip to next node
        if i in alr_counted:
            continue
        # Check 2: If the visited node is a sink
        if r[i] == i:
            hsd_upstr.update({i: [hsd_ids[i]]})
            flow_accum[i] += 1.
            alr_counted.append(i)
            continue
        # Check 3: Now, if the node is not a sink and hasn't been visited, it
        # belongs to a stream segment. Hence, all the nodes in the stream will
        # have to betraversed.
        # stream_buffer is a list that will hold the upstream contributing
        # node information for that particular segment until reaching outlet.
        stream_buffer = []
        j = i
        switch_i = True
        a = 0.
        # Loop below will traverse the segment of the stream until an outlet
        # is reached.
        while True:
            # Following if loop is to execute the contents once the first node
            # in the segment is visited.
            if not switch_i:
                j = r[j]
                if j not in core_nodes:
                    break
            # If this node is being visited for the first time,
            # this 'if statement' will executed.
            if flow_accum[j] == 0.:
                a += 1.
                alr_counted.append(j)
                stream_buffer.append(hsd_ids[j])
            # Update number of upstream nodes.
            flow_accum[j] += a
            # If the node is being visited for the first time, the dictionary
            # 'hsd_upstr' will be updated.
            if j in hsd_upstr.keys():
                hsd_upstr[j] += copy.copy(stream_buffer)
            # If the node has been already visited, then the upstream segment
            # that was not accounted for in the main stem, would be added to
            # all downstream nodes, one by one, until the outlet is reached.
            else:
                hsd_upstr.update({j: copy.copy(stream_buffer)})
            # If the outlet is reached, the 'while' loop will be exited.
            if r[j] == j:
                break
            # This will be executed only for the first node of the
            # stream segment.
            if switch_i:
                switch_i = False
    return (hsd_upstr, flow_accum)


# %%
# Algorithm to calculate coefficients of each upstream HSD ID
def find_unique_upstream_hsd_ids_and_fractions(hsd_upstr):
    uniq_ids = {}  # Holds unique upstream HSD ids
    C = {}  # Holds corresponding total numbers
    coeff = {}  # Holds corresponding coefficients of contribution
    for ke in hsd_upstr.keys():
        cnt = Counter()
        for num in hsd_upstr[ke]:
            cnt[num] += 1
        uniq_ids.update({ke: cnt.keys()})
        buf = []
        for k in cnt.keys():
            buf.append(cnt[k])
        C.update({ke: buf})
        e = [s/float(sum(buf)) for s in buf]
        coeff.update({ke: e})
    return (uniq_ids, coeff)