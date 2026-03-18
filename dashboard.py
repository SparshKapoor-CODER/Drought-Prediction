import pandas as pd
import numpy as np
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output

LOSS_CSV = "all_loss.csv"
RAIN_CSV = "NE_India_Rainfall_by_State_Period.csv"

loss_raw = pd.read_csv(LOSS_CSV)[['Period', 'State', 'Total_Loss_Area_km2']]
rain_raw = pd.read_csv(RAIN_CSV)
loss_raw.columns = loss_raw.columns.str.strip()
rain_raw.columns = rain_raw.columns.str.strip()
loss_raw['State']  = loss_raw['State'].str.strip()
loss_raw['Period'] = loss_raw['Period'].str.strip()
rain_raw['state']  = rain_raw['state'].str.strip()
rain_raw['period'] = rain_raw['period'].str.strip()

PERIOD_YEARS = {'2001-2005': 5, '2006-2010': 5, '2011-2015': 5, '2016-2020': 5, '2021-2023': 3}
PERIODS = ['2001-2005', '2006-2010', '2011-2015', '2016-2020', '2021-2023']

loss_raw['years']       = loss_raw['Period'].map(PERIOD_YEARS)
loss_raw['annual_loss'] = loss_raw['Total_Loss_Area_km2'] / loss_raw['years']

df = pd.merge(loss_raw, rain_raw, left_on=['State', 'Period'], right_on=['state', 'period'])
df['annual_rain'] = df['rainfall_in_mm'] / df['years']

STATES = sorted(df['State'].unique())
COLORS = {
    'Assam': '#378ADD', 'Manipur': '#D85A30', 'Meghalaya': '#1D9E75',
    'Mizoram': '#BA7517', 'Nagaland': '#7F77DD', 'Sikkim': '#D4537E',
    'Tripura': '#639922', 'Arunachal Pradesh': '#888780'
}

def compute_projections(data, value_col):
    """
    1. annual rate = value_col / years  (per year)
    2. linear trend on periods 1-4 -> predict period-5 annual rate
    3. compound growth on period-4 annual rate
    4. multiply both by 3 (years in 2021-2023) for 3-yr totals
    """
    results = []
    p_map = {p: i + 1 for i, p in enumerate(PERIODS)}
    for state in data['State'].unique():
        sdf = data[data['State'] == state].copy()
        sdf['p_num']      = sdf['Period'].map(p_map)
        sdf['annual_val'] = sdf[value_col] / sdf['years']
        train = sdf[sdf['p_num'] <= 4].sort_values('p_num')
        test  = sdf[sdf['p_num'] == 5]
        if test.empty:
            continue
        slope, intercept, r, _, _ = stats.linregress(train['p_num'], train['annual_val'])
        exp_annual_linear   = intercept + slope * 5
        growths             = train['annual_val'].pct_change().dropna()
        avg_growth          = growths.mean()
        last_annual         = train['annual_val'].iloc[-1]
        exp_annual_compound = last_annual * (1 + avg_growth)
        act_annual          = test['annual_val'].values[0]
        diff_pct            = (act_annual - exp_annual_linear) / abs(exp_annual_linear) * 100
        results.append({
            'state':               state,
            'actual_annual':       round(act_annual, 1),
            'exp_annual_linear':   round(exp_annual_linear, 1),
            'exp_annual_compound': round(exp_annual_compound, 1),
            'actual_total':        round(act_annual * 3, 1),
            'exp_total_linear':    round(exp_annual_linear * 3, 1),
            'exp_total_compound':  round(exp_annual_compound * 3, 1),
            'diff_pct':            round(diff_pct, 1),
            'avg_growth_pct':      round(avg_growth * 100, 1),
            'r2':                  round(r ** 2, 3),
        })
    return pd.DataFrame(results)

loss_proj = compute_projections(df, 'Total_Loss_Area_km2')
rain_proj = compute_projections(df, 'rainfall_in_mm')

