

import numpy as np
from numpy import genfromtxt
import scipy.linalg
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from abfderivative import *
from nuactionpotential import *
import pyabf
from pyabf.tools import *
from matplotlib import cm
import tkinter as tk
from tkinter import filedialog
import os
import pandas


directory = 'Processed/'

i = 0
k = 0
for filename in os.listdir(directory):
    if filename.endswith(".abf"):
        i += 1
        file_path = directory + filename
        abf = pyabf.ABF(file_path)
        if abf.sweepLabelY != 'Clamp Current (pA)':
            print(filename + ' import')
            np.nan_to_num(abf.data, nan=-9999, copy=False)
            tag = file_path.split('/')
            tag = tag[(len(tag) - 1)]
            #fileno, void = tag.split('-')
            thresholdavg(abf,0)
            _, df, _ = apisolate(abf, 0, "", False, True, plot=8)
        else: 
            k += 1
            print('current wrong')
                     
print(i)
print(k)
plt.show()