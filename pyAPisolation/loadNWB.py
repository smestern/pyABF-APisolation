import numpy as np
from .loadABF import loadABF
try:
    import h5py
    ##Does not import when using python-matlab interface on windows machines
except:
    print("h5py import fail")
import pandas as pd

def loadFile(file_path, return_obj=False, old=False):
    """Loads the nwb object and returns three arrays dataX, dataY, dataC and optionally the object.
    same input / output as loadABF for easy pipeline inclusion

    Args:
        file_path (str): [description]
        return_obj (bool, optional): return the NWB object to access various properites. Defaults to False.
        old (bool, optional): use the old indexing method, uneeded in most cases. Defaults to False.

    Returns:
        dataX: time (should be seconds)
        dataY: voltage (should be mV)
        dataC: current (should be pA)
        dt: time step (should be seconds)
    """    
    if file_path.endswith(".nwb"):
        return loadNWB(file_path, return_obj, old)
    elif file_path.endswith(".abf"):
        return loadABF(file_path, return_obj)
    else:
        raise Exception("File type not supported")



def loadNWB(file_path, return_obj=False, old=False):
    """Loads the nwb object and returns three arrays dataX, dataY, dataC and optionally the object.
    same input / output as loadABF for easy pipeline inclusion

    Args:
        file_path (str): [description]
        return_obj (bool, optional): return the NWB object to access various properites. Defaults to False.
        old (bool, optional): use the old indexing method, uneeded in most cases. Defaults to False.

    Returns:
        dataX: time (should be seconds)
        dataY: voltage (should be mV)
        dataC: current (should be pA)
        dt: time step (should be seconds)
    """    
   
    if old:
        nwb = old_nwbFile(file_path)
    else:
        nwb = nwbFile(file_path)
    
    fs_dict = nwb.rate # sampling rate info
    fs = fs_dict["rate"] # assumes units of Hz
    dt = np.reciprocal(fs) # seconds
    
    if isinstance(nwb.dataX, np.ndarray)==False:
        dataX = np.asarray(nwb.dataX, dtype=np.dtype('O')) ##Assumes if they are still lists its due to uneven size
        dataY = np.asarray(nwb.dataY, dtype=np.dtype('O')) #Casts them as numpy object types to deal with this
        dataC = np.asarray(nwb.dataC, dtype=np.dtype('O'))
    else:
        dataX = nwb.dataX #If they are numpy arrays just pass them
        dataY = nwb.dataY
        dataC = nwb.dataC

    if return_obj == True:
        return dataX, dataY, dataC, dt, nwb
    else:
        return dataX, dataY, dataC, dt

    ##Final return incase if statement fails somehow
    return dataX, dataY, dataC, dt



# A simple class to load the nwb data quick and easy
##Call like nwb = nwbfile('test.nwb')
##Sweep data is then located at nwb.dataX, nwb.dataY, nwb.dataC (for stim)
class old_nwbFile(object):

    def __init__(self, file_path):
        with h5py.File(file_path,  "r") as f:
            ##Load some general properities
            sweeps = list(f['acquisition'].keys()) ##Sweeps are stored as keys
            self.sweepCount = len(sweeps)
            self.rate = dict(f['acquisition'][sweeps[0]]['starting_time'].attrs.items())
            self.sweepYVars = dict(f['acquisition'][sweeps[0]]['data'].attrs.items())
            self.sweepCVars = dict(f['stimulus']['presentation'][sweeps[0]]['data'].attrs.items())
            ##Load the response and stim
            data_space_s = 1/self.rate['rate']
            dataY = []
            dataX = []
            dataC = []
            for sweep in sweeps:
                ##Load the response and stim
                data_space_s = 1/(dict(f['acquisition'][sweeps[0]]['starting_time'].attrs.items())['rate'])
                temp_dataY = np.asarray(f['acquisition'][sweep]['data'][()])
                temp_dataX = np.cumsum(np.hstack((0, np.full(temp_dataY.shape[0]-1,data_space_s))))
                temp_dataC = np.asarray(f['stimulus']['presentation'][sweep]['data'][()])
                dataY.append(temp_dataY)
                dataX.append(temp_dataX)
                dataC.append(temp_dataC)
            try:
                ##Try to vstack assuming all sweeps are same length
                self.dataX = np.vstack(dataX)
                self.dataC = np.vstack(dataC)
                self.dataY = np.vstack(dataY)
            except:
                #Just leave as lists
                self.dataX = dataX
                self.dataC = dataC
                self.dataY = dataY
        return




