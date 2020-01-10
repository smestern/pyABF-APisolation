
import matplotlib.pyplot as plt
import numpy as np
from numpy import genfromtxt
import pyabf
import tkinter as tk
from tkinter import filedialog
import os
import pandas as pd
import pyAPisolation as apis
from sklearn.ensemble import IsolationForest
from ipfx import feature_extractor
root = tk.Tk()
root.withdraw()
files = filedialog.askopenfilenames(filetypes=(('ABF Files', '*.abf'),
                                   ('All files', '*.*')),
                                   title='Select Input File'
                                   )
fileList = root.tk.splitlist(files)

##Declare our options at default
filter = input("Filter (recommended to be set to 0): ")
braw = False
bfeat = True
try: 
    filter = int(filter)
except:
    filter = 0
tag = input("tag to apply output to files: ")
try: 
    tag = str(tag)
except:
    tag = ""

feat = input("save feature arrays for each file? (y/n): ")
try: 
    feat = str(feat)
except:
    feat = "n"
if feat == "n" or feat =="N":
    bfeat = False
else: 
    bfeat = True

featcon = input("save feature arrays all-in-one file? (y/n): ")
try: 
    feat = str(featcon)
except:
    feat = "n"
if feat == "n" or feat =="N":
    bfeatcon = False
else: 
    bfeatcon = True
    bfeat = False


if bfeatcon == True:
    featfile = input("save feature arrays all-in-one file averaging per input file? (y/n): ")
    try: 
        featfile = str(featfile)
    except:
        featfile = "n"
    if featfile == "n" or featfile =="N":
        featfile = False
    else: 
        featfile = True

    featrheo = input("save feature arrays all-in-one file rheobase only? (y/n): ")
    try: 
        featrheo = str(featrheo)
    except:
        featrheo = "n"
    if featrheo == "n" or featrheo =="N":
        featrheo = False
    else: 
        featrheo = True


    boutlier = input("Perform Outlier Elim? (y/n): ")
    try: 
        boutlier = str(boutlier)
    except:
        boutlier = "n"
    if boutlier == "n" or boutlier =="N":
        boutlier = False
    else: 
        boutlier = True
        


debugplot = 0

