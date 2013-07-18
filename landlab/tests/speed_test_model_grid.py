"""
simple script to run speed tests of various functions in model grid
"""

from landlab import model_grid
import time
import numpy

mg = model_grid.RasterModelGrid(20, 30, 1.0)

nt = 1000

s = mg.create_node_dvector()
g = mg.create_active_link_dvector()
divg = mg.create_node_dvector()

start_time = time.time()

for i in range(nt):
    
    g = mg.calculate_gradients_at_active_links(s, g)
    
time1 = time.time()

for i in range(nt):
    
    g = mg.calculate_gradients_at_active_links_slow(s, g)
    
time2 = time.time()

for i in range(nt):
    
    divg = mg.calculate_flux_divergence_at_nodes(g, divg)
    
time3 = time.time()

for i in range(nt):
    
    divg = mg.calculate_flux_divergence_at_nodes_slow(g, divg)

time4 = time.time()
  
for i in range(nt):
    
    divg = mg.calculate_flux_divergence_at_active_cells(g)
    
time5 = time.time()

for i in range(nt):
    
    divg = mg.calculate_flux_divergence_at_active_cells_slow(g)

time6 = time.time()
  
print('Elapsed time with fast gradient algo: '+str(time1-start_time))
print('Elapsed time with slow gradient algo: '+str(time2-time1))
print('Elapsed time with fast node-divergence algo: '+str(time3-time2))
print('Elapsed time with slow node-divergence algo: '+str(time4-time3))
print('Elapsed time with fast activecell-divergence algo: '+str(time5-time4))
print('Elapsed time with slow activecell-divergence algo: '+str(time6-time5))

   