corr_df = pd.DataFrame([{
    'state': s,
    'r': round(stats.pearsonr(df[df['State']==s]['rainfall_in_mm'],
                              df[df['State']==s]['Total_Loss_Area_km2'])[0], 3),
    'p': round(stats.pearsonr(df[df['State']==s]['rainfall_in_mm'],
                              df[df['State']==s]['Total_Loss_Area_km2'])[1], 3),
} for s in STATES]).sort_values('r', ascending=False)

app = dash.Dash(__name__, title="NE India Forest Loss & Rainfall Dashboard")

CARD = {'backgroundColor': '#fff', 'border': '1px solid #e5e7eb',
        'borderRadius': 10, 'padding': 16, 'marginBottom': 16}
LAYOUT_BASE = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=40, r=20, t=20, b=40), font=dict(family='Arial', size=11),
    xaxis=dict(showgrid=False, linecolor='#e5e7eb'),
    yaxis=dict(gridcolor='#f3f4f6', linecolor='#e5e7eb'),
)

def mcard(label, value, color='#1a3a2a', sub='', sub2='', sub2_color='#9ca3af'):
    return html.Div([
        html.Div(label, style={'fontSize': 11, 'color': '#6b7280', 'marginBottom': 4}),
        html.Div(value, style={'fontSize': 20, 'fontWeight': 600, 'color': color}),
        html.Div(sub,   style={'fontSize': 10, 'color': '#9ca3af', 'marginTop': 2}) if sub else None,
        html.Div(sub2,  style={'fontSize': 10, 'color': sub2_color, 'marginTop': 1, 'fontWeight': 500}) if sub2 else None,
    ], style={**CARD, 'flex': 1, 'minWidth': 140})

def proj_table(proj_df, unit):
    rows = [html.Tr([
        html.Th(c, style={'padding': '7px 10px', 'background': '#f9fafb',
                'borderBottom': '1px solid #e5e7eb', 'fontSize': 11,
                'fontWeight': 600, 'color': '#6b7280'})
        for c in ['State', 'Avg Growth/Period',
                  f'Actual ({unit}/yr)', f'Exp Linear ({unit}/yr)', f'Exp Compound ({unit}/yr)',
                  f'Actual 3-yr', f'Exp Linear 3-yr', f'Exp Compound 3-yr',
                  'Deviation', 'R²']
    ])]
    for _, r in proj_df.sort_values('diff_pct').iterrows():
        color    = '#1D9E75' if r['diff_pct'] < 0 else '#D85A30'
        badge_bg = '#E1F5EE' if r['diff_pct'] < 0 else '#FCEBEB'
        sign     = '+' if r['diff_pct'] > 0 else ''
        rows.append(html.Tr([
            html.Td([
                html.Span(style={'width': 8, 'height': 8, 'borderRadius': '50%',
                    'background': COLORS.get(r['state'], '#888'),
                    'display': 'inline-block', 'marginRight': 6}),
                r['state']
            ], style={'padding': '7px 10px', 'fontSize': 12}),
            html.Td(f"{r['avg_growth_pct']}%",        style={'padding': '7px 10px', 'fontSize': 12}),
            html.Td(str(r['actual_annual']),           style={'padding': '7px 10px', 'fontSize': 12, 'fontWeight': 600, 'color': color}),
            html.Td(str(r['exp_annual_linear']),       style={'padding': '7px 10px', 'fontSize': 12, 'color': '#6b7280'}),
            html.Td(str(r['exp_annual_compound']),     style={'padding': '7px 10px', 'fontSize': 12, 'color': '#9ca3af'}),
            html.Td(str(r['actual_total']),            style={'padding': '7px 10px', 'fontSize': 12, 'fontWeight': 600, 'color': color}),
            html.Td(str(r['exp_total_linear']),        style={'padding': '7px 10px', 'fontSize': 12, 'color': '#6b7280'}),
            html.Td(str(r['exp_total_compound']),      style={'padding': '7px 10px', 'fontSize': 12, 'color': '#9ca3af'}),
            html.Td(f"{sign}{r['diff_pct']}%",        style={'padding': '5px 10px', 'fontSize': 11,
                'fontWeight': 600, 'color': color, 'background': badge_bg, 'borderRadius': 4}),
            html.Td(str(r['r2']),                     style={'padding': '7px 10px', 'fontSize': 12, 'color': '#9ca3af'}),
        ], style={'borderBottom': '1px solid #f3f4f6'}))
    return html.Table(rows, style={'width': '100%', 'borderCollapse': 'collapse',
        'fontSize': 12, 'fontFamily': 'Arial,sans-serif', 'overflowX': 'auto', 'display': 'block'})

