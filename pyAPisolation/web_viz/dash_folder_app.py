#os sys imports
import os
import sys
import glob
import argparse

#dash / plotly imports
import dash
from dash.dependencies import Input, Output
import dash_table
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objs as go
import plotly.express as px

#data science imports
import pandas as pd
import numpy as np
import pyabf

sys.path.append('..')
sys.path.append('')
print(os.getcwd())
#pyAPisolation imports
from pyAPisolation.patch_ml import *
from pyAPisolation.abf_featureextractor import *
from pyAPisolation.loadNWB import loadFile

def _df_select_by_col(df, string_to_find):
    columns = df.columns.values
    out = []
    for col in columns:
        string_found = [x in col for x in string_to_find]
        if np.any(string_found):
            out.append(col)
    return df[out]


class live_data_viz():
    def __init__(self, dir_path=None, database_file=None):
        self.df_raw = None
        self.df = None
        self.para_df =None
        self._run_analysis(dir_path, database_file)
        
        app = dash.Dash("abf", external_stylesheets=[dbc.themes.BOOTSTRAP])
        

        #Umap
        umap_fig = self.gen_umap_plots(1,2)


        #Make grid ui
        
        
        col2 = dbc.Col([dcc.Loading(
                    id="loading-2",
                    children=[html.Div(id='datatable-plot-cell', style={
                    "flex-wrap": "nowrap" })])], width='auto')
        col1 = dbc.Col(umap_fig,
                     width='auto')
        col3 = dbc.Col([dash_table.DataTable(
                id='datatable-row-ids',
                columns=[
                    {'name': i, 'id': i, 'deletable': True} for i in self.df.columns
                    # omit the id column
                    if i != 'id'
                ],
                data=self.df.to_dict('records'),
                filter_action="native",
                sort_action="native",
                sort_mode='multi',
                row_selectable='multi',
                selected_rows=[],
                page_action='native',
                page_current= 0,
                page_size= 10,
                style_cell={
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    'maxWidth': 0
                }
                
            )], id='data-table-col')

         
        app.layout = html.Div([
                dbc.Card([dbc.CardBody([
                 dbc.Row([col1, col2]),
                 dbc.Row([col3])
                 ])]),
                dcc.Interval(
                    id='interval-component',
                    interval=240*1000, # in milliseconds
                    n_intervals=0
                )
                ])
        self.app = app
        #Define Callbacks
        app.callback(
        Output('loading-2', 'children'),
        Input('datatable-row-ids', 'derived_virtual_row_ids'),
        Input('datatable-row-ids', 'selected_row_ids'),
        Input('datatable-row-ids', 'active_cell'))(self.update_cell_plot)


        app.callback(Output('datatable-row-ids', 'data'), 
                   Input('UMAP-graph', 'selectedData'),
                    Input('UMAP-graph', 'figure')
                    )(self._filter_datatable_umap)

        
    def _gen_abf_list(self, dir):
        #os.path.abspath(dir)
        pass

    def _run_analysis(self, dir=None, df=None):
        if df is None:
            
            if dir is not None:
                _, df, _ = folder_feature_extract(os.path.abspath(dir), default_dict, protocol_name='')
            else:
                _, df, _ = folder_feature_extract(os.path.abspath('../data/'), default_dict, protocol_name='')
        else:
            df = pd.read_csv(df) 
        self.df_raw = df
        df = _df_select_by_col(df, ["rheo", "filename", "foldername", "QC"])
        df['id'] = df["filename"]
        df.set_index('id', inplace=True, drop=False)
        self.df = df
        return [dash_table.DataTable(
                id='datatable-row-ids',
                columns=[
                    {'name': i, 'id': i, 'deletable': True} for i in self.df.columns
                    # omit the id column
                    if i != 'id'
                ],
                data=self.df.to_dict('records'),
                filter_action="native",
                sort_action="native",
                sort_mode='multi',
                row_selectable='multi',
                selected_rows=[],
                page_action='native',
                page_current= 0,
                page_size= 10,
                style_cell={
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    'maxWidth': 0
                }
                
            )]

    def gen_umap_plots(self,*args):
        pre_df, outliers = preprocess_df(self.df)
        umap_labels_df, labels_df = _df_select_by_col(self.df_raw, ['umap']), _df_select_by_col(self.df_raw, ['label'])
        if umap_labels_df.empty is False:
            
            data = umap_labels_df[['umap X', 'umap Y']].to_numpy()
            labels = labels_df['label_c'].to_numpy()
        else:
            data = dense_umap(pre_df)
            labels = cluster_df(pre_df)
        #df = _df_select_by_col(self.df, ["rheo", "filename"])
        fig = go.Figure(data=go.Scatter(x=data[:,0], y=data[:,1], mode='markers', marker=dict(color=labels), ids=self.df['id'].to_numpy()))
        #fig = px.parallel_coordinates(df, color="rheobase_width",
                             #color_continuous_scale=px.colors.diverging.Tealrose)
        self.para_df = pre_df
        fig.layout.autosize = True
        return [
                dcc.Graph(
                    id='UMAP-graph',
                    figure=fig,
                    style={
                    "width": "100%",
                    "height": "100%"
                    },
                    config=dict(
                        autosizable=True,
                    ),
                    responsive=True
                    
                )
            ]

    def _filter_datatable_para(self, selectedData, fig):
        def bool_multi_filter(df, kwargs):
            return ' & '.join([f'{key} >= {i[0]} & {key} <= {i[1]}' for key, i in kwargs.items()])

        if selectedData is None:
            out_data = self.df.to_dict('records')
        else:
            #selected_ids = [x['id'] for x in selectedData['points']]
            constraints = {}
            for row in fig['data'][0]['dimensions']:
                try:
                    constraints[row['label']] = row['constraintrange']
                except:
                    constraints[row['label']] = [-9999, 9999]
            out = bool_multi_filter(self.df, constraints)
            filtered_df = self.df.query(out)
            out_data = filtered_df.to_dict('records')
        return out_data
    
    def _filter_datatable_umap(self, selectedData, fig):
        def bool_multi_filter(df, kwargs):
            return ' & '.join([f'{key} >= {i[0]} & {key} <= {i[1]}' for key, i in kwargs.items()])

        if selectedData is None:
            out_data = self.df.to_dict('records')
        else:
            selected_ids = [x['id'] for x in selectedData['points']]
            
            filtered_df = self.df.loc[selected_ids]
            out_data = filtered_df.to_dict('records')
        return out_data

    def update_cell_plot(self, row_ids, selected_row_ids, active_cell):
        selected_id_set = set(selected_row_ids or [])

        if row_ids is None:
            dff = self.df
            # pandas Series works enough like a list for this to be OK
            row_ids = self.df['id']
        else:
            dff = self.df.loc[row_ids]

        active_row_id = active_cell['row_id'] if active_cell else None
        if active_row_id is None:
            active_row_id = self.df.iloc[0]['id']
        if active_row_id is not None:
            fold = self.df.loc[active_row_id][ "foldername"]
            if isinstance(fold, (list,tuple, np.ndarray, pd.Series)):
                fold = fold.to_numpy()[0]
            file_path = os.path.join(fold, active_row_id+ ".abf")
            x, y, c = loadABF(file_path)
            
            cutoff = np.argmin(np.abs(x-2.50))
            x, y = x[:, :cutoff], y[:, :cutoff]
            traces = []
            for sweep_x, sweep_y in zip(x, y):
                traces.append(go.Scattergl(x=sweep_x, y=sweep_y, mode='lines'))
            fig =  go.Figure(data=traces, )

            fig.layout.autosize = True


            return dcc.Graph(
                    id="file_plot",
                    figure=fig,
                   style={
                    "width": "100%",
                    "height": "100%"
                    },
                    config=dict(
                        autosizable=True,
                    ),
                    responsive=True
                )
            

    
    def update_graphs(self, row_ids, selected_row_ids, active_cell):
        selected_id_set = set(selected_row_ids or [])

        if row_ids is None:
            dff = self.df
            # pandas Series works enough like a list for this to be OK
            row_ids = self.df['id']
        else:
            dff = self.df.loc[row_ids]

        active_row_id = active_cell['row_id'] if active_cell else None

        colors = ['#FF69B4' if id == active_row_id
                else '#7FDBFF' if id in selected_id_set
                else '#0074D9'
                for id in row_ids]

        return [
            dcc.Graph(
                id=column + '--row-ids',
                figure={
                    'data': [
                        {
                            'x': str(dff['id']),
                            'y': dff[column],
                            'type': 'bar',
                            'marker': {'color': colors},
                        }
                    ],
                    'layout': {
                        'xaxis': {'automargin': True},
                        'yaxis': {
                            'automargin': True,
                            'title': {'text': column}
                        }
                    },
                },
                style={
                    "width": "50%",
                    "height": "100%"
                },
                config=dict(
                    autosizable=False
                )
            )
            # check if column exists - user may have deleted it
            # If `column.deletable=False`, then you don't
            # need to do this check.
            for column in dff.columns.values[:3]
        ]


if __name__ == '__main__':
    #make an argparse to parse the command line arguments. command line args should be the path to the data folder, or 
    #pregenerated dataframes
    parser = argparse.ArgumentParser(description='web app for visualizing data')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--data_folder', type=str, help='path to the data folder containing the ABF files')
    group.add_argument('--data_df', type=str, help='path to the pregenerated database')
    args = parser.parse_args()
    data_folder = args.data_folder
    data_df = args.data_df

    app = live_data_viz(data_folder, database_file=data_df)


    app.app.run_server(host= '0.0.0.0',debug=False)