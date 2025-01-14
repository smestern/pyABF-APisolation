import numpy as np

from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.cluster import AgglomerativeClustering
from sklearn.ensemble import RandomForestClassifier, IsolationForest

#import umap
from sklearn.manifold import TSNE
import umap

def dense_umap(df):
    dens_map = umap.UMAP( metric='euclidean', min_dist=0.5, n_components=2).fit_transform(df)
    return dens_map

def preprocess_df(df, remove_outliers=True): 
    df = df.select_dtypes(["float32", "float64", "int32", "int64"]).drop(columns=["GMM cluster label"])
    scaler = StandardScaler()
    impute = SimpleImputer()
    
    out = impute.fit_transform(df)
    out, outliers = drop_outliers(out) if remove_outliers else (out, [])
    out = scaler.fit_transform(out)
    return out, outliers

def drop_outliers(df):
    od = IsolationForest(contamination='auto')
    f_outliers = od.fit_predict(df)
    drop_o = np.nonzero(np.where(f_outliers==-1, 1, 0))[0]
    out = np.delete(df, drop_o, axis=0) 
    #return outliers
    return out, drop_o

def cluster_df(df, n=5):
    clust = AgglomerativeClustering(n_clusters=n)
    y = clust.fit_predict(df)
    return y

def feature_importance(df, labels):
    rf = RandomForestClassifier(n_estimators=500)
    rf.fit(df, labels)
    feat_import = rf.feature_importances_
    return np.argsort(feat_import)[::-1]

def extract_features(df, ret_labels=False, labels=None):
    """Extract important features from the dataframe. Features are 'important' if they are able to predict the labels. If no labels are provided, 
    the function will cluster the data and use the clusters as labels. If the labels are provided, the function will encode the labels and use them to predict the features.
    The function will return the column names of the important features and the labels if ret_labels is True. If ret_labels is False, the function will return the column names of the important features."""
    #handle the labels

    pre_df, outliers = preprocess_df(df)

    if labels is None:
        labels = cluster_df(pre_df)
        labels_feat = labels.copy()
        LE = None
    elif isinstance(labels, np.ndarray):
        if labels.dtype != np.int32:
            #encode the labels
            LE = LabelEncoder()
            labels_feat = LE.fit_transform(labels)

    idx_feat = feature_importance(pre_df, labels_feat)
    if outliers is not None:
        new_labels = []
        labels_iter = iter(labels_feat)
        for i in np.arange(len(df)):
            if i in outliers:
                new_labels.append(0)
            else:
                new_labels.append(next(labels_iter))
        labels_feat = np.array(new_labels)
        labels = LE.inverse_transform(labels_feat) if LE is not None else np.array(new_labels)

    col = df.columns.values
    if ret_labels:
        return col[idx_feat], labels
    else:
        return col[idx_feat]