dfs = pd.DataFrame()
df_spike_count = pd.DataFrame()
for filename in fileList:
    if filename.endswith(".abf"):
        file_path = filename
        abf = pyabf.ABF(file_path)
        
        if abf.sweepLabelY != 'Clamp Current (pA)':
            print(filename + ' import')
            np.nan_to_num(abf.data, nan=-9999, copy=False)
             #If there is more than one sweep, we need to ensure we dont iterate out of range
            if abf.sweepCount > 1:
                sweepcount = (abf.sweepCount)
            else:
                sweepcount = 1
            df = pd.DataFrame()
            #Now we walk through the sweeps looking for action potentials
            temp_spike_df = pd.DataFrame()
            temp_spike_df['a_filename'] = [abf.abfID]
            for sweepNumber in range(0, sweepcount): 
                
                spikext = feature_extractor.SpikeFeatureExtractor(filter=0, dv_cutoff=15)
                spiketxt = feature_extractor.SpikeTrainFeatureExtractor(start=0.55, end=1.6)
                abf.setSweep(sweepNumber)
                dataT, dataV, dataI = abf.sweepX, abf.sweepY, abf.sweepC
                spike_in_sweep = spikext.process(dataT, dataV, dataI)
                spike_train = spiketxt.process(dataT, dataV, dataI, spike_in_sweep)
                spike_count = spike_in_sweep.shape[0]
                temp_spike_df["Sweep " + str(sweepNumber +1) + " spike count"] = [spike_count]
                temp_spike_df["Current_Sweep " + str(sweepNumber +1)+ " current injection"] = [dataI[20613]]
                
                if spike_count > 0:
                    temp_spike_df["isi_Sweep " + str(sweepNumber +1)+ " isi"] = [spike_train['first_isi']]
                    spike_train_df = pd.DataFrame(spike_train, index=[0])
                    nan_series = pd.DataFrame(np.full(abs(spike_count-1), np.nan))
                    #spike_train_df = spike_train_df.append(nan_series)
                    spike_in_sweep['spike count'] = np.hstack((spike_count, np.full(abs(spike_count-1), np.nan)))
                    spike_in_sweep['sweep Number'] = np.hstack(((sweepNumber+1), np.full(abs(spike_count-1), np.nan)))
                    spike_in_sweep = spike_in_sweep.join(spike_train_df)
                    print("Processed Sweep " + str(sweepNumber+1) + " with " + str(spike_count) + " aps")
                    df = df.append(spike_in_sweep, ignore_index=True, sort=True)
                else:
                    temp_spike_df["isi_Sweep " + str(sweepNumber +1)+ " isi"] = [np.nan]
            df = df.assign(file_name=np.full(len(df.index),abf.abfID))
            temp_spike_df["rheobase_current"] = [df['peak_i'].to_numpy()[0]]
            temp_spike_df["rheobase_latency"] = [df['latency'].to_numpy()[0]]
            temp_spike_df["rheobase_thres"] = [df['threshold_v'].to_numpy()[0]]
            temp_spike_df["rheobase_width"] = [df['width'].to_numpy()[0]]
            temp_spike_df["rheobase_heightPT"] = [abs(df['peak_v'].to_numpy()[0] - df['fast_trough_v'].to_numpy()[0])]
            temp_spike_df["rheobase_heightTP"] = [abs(df['threshold_v'].to_numpy()[0] - df['peak_v'].to_numpy()[0])]
            temp_spike_df["rheobase_upstroke"] = [df['upstroke'].to_numpy()[0]]
            temp_spike_df["rheobase_downstroke"] = [df['upstroke'].to_numpy()[0]]
            temp_spike_df["rheobase_fast_trough"] = [df['fast_trough_v'].to_numpy()[0]]
            temp_spike_df["mean_current"] = [np.mean(df['peak_i'].to_numpy())]
            temp_spike_df["mean_latency"] = [np.mean(df['latency'].to_numpy())]
            temp_spike_df["mean_thres"] = [np.mean(df['threshold_v'].to_numpy())]
            temp_spike_df["mean_width"] = [np.mean(df['width'].to_numpy())]
            temp_spike_df["mean_heightPT"] = [np.mean(abs(df['peak_v'].to_numpy() - df['fast_trough_v'].to_numpy()))]
            temp_spike_df["mean_heightTP"] = [np.mean(abs(df['threshold_v'].to_numpy() - df['peak_v'].to_numpy()))]
            temp_spike_df["mean_upstroke"] = [np.mean(df['upstroke'].to_numpy())]
            temp_spike_df["mean_downstroke"] = [np.mean(df['upstroke'].to_numpy())]
            temp_spike_df["mean_fast_trough"] = [np.mean(df['fast_trough_v'].to_numpy())]
            cols = df.columns.tolist()
            cols = cols[-1:] + cols[:-1]
            df = df[cols]
            df = df[cols]
            if bfeatcon == True:
               df_spike_count = df_spike_count.append(temp_spike_df, sort=True)
               dfs = dfs.append(df, sort=True)
        else:
            print('Not Current CLamp')
   
if boutlier == True:
    od = IsolationForest(contamination=0.01)
    d_out = dfs.iloc[:,2:].to_numpy()
    d_out = np.nan_to_num(d_out, False, 0.0)
    f_outliers = od.fit_predict(d_out)
    drop_o = np.nonzero(np.where(f_outliers==-1, 1, 0))[0]         

    outliers = dfs.iloc[drop_o].copy(deep=True)
    dfs = dfs.drop(dfs.index[drop_o], axis=0)
    outliers.to_csv('output/outliers_' + tag + '.csv')

if featfile == True:
    ids = dfs['file_name'].unique()
    


    tempframe = dfs.groupby('file_name').mean().reset_index()
    tempframe.to_csv('output/allAVG' + tag + '.csv')

if featrheo == True:
    tempframe = dfs.drop_duplicates(subset='file_name')
    tempframe.to_csv('output/allRheo' + tag + '.csv')

        




if bfeatcon == True:
    df_spike_count.to_csv('output/spike_count_' + tag + '.csv')
    dfs.to_csv('output/allfeat' + tag + '.csv')
    



plt.show()