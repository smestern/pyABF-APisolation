import numpy as np
import pandas as pd
import os
import glob
import sys
import anndata as ad
import logging
from ..patch_utils import df_select_by_col
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


DEFAULT_META_COLS = ['cell_type', 'time', 'cell_id', 'protocol', 'primary', 'filename', 'foldername', 'depolarizing_current', 'IC1_protocol_check', 'sample_rate']
DEFAULT_FEAT_COLS = ['']

class experimentalStructure:
    """
    A class to represent the experimental structure of a time series database. Each entry represents a protocol,
    and each protcol has a set of flags, (e.g. time, cell type, etc.).
    One flag is the primairy flag, which is used to flag the protocool the represents the primary time series (for computing features etc).
    """
    def __init__(self):
        """
        Constructor for the experimentalStructure class
        :param path: Path to the database
        :param exp: Experimental structure of the database
        """
        self.protocols = []
        self.primary = None
        self.flags = {}

    def addProtocol(self, name, flags):
        """
        Add a protocol to the experimental structure
        :param name: Name of the protocol
        :param flags: Flags of the protocol
        """
        self.protocols.append(name)
        for flag in flags:
            if flag not in self.flags:
                self.flags[flag] = []
            self.flags[flag].append(flags[flag])
    
    def setPrimary(self, name):
        """
        Set the primary protocol
        :param name: Name of the primary protocol
        """
        self.primary = name


class tsDatabase:
    """
        A class to represent a time series database. Overall this class will a database style of indexing of files.
        The user will provide a experimental structure, and the class will provide a simple interface to load the data. 
        Each DB entry will be a single cell, it will have metadata describing the cell, and linking the different files to the cell.
        It will also have a table of features, and a table of time series data (hot-loaded from the files).
        
    """
    ## internally this looks something like
    ## Subject | Protocol 1 | Protocol 2 | ... | Protocol N | Metadata | Features | Time Series
    ## 1       | file1      | file2      | ... | fileN      | meta1    | feat1    | ts1
    ## 2       | file1      | file2      | ... | fileN      | meta2    | feat2    | ts2
    ## ...     | ...        | ...        | ... | ...        | ...      | ...      | ...
    #internally we will use annData to store the data, externally we use a excel sheet to store the metadata and features. This is not ideal but end users want to be able to edit the metadata and features in excel.
    #we could use a sqlite database to store the metadata and features, but this would require a lot of extra code to handle the database, for now we will use this simple solution.


    def __init__(self, path=None, exp=None, dataframe = None, **kwargs):
        """
        Constructor for the tsDatabase class
        :param path: Path to the database
        :param exp: Experimental structure of the database
        """
        self.data = ad.AnnData()
        if path is None:
            self.path = os.getcwd()
        else:
            self.path = path

        if exp is None:
            self.exp = experimentalStructure()
        else:
            self.exp = exp

        #if a dataframe is passed in here, we will use it to populate the database
        if dataframe is not None:
            self.dataframe = dataframe
            self.fromDataFrame(dataframe, self=self, **kwargs)


    def load(self, path):
        """
        Load the database from a path
        :param path: Path to the database
        """
        pass

    @classmethod
    def fromDataFrame(cls, dataframe, **kwargs):
        """
        Load the database from a dataframe
        :param dataframe: Dataframe to load from
        """
        #if self is in kwargs, we will load the data into that object, otherwise we will create a new object
        if 'self' in kwargs:
            logger.info('Loading data into existing object')
            self = kwargs.pop('self')
            #self = kwargs['self']
        else:
            logger.info('Creating new object')
            self = cls()
        
        data_obj = self.parseDataFrame(dataframe, **kwargs)

        #this will be our primary data object

        self.data = data_obj
        self.exp.addProtocol(data_obj.obs['protocol'][0], data_obj.obs)
        self.exp.primary = data_obj.obs['protocol'][0]


    def parseDataFrame(self, dataframe, **kwargs):
        """
        Parse the dataframe in a format that can be used by the database
        :param dataframe: Dataframe to parse
        """

        #load the metadata and features from the dataframe
        if 'id_col' in kwargs:
            id_col = kwargs['id_col']
        else:
            id_col = None
        
        if 'meta_cols' in kwargs:
            meta_cols = kwargs['meta_cols']
        else:
            meta_cols = DEFAULT_META_COLS

        if 'feature_cols' in kwargs:
            feature_cols = kwargs['feature_cols']
        else:
            feature_cols = DEFAULT_FEAT_COLS

        if 'time_series_cols' in kwargs:
            time_series_cols = kwargs['time_series_cols']
        else:
            time_series_cols = None

        dataframe.set_index(id_col, inplace=True) if id_col is not None else None

        #load the metadata
        meta = df_select_by_col(dataframe, meta_cols)
        
        #in our case features must not be in the metadata

        #load the features
        features = df_select_by_col(dataframe, feature_cols)
        
        #drop meta features from the features
        features = features.drop(meta.columns.values, axis=1)

        #time series will be hotloaded from the files, but for now we want to make the parsing of the dataframe as simple as possible
        if time_series_cols is not None:
            time_series = df_select_by_col(dataframe, time_series_cols)
        else:
            time_series = None
        
        #var is gonna be features name and protocol source
        feature_name = features.columns
        protocol_source = [meta['protocol'] for i in range(len(features.columns))]
        var = pd.DataFrame(index=features.columns, data={'feature_name': feature_name, 'protocol_source': protocol_source})


        data = ad.AnnData(X=features, obs=meta, var=var)
        #data.obs_names = meta.columns.values
        #data.var_names = features.columns
        return data

        

    def addEntry(self, name, path):
        """
        Add an entry to the database
        :param name: Name of the entry
        :param path: Path to the entry
        """
        pass

    def addEntries(self, path):
        """
        Add multiple entries to the database
        :param path: Path to the entries
        """
        pass

    def loadEntry(self, name):
        """
        Load an entry from the database
        :param name: Name of the entry
        """
        pass
            
    def updateEntry(self, name):
        """
        Update an entry in the database
        :param name: Name of the entry
        """
        pass

    def __getitem__(self, key, protocol, column):
        return self.data[key]
    
    def __setitem__(self, key, protocol, column, value):
        self.data[key] = value

    def __delitem__(self, key, protocol, column):
        del self.data[key]