class nwbFile(object):

    def __init__(self, file_path):
        with h5py.File(file_path,  "r") as f:
            ##Load some general properities
            acq_keys = list(f['acquisition'].keys())
            stim_keys = list(f['stimulus']['presentation'].keys())
            sweeps = zip(acq_keys, stim_keys)##Sweeps are stored as keys
            self.sweepCount = len(acq_keys)
            self.rate = dict(f['acquisition'][acq_keys[0]]['starting_time'].attrs.items())
            self.sweepYVars = dict(f['acquisition'][acq_keys[-1]]['data'].attrs.items())
            try:
                self.sweepCVars = dict(f['stimulus']['presentation'][stim_keys[-1]]['data'].attrs.items())
            except:
                self.sweepCVars = None
            #self.temp = f['general']['Temperature'][()]
            ## Find the index's with long square
            index_to_use = []
            for key_resp, key_stim in sweeps: 
                sweep_dict = dict(f['acquisition'][key_resp].attrs.items())
                
                if check_stimulus(sweep_dict['stimulus_description']) or check_stimulus(sweep_dict['description']):
                    index_to_use.append((key_resp, key_stim)) 

            
            dataY = []
            dataX = []
            dataC = []
            self.sweepMetadata = []
            for sweep_resp, sweep_stim in index_to_use:
                ##Load the response and stim
                data_space_s = 1/(dict(f['acquisition'][sweep_resp]['starting_time'].attrs.items())['rate'])
                try:
                    bias_current = f['acquisition'][sweep_resp]['bias_current'][()]
                    if np.isnan(bias_current):
                        #continue
                        bias_current = 0
                except:
                    bias_current = 0
                temp_dataY = np.asarray(f['acquisition'][sweep_resp]['data'][()]) * dict(f['acquisition'][sweep_resp]['data'].attrs.items())['conversion'] 
                temp_dataX = np.cumsum(np.hstack((0, np.full(temp_dataY.shape[0]-1,data_space_s))))
                temp_dataC = np.asarray(f['stimulus']['presentation'][sweep_stim]['data'][()]) * dict(f['stimulus']['presentation'][sweep_stim]['data'].attrs.items())['conversion']
                dataY.append(temp_dataY)
                dataX.append(temp_dataX)
                dataC.append(temp_dataC)
                sweep_dict_resp = dict(f['acquisition'][sweep_resp].attrs.items())
                sweep_dict_resp.update(dict(f['acquisition'][sweep_resp]['data'].attrs.items()))
                sweep_dict_stim = dict(f['stimulus']['presentation'][sweep_stim].attrs.items())
                sweep_dict_stim.update(dict(f['stimulus']['presentation'][sweep_stim]['data'].attrs.items()))
                self.sweepMetadata.append(dict(resp_dict = sweep_dict_resp, stim_dict=sweep_dict_stim))
            try:
                ##Try to vstack assuming all sweeps are same length
                self.dataX = np.vstack(dataX)
                self.dataC = np.vstack(dataC)
                self.dataY = np.vstack(dataY)
            except:
                #Just leave as lists
                self.dataX = dataX
                self.dataC = dataC
                self.dataY = dataY
        return

class stim_names:
    stim_inc = ['long', '1000']
    stim_exc = ['rheo', 'Rf50_']
    def __init__(self):
        self.stim_inc = stim_names.stim_inc
        self.stim_exc = stim_names.stim_exc
        return

GLOBAL_STIM_NAMES = stim_names()
def check_stimulus(stim_desc):
    try:
        stim_desc_str = stim_desc.decode()
    except:
        stim_desc_str = stim_desc
    #print(stim_desc_str)
    include_s = np.any([x.upper() in stim_desc_str.upper() for x in GLOBAL_STIM_NAMES.stim_inc])
    exclude_s = np.invert(np.any([x.upper() in stim_desc_str.upper() for x in GLOBAL_STIM_NAMES.stim_exc]))
    return np.logical_and(include_s, exclude_s)