app.layout = html.Div(
    style={'fontFamily': 'Arial,sans-serif', 'backgroundColor': '#f3f4f6',
           'padding': '24px', 'maxWidth': 1300, 'margin': '0 auto'},
    children=[
        html.Div([
            html.H1("NE India Forest Loss & Rainfall Analysis",
                    style={'margin': 0, 'fontSize': 24, 'fontWeight': 700}),
            html.P("8 states · 5 periods (2001-2023) · CHIRPS rainfall + GFC forest loss",
                   style={'margin': '6px 0 0', 'opacity': 0.8, 'fontSize': 13}),
        ], style={'background': 'linear-gradient(135deg,#1a3a2a,#2d5a3d)',
                  'color': 'white', 'padding': '20px 30px', 'borderRadius': 10, 'marginBottom': 20}),

        dcc.Tabs(style={'fontFamily': 'Arial,sans-serif', 'fontSize': 13}, children=[

            dcc.Tab(label='Overview', children=[
                html.Br(),
                html.Div([
                    mcard("Overall Pearson r", "0.130", "#6b7280", "Rainfall vs Forest Loss"),
                    mcard("p-value", "0.42", "#6b7280", "Not significant"),
                    mcard("Data points", "40", "#1a3a2a", "8 states x 5 periods"),
                    mcard("Trend", "Loss up, Rain down", "#D85A30", "Diverging over time"),
                ], style={'display': 'flex', 'gap': 12, 'flexWrap': 'wrap', 'marginBottom': 16}),
                html.Div([
                    html.Div([html.H4("Total Forest Loss by Period (km2)", style={'margin': '0 0 10px', 'fontSize': 13}),
                              dcc.Graph(id='loss-bar', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                    html.Div([html.H4("Avg Rainfall by Period (mm)", style={'margin': '0 0 10px', 'fontSize': 13}),
                              dcc.Graph(id='rain-bar', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                ], style={'display': 'flex', 'gap': 16}),
                html.Div([html.H4("Rainfall vs Forest Loss - Dual Axis", style={'margin': '0 0 10px', 'fontSize': 13}),
                          dcc.Graph(id='dual-axis', config={'displayModeBar': False})], style=CARD),
            ]),

            dcc.Tab(label='State Trends', children=[
                html.Br(),
                html.Div([
                    html.Label("Select states:", style={'fontSize': 12, 'fontWeight': 600}),
                    dcc.Dropdown(id='state-selector',
                        options=[{'label': s, 'value': s} for s in STATES],
                        value=STATES, multi=True, style={'fontSize': 12}),
                ], style={**CARD, 'paddingBottom': 8}),
                html.Div([
                    html.Div([html.H4("Annual Forest Loss (km2/yr)", style={'margin': '0 0 8px', 'fontSize': 13}),
                              dcc.Graph(id='trend-loss', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                    html.Div([html.H4("Annual Rainfall (mm/yr)", style={'margin': '0 0 8px', 'fontSize': 13}),
                              dcc.Graph(id='trend-rain', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                ], style={'display': 'flex', 'gap': 16}),
            ]),

            dcc.Tab(label='Expected vs Actual Rainfall (2021-23)', children=[
                html.Br(),
                html.Div(id='rain-proj-metrics',
                    style={'display': 'flex', 'gap': 12, 'flexWrap': 'wrap', 'marginBottom': 16}),
                html.Div([
                    html.Div([html.H4("Annual Rainfall: Actual vs Expected (mm/yr)", style={'margin': '0 0 8px', 'fontSize': 13}),
                              dcc.Graph(id='rain-proj-annual', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                    html.Div([html.H4("3-Year Total Rainfall: Actual vs Expected (mm)", style={'margin': '0 0 8px', 'fontSize': 13}),
                              dcc.Graph(id='rain-proj-total', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                ], style={'display': 'flex', 'gap': 16}),
                html.Div([html.H4("Rainfall Projection Table", style={'margin': '0 0 10px', 'fontSize': 13}),
                          html.Div(id='rain-proj-table')], style=CARD),
            ]),

            dcc.Tab(label='Expected vs Actual Forest Loss (2021-23)', children=[
                html.Br(),
                html.Div(id='loss-proj-metrics',
                    style={'display': 'flex', 'gap': 12, 'flexWrap': 'wrap', 'marginBottom': 16}),
                html.Div([
                    html.Div([html.H4("Annual Loss: Actual vs Expected (km2/yr)", style={'margin': '0 0 8px', 'fontSize': 13}),
                              dcc.Graph(id='loss-proj-annual', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                    html.Div([html.H4("3-Year Total Loss: Actual vs Expected (km2)", style={'margin': '0 0 8px', 'fontSize': 13}),
                              dcc.Graph(id='loss-proj-total', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                ], style={'display': 'flex', 'gap': 16}),
                html.Div([html.H4("Forest Loss Projection Table", style={'margin': '0 0 10px', 'fontSize': 13}),
                          html.Div(id='loss-proj-table')], style=CARD),
            ]),

            dcc.Tab(label='Correlation', children=[
                html.Br(),
                html.Div([
                    html.Div([html.H4("Scatter: Rainfall vs Forest Loss", style={'margin': '0 0 8px', 'fontSize': 13}),
                              dcc.Graph(id='scatter', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                    html.Div([html.H4("Per-state Pearson r", style={'margin': '0 0 8px', 'fontSize': 13}),
                              dcc.Graph(id='corr-bar', config={'displayModeBar': False})], style={**CARD, 'flex': 1}),
                ], style={'display': 'flex', 'gap': 16}),
            ]),
        ]),
    ]
)

@app.callback(
    Output('loss-bar', 'figure'), Output('rain-bar', 'figure'), Output('dual-axis', 'figure'),
    Input('loss-bar', 'id')
)
def overview(_):
    loss_by_p = [df[df['Period'] == p]['Total_Loss_Area_km2'].sum() for p in PERIODS]
    rain_by_p = [df[df['Period'] == p]['rainfall_in_mm'].mean() for p in PERIODS]
    fig_loss = go.Figure(go.Bar(x=PERIODS, y=loss_by_p, marker_color='#E24B4A', marker_line_width=0))
    fig_loss.update_layout(**LAYOUT_BASE, height=240)
    fig_rain = go.Figure(go.Bar(x=PERIODS, y=rain_by_p, marker_color='#378ADD', marker_line_width=0))
    fig_rain.update_layout(**LAYOUT_BASE, height=240)
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(go.Bar(name='Avg Rainfall (mm)', x=PERIODS, y=rain_by_p,
        marker_color='rgba(55,138,221,0.5)', marker_line_width=0), secondary_y=False)
    fig_dual.add_trace(go.Scatter(name='Total Loss (km2)', x=PERIODS, y=loss_by_p,
        mode='lines+markers', line=dict(color='#E24B4A', width=2.5), marker=dict(size=7)), secondary_y=True)
    fig_dual.update_layout(**LAYOUT_BASE, height=280,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
    fig_dual.update_yaxes(title_text="Avg Rainfall (mm)", secondary_y=False, gridcolor='#f3f4f6')
    fig_dual.update_yaxes(title_text="Total Loss (km2)", secondary_y=True, showgrid=False)
    return fig_loss, fig_rain, fig_dual

@app.callback(
    Output('trend-loss', 'figure'), Output('trend-rain', 'figure'),
    Input('state-selector', 'value')
)
def state_trends(selected):
    sel = selected or STATES
    fig_loss = go.Figure()
    fig_rain = go.Figure()
    for s in sel:
        sd = df[df['State'] == s].sort_values('Period')
        c  = COLORS.get(s, '#888')
        fig_loss.add_trace(go.Scatter(x=sd['Period'], y=sd['annual_loss'].round(1), name=s,
            mode='lines+markers', line=dict(color=c, width=2), marker=dict(size=5)))
        fig_rain.add_trace(go.Scatter(x=sd['Period'], y=sd['annual_rain'].round(1), name=s,
            mode='lines+markers', line=dict(color=c, width=2), marker=dict(size=5)))
    for fig in [fig_loss, fig_rain]:
        fig.update_layout(**LAYOUT_BASE, height=300, legend=dict(font=dict(size=10), itemsizing='constant'))
    fig_rain.update_layout(yaxis_title='mm/yr')
    fig_loss.update_layout(yaxis_title='km2/yr')
    return fig_loss, fig_rain

@app.callback(
    Output('rain-proj-metrics', 'children'),
    Output('rain-proj-annual', 'figure'),
    Output('rain-proj-total', 'figure'),
    Output('rain-proj-table', 'children'),
    Input('rain-proj-annual', 'id')
)
def rain_projections(_):
    rp        = rain_proj.sort_values('diff_pct')

    def diff_compound(row):
        return round((row['actual_annual'] - row['exp_annual_compound']) / abs(row['exp_annual_compound']) * 100, 1)

    rp = rp.copy()
    rp['diff_pct_compound'] = rp.apply(diff_compound, axis=1)

    below_lin  = int((rp['diff_pct'] < 0).sum())
    below_comp = int((rp['diff_pct_compound'] < 0).sum())
    avg_lin    = round(rp['diff_pct'].mean(), 1)
    avg_comp   = round(rp['diff_pct_compound'].mean(), 1)
    worst_lin  = rp.loc[rp['diff_pct'].idxmin()]
    worst_comp = rp.loc[rp['diff_pct_compound'].idxmin()]
    above_lin  = rp[rp['diff_pct'] > 0]
    above_comp = rp[rp['diff_pct_compound'] > 0]

    def sign(v): return f"+{v}%" if v > 0 else f"{v}%"

    metrics = [
        mcard("States below projection",
              f"Linear: {below_lin}/8   Compound: {below_comp}/8",
              "#1D9E75", "Actual < linear trend", "Actual < compound trend", "#1D9E75"),
        mcard("Avg deviation",
              f"Lin: {sign(avg_lin)}",
              "#1D9E75" if avg_lin < 0 else "#D85A30",
              f"vs linear trend",
              f"Compound: {sign(avg_comp)}",
              "#1D9E75" if avg_comp < 0 else "#D85A30"),
        mcard("Biggest decline (linear)",
              f"{worst_lin['state']}",
              "#D85A30",
              f"Lin: {sign(worst_lin['diff_pct'])} vs expected",
              f"Comp: {sign(worst_lin['diff_pct_compound'])} vs expected",
              "#BA7517"),
        mcard("Biggest decline (compound)",
              f"{worst_comp['state']}",
              "#D85A30",
              f"Comp: {sign(worst_comp['diff_pct_compound'])} vs expected",
              f"Lin: {sign(worst_comp['diff_pct'])} vs expected",
              "#BA7517"),
    ]
    fig_ann = go.Figure()
    fig_ann.add_trace(go.Bar(name='Expected linear (mm/yr)', x=rp['state'], y=rp['exp_annual_linear'],
        marker_color='rgba(55,138,221,0.4)', marker_line_color='#378ADD', marker_line_width=1))
    fig_ann.add_trace(go.Bar(name='Expected compound (mm/yr)', x=rp['state'], y=rp['exp_annual_compound'],
        marker_color='rgba(186,117,23,0.33)', marker_line_color='#BA7517', marker_line_width=1))
    fig_ann.add_trace(go.Bar(name='Actual (mm/yr)', x=rp['state'], y=rp['actual_annual'],
        marker_color='rgba(29,158,117,0.6)', marker_line_color='#1D9E75', marker_line_width=1))
    fig_ann.update_layout(**LAYOUT_BASE, barmode='group', height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=10)), yaxis_title='mm/yr')
    fig_tot = go.Figure()
    fig_tot.add_trace(go.Bar(name='Expected linear (3-yr)', x=rp['state'], y=rp['exp_total_linear'],
        marker_color='rgba(55,138,221,0.4)', marker_line_color='#378ADD', marker_line_width=1))
    fig_tot.add_trace(go.Bar(name='Expected compound (3-yr)', x=rp['state'], y=rp['exp_total_compound'],
        marker_color='rgba(186,117,23,0.33)', marker_line_color='#BA7517', marker_line_width=1))
    fig_tot.add_trace(go.Bar(name='Actual (3-yr)', x=rp['state'], y=rp['actual_total'],
        marker_color='rgba(29,158,117,0.6)', marker_line_color='#1D9E75', marker_line_width=1))
    fig_tot.update_layout(**LAYOUT_BASE, barmode='group', height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=10)), yaxis_title='mm (3-yr total)')
    return metrics, fig_ann, fig_tot, proj_table(rp, 'mm')

@app.callback(
    Output('loss-proj-metrics', 'children'),
    Output('loss-proj-annual', 'figure'),
    Output('loss-proj-total', 'figure'),
    Output('loss-proj-table', 'children'),
    Input('loss-proj-annual', 'id')
)
def loss_projections(_):
    p = loss_proj.sort_values('diff_pct').copy()

    def diff_compound(row):
        return round((row['actual_annual'] - row['exp_annual_compound']) / abs(row['exp_annual_compound']) * 100, 1)
    p['diff_pct_compound'] = p.apply(diff_compound, axis=1)

    below_lin  = int((p['diff_pct'] < 0).sum())
    below_comp = int((p['diff_pct_compound'] < 0).sum())
    avg_lin    = round(p['diff_pct'].mean(), 1)
    avg_comp   = round(p['diff_pct_compound'].mean(), 1)
    worst_lin  = p.loc[p['diff_pct'].idxmin()]
    worst_comp = p.loc[p['diff_pct_compound'].idxmin()]

    def sign(v): return f"+{v}%" if v > 0 else f"{v}%"

    loss_metrics = [
        mcard("States below projection",
              f"Linear: {below_lin}/8   Compound: {below_comp}/8",
              "#1D9E75", "Actual < linear trend", "Actual < compound trend", "#1D9E75"),
        mcard("Avg deviation",
              f"Lin: {sign(avg_lin)}",
              "#1D9E75" if avg_lin < 0 else "#D85A30",
              "vs linear trend",
              f"Compound: {sign(avg_comp)}",
              "#1D9E75" if avg_comp < 0 else "#D85A30"),
        mcard("Biggest slowdown (linear)",
              f"{worst_lin['state']}",
              "#D85A30",
              f"Lin: {sign(worst_lin['diff_pct'])} vs expected",
              f"Comp: {sign(worst_lin['diff_pct_compound'])} vs expected",
              "#BA7517"),
        mcard("Biggest slowdown (compound)",
              f"{worst_comp['state']}",
              "#D85A30",
              f"Comp: {sign(worst_comp['diff_pct_compound'])} vs expected",
              f"Lin: {sign(worst_comp['diff_pct'])} vs expected",
              "#BA7517"),
    ]

    fig_ann = go.Figure()
    fig_ann.add_trace(go.Bar(name='Expected linear (km2/yr)', x=p['state'], y=p['exp_annual_linear'],
        marker_color='rgba(55,138,221,0.4)', marker_line_color='#378ADD', marker_line_width=1))
    fig_ann.add_trace(go.Bar(name='Expected compound (km2/yr)', x=p['state'], y=p['exp_annual_compound'],
        marker_color='rgba(186,117,23,0.33)', marker_line_color='#BA7517', marker_line_width=1))
    fig_ann.add_trace(go.Bar(name='Actual (km2/yr)', x=p['state'], y=p['actual_annual'],
        marker_color='rgba(226,75,74,0.6)', marker_line_color='#E24B4A', marker_line_width=1))
    fig_ann.update_layout(**LAYOUT_BASE, barmode='group', height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=10)), yaxis_title='km2/yr')
    fig_tot = go.Figure()
    fig_tot.add_trace(go.Bar(name='Expected linear (3-yr)', x=p['state'], y=p['exp_total_linear'],
        marker_color='rgba(55,138,221,0.4)', marker_line_color='#378ADD', marker_line_width=1))
    fig_tot.add_trace(go.Bar(name='Expected compound (3-yr)', x=p['state'], y=p['exp_total_compound'],
        marker_color='rgba(186,117,23,0.33)', marker_line_color='#BA7517', marker_line_width=1))
    fig_tot.add_trace(go.Bar(name='Actual (3-yr)', x=p['state'], y=p['actual_total'],
        marker_color='rgba(226,75,74,0.6)', marker_line_color='#E24B4A', marker_line_width=1))
    fig_tot.update_layout(**LAYOUT_BASE, barmode='group', height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=10)), yaxis_title='km2 (3-yr total)')
    return loss_metrics, fig_ann, fig_tot, proj_table(p, 'km2')

@app.callback(
    Output('scatter', 'figure'), Output('corr-bar', 'figure'),
    Input('scatter', 'id')
)
def correlation(_):
    fig_sc = go.Figure()
    for s in STATES:
        sd = df[df['State'] == s]
        fig_sc.add_trace(go.Scatter(x=sd['rainfall_in_mm'], y=sd['Total_Loss_Area_km2'],
            mode='markers', name=s, marker=dict(color=COLORS.get(s, '#888'), size=9, opacity=0.85),
            text=sd['Period'], hovertemplate='%{text}<br>Rain: %{x:.0f} mm<br>Loss: %{y:.1f} km2'))
    fig_sc.update_layout(**LAYOUT_BASE, height=320, xaxis_title='Rainfall (mm)',
        yaxis_title='Forest Loss (km2)', legend=dict(font=dict(size=10)))
    colors = ['#1D9E75' if r < 0 else '#E24B4A' for r in corr_df['r']]
    fig_corr = go.Figure(go.Bar(x=corr_df['r'], y=corr_df['state'], orientation='h',
        marker_color=colors, marker_line_width=0,
        text=[f"r={r:.3f}" for r in corr_df['r']], textposition='outside'))
    fig_corr.add_vline(x=0, line_width=1, line_color='#9ca3af')
    fig_corr.update_layout(**LAYOUT_BASE, height=320)
    fig_corr.update_xaxes(range=[-1, 1], showgrid=True, gridcolor='#f3f4f6')
    fig_corr.update_yaxes(showgrid=False)
    return fig_sc, fig_corr

if __name__ == '__main__':
    print("\n Dashboard running at: http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050)
