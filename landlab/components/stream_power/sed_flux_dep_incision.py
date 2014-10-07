import numpy as np
from landlab import ModelParameterDictionary

from landlab.core.model_parameter_dictionary import MissingKeyError
from landlab.field.scalar_data_fields import MissingKeyError

from landlab.components.stream_power.stream_power import StreamPowerEroder

class SedDepEroder(object):
    """
    This class implements sediment flux dependent fluvial incision. It is built
    on the back of the simpler stream power class, stream_power.py, also in this
    component, and follows its limitations - we require single flow directions,
    provided to the class. See the docstrings of stream_power.py for more detail
    on required initialization and operating parameters.
    """
    
    def __init__(self, grid, params):
        self.initialize(grid, params)
        
    def initialize(self, grid, params_file):
        """
        This module implements sediment flux dependent channel incision following:
            
        E = f(Qs, Qc) * stream_power - sp_crit,
        
        where stream_power is the stream power (often ==K*A**m*S**n) provided by the
        stream_power.py component. Note that under this incision paradigm, sp_crit
        is assumed to be controlled exclusively by sediment mobility, i.e., it is
        not a function of bedrock resistance. If you want it to represent a bedrock
        resistance term, be sure to set Dchar if you use the MPM transport capacity
        relation, and do not use the flag 'slope_sensitive_threshold'.
        
        This calculation has a tendency to be slow, and can easily result in 
        numerical instabilities. These instabilities are suppressed by retaining a
        memory of what the sediment flux was in the last time step, and weighting
        the next timestep by that value. XXXmore detail needed. Possibilities:
            1. weight by last timestep/2timesteps (what about early ones?)
            2. do it iteratively; only do incision one the sed flux you are using
            stabilises (so the previous iter "seed" becomes less important)
        
        Parameters needed in the initialization file follow those for 
        stream_power.py. However, we now require additional input terms for the
        f(Qs,Qc) term:
        REQUIRED:
            sed_dependency_type -> 'None', 'linear_decline', 'parabolic', 
            'almost_parabolic', 'generalized_humped'. For definitions, see Gasparini
            et al., 2006; Hobley et al., 2011.
            Qc -> This input controls the sediment capacity used by the component.
            It can either calculate sediment carrying capacity for itself if this
            parameter is a string 'MPM', which will cause the component to use a
            slightly modified version of the Meyer-Peter Muller equation (again, see
            Hobley et al., 2011). Alternatively, it can be another string denoting
            the grid field name in which a precalculated capacity is stored.
        Depending on which options are specified above, further parameters may be
        required:
            If sed_dependency_type=='generalized_humped', need the shape parameters
            used by Hobley et al:
                kappa_hump
                nu_hump
                phi_hump
                c_hump
                Note the onus is on the user to ensure that these parameters result
                in a viable shape, i.e., one where the maximum is 1 and there is
                indeed a hump in the profile. If these parameters are NOT specified,
                they will default to the form of the curve for Leh valley as found
                in Hobley et al 2011: nu=1.13; phi=4.24; c=0.00181; kappa=13.683.
                
            If Qc=='MPM', these parameters may optionally be provided:
                Dchar -> characteristic grain size (i.e., D50) on the bed, in m.
                C_MPM -> the prefactor in the MPM relation. Defaults to 1, as in the
                    relation sensu stricto, but can be modified to "tune" the 
                    equations to a known point 
                
            ...if Dchar is NOT provided, the component will attempt to set (and will
            report) an appropriate characteristic grain size, such that it is
            consistent both with the threshold provided *and* a critical Shields
            number of 0.06. (If you really, really want to, you can override this
            critical Shields number too; use parameter 'critical_Shields').
        
        OPTIONAL:
            rock_density -> in kg/m3 (defaults to 2700)
            sediment_density -> in kg/m3 (defaults to 2700)
            fluid_density -> in most cases water density, in kg/m3 (defaults to 1000)
            g -> acceleration due to gravity, in m/s^2 (defaults to 9.81)
            
            slope_sensitive_threshold -> a boolean, defaults to FALSE.
                In steep mountain environments, the critical Shields number for particle
            motion appears to be weakly sensitive to the local slope, as 
            taustar_c=0.15*S**0.25 (Lamb et al, 2008). If this flag is set to TRUE,
            the critical threshold in the landscape is allowed to become slope 
            sensitive as well, in order to be consistent with this equation.
            This modification was used by Hobley et al., 2011.
            
            set_threshold_from_Dchar -> a boolean, defaults to FALSE.
                Use this flag to force an appropriate threshold value from a
            provided Dchar. i.e., this is the inverse of the procedure that is
            used to find Dchar if it isn't provided. No threshold can be
            specified in the parameter file, and Dchar must be specified.
        """
        
        inputs = ModelParameterDictionary(params_file)
        #create a initialization of stream power, which will provide the stream power value to modify:
        self.simple_sp = StreamPowerEroder(grid, params_file)
        self.simple_sp.no_erode = True #suppress the ability of the module to do any erosion
        self.threshold = self.simple_sp.sp_crit
        #set gravity
        try:
            self.g = inputs.read_float('g')
        except MissingKeyError:
            self.g = 9.81
        try:
            self.rock_density = inputs.read_float('rock_density')
        except MissingKeyError:
            self.rock_density = 2700
        try:
            self.sed_density = inputs.read_float('sediment_density')
        except MissingKeyError:
            self.sed_density = 2700
        try:
            self.fluid_density = inputs.read_float('fluid_density')
        except MissingKeyError:
            self.fluid_density = 1000
        self.type = inputs.read_string('sed_dependency_type')
        try:
            self.Qc = inputs.read_string('Qc')
        except MissingKeyError:
            self.Qc = None
        else:
            if self.Qc=='MPM':
                self.MPM_flag = True
            else:
                self.MPM_flag = False
        try:
            override_threshold = inputs.read_bool('set_threshold_from_Dchar')
        except MissingKeyError:
            override_threshold = False
        try:
            shields = inputs.read_float('critical_Shields')
        except MissingKeyError:
            shields = 0.06
            
        #now conditional inputs
        if self.type == 'generalized_humped':
            try:
                self.kappa = inputs.read_float('kappa_hump')
                self.nu = inputs.read_float('nu_hump')
                self.phi = inputs.read_float('phi_hump')
                self.c = inputs.read_float('c_hump')
            except MissingKeyError:
                self.kappa = 13.683
                self.nu = 1.13
                self.phi = 4.24
                self.c = 0.00181
                print 'Adopting inbuilt parameters for the humped function form...'
        
        if self.Qc == 'MPM':
            try:
                self.Dchar = inputs.read_float('Dchar')
            except MissingKeyError:
                assert self.threshold > 0., "Can't automatically set characteristic grain size if threshold is 0 or unset!"
                self.Dchar = self.threshold/self.g/(self.sed_density-self.fluid_density)/shields
                print 'Setting characteristic grain size from the Shields criterion...'
                print 'Characteristic grain size is: ', self.Dchar
            try:
                self.C_MPM = inputs.read_float('C_MPM')
            except MissingKeyError:
                self.C_MPM = 1.
        
        if override_threshold:
            assert self.simple_sp.set_threshold==False, 'Threshold cannot be manually set if you wish it to be generated from Dchar!'
            try:
                self.threshold = shields*self.g*(self.sed_density-self.fluid_density)*self.Dchar
            except AttributeError:
                self.threshold = shields*self.g*(self.sed_density-self.fluid_density)*inputs.read_float('Dchar')
            self.simple_sp.sp_crit = self.threshold
        
        try:
            self.S_sensitive_thresh = inputs.read_bool('slope_sensitive_threshold')
            #this is going to be a nightmare to implement...
        except:
            self.S_sensitive_thresh = False
        
        ###No, we won't do this. ID the first step with try: self.past_sed_flux; except AttributeError: ...
        ##self.past_sed_flux = np.empty(grid.number_of_nodes) #this is where we're going to store the previous sed flux...
        ##self.first_iter = True #this will let us identify the "startup" condition, which we need to allow to become stable...
        
    def erode(self, grid, dt, node_drainage_areas='planet_surface__drainage_area', slopes_at_nodes=None, link_slopes=None, link_node_mapping='links_to_flow_reciever', slopes_from_elevs=None, W_if_used=None, Q_if_used=None, io=None):
        """
        """
        #get the stream power part of the equation from the simple module:
        _,_,simple_stream_power = self.simple_sp.erode(grid, dt, node_drainage_areas, slopes_at_nodes, link_slopes, link_node_mapping, slopes_from_elevs, W_if_used, Q_if_used, io)
        