import dash
from dash.dependencies import Input, Output
import dash_table
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
import pyabf
import os
import sys
import glob
sys.path.append('..')
sys.path.append('')
os.chdir(".\\pyAPisolation\\")
print(os.getcwd())
from pyAPisolation.patch_ml import *
from pyAPisolation.abf_featureextractor import *


def loadABF(file_path, return_obj=False):
    '''
    Employs pyABF to generate numpy arrays of the ABF data. Optionally returns abf object.
    Same I/O as loadNWB
    '''
    abf = pyabf.ABF(file_path)
    dataX = []
    dataY = []
    dataC = []
    for sweep in abf.sweepList:
        abf.setSweep(sweep)
        tempX = abf.sweepX
        tempY = abf.sweepY
        tempC = abf.sweepC
        dataX.append(tempX)
        dataY.append(tempY)
        dataC.append(tempC)
    npdataX = np.vstack(dataX)
    npdataY = np.vstack(dataY)
    npdataC = np.vstack(dataC)

    if return_obj == True:

        return npdataX, npdataY, npdataC, abf
    else:

        return npdataX, npdataY, npdataC

    ##Final return incase if statement fails somehow
    return npdataX, npdataY, npdataC

def _df_select_by_col(df, string_to_find):
    columns = df.columns.values
    out = []
    for col in columns:
        string_found = [x in col for x in string_to_find]
        if np.any(string_found):
            out.append(col)
    return df[out]


class live_data_viz():
    def __init__(self):
        self.df_raw = None
        self.df = None
        self.para_df =None
        self._run_analysis(os.getcwd()+'/bin/')
        
        app = dash.Dash("abf", external_stylesheets=[dbc.themes.BOOTSTRAP])
        

        #Umap
        umap_fig = self.gen_umap_plots()


        #Make grid ui
        
        
        col2 = dbc.Col([dcc.Loading(
                    id="loading-2",
                    children=[html.Div(id='datatable-plot-cell', style={
                    "flex-wrap": "nowrap" })])], width='auto')
        col1 = dbc.Col([dcc.Graph(id='UMAP-graph',
                figure=umap_fig, style={
                    "width": "100%",
                    "height": "100%"
                }
               )], width='auto') # config=dict(
                 #   autosizable=True,
                  #  fillFrame=False
                #),
                #responsive=True
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
                
            )])

         
        app.layout = html.Div([dcc.Input(
                id='dir-input',
                placeholder='Enter a dir',
                type='text',
                value='/../bin'
                ),
                dbc.Card([dbc.CardBody([
                 dbc.Row([col1, col2], style={"flex-wrap":"nowrap"}),
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
        #app.callback(
        #Output('datatable-row-ids-container', 'children'),
        #Input('datatable-row-ids', 'derived_virtual_row_ids'),
        #Input('datatable-row-ids', 'selected_row_ids'),
        #Input('datatable-row-ids', 'active_cell'))(self.update_graphs)
        app.callback(
        Output('loading-2', 'children'),
        Input('datatable-row-ids', 'derived_virtual_row_ids'),
        Input('datatable-row-ids', 'selected_row_ids'),
        Input('datatable-row-ids', 'active_cell'))(self.update_cell_plot)


        #app.callback(Output('datatable-row-ids', 'data'), 
         #           Input('UMAP-graph', 'restyleData'),
          #          Input('UMAP-graph', 'figure')
           #         )(self.filter_datatable)

        app.callback(Output('datatable-row-ids', 'data'),
            Output('UMAP-graph', 'figure'),
            Input('dir-input', 'value'))(self._run_analysis)

        app.callback(Output('dir-input', 'children'),
                    Input('interval-component', 'n_intervals'))(self._gen_abf_list)

    def _gen_abf_list(self, dir):
        #os.path.abspath(dir)
        pass

    def _run_analysis(self, dir):
        _, df, _ = folder_feature_extract(os.path.abspath(dir), default_dict, protocol_name='1000')
        self.df_raw = df
        df = _df_select_by_col(df, ["rheo", "filename", "foldername", "QC"])
        df['id'] = df["filename"]
        df.set_index('id', inplace=True, drop=False)
        self.df = df
        return self.df.to_dict('records'), self.gen_umap_plots()

    def gen_umap_plots(self):
        pre_df = preprocess_df(self.df)
        #data = dense_umap(pre_df)
        #labels = cluster_df(pre_df)
        df = _df_select_by_col(self.df, ["rheo", "filename"])
        #fig = go.Figure(data=go.Scatter(x=data[:,0], y=data[:,1], mode='markers', marker=dict(color=labels), ids=self.df['id'].to_numpy()))
        fig = px.parallel_coordinates(df, color="rheobase_width",
                             color_continuous_scale=px.colors.diverging.Tealrose)
        self.para_df = df
        fig.layout.autosize = True
        return fig

    def filter_datatable(self, selectedData, fig):
        if selectedData is None:
            out_data = self.df.to_dict('records')
        else:
            #selected_ids = [x['id'] for x in selectedData['points']]
            constraints = []
            for row in fig['data'][0]['dimensions']:
                pass
            #filtered_df = self.df.loc[selected_ids]
            out_data = self.df.to_dict('records')
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
            fig =  go.Figure(data=traces)

            fig.layout.autosize = True


            return [
                dcc.Graph(
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
            ]

    
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

    app = live_data_viz()


    app.app.run_server(host= '0.0.0.0',debug=False)