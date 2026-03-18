import pandas as pd
import numpy as np
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output

# ── Data ─────────────────────────────────────────────────────────────────────

LOSS_CSV  = "all_loss.csv"
RAIN_CSV  = "NE_India_Rainfall_by_State_Period.csv"

loss_raw = pd.read_csv(LOSS_CSV)[['Period','State','Total_Loss_Area_km2']]
rain_raw = pd.read_csv(RAIN_CSV)
loss_raw.columns = loss_raw.columns.str.strip()
rain_raw.columns = rain_raw.columns.str.strip()
loss_raw['State']  = loss_raw['State'].str.strip()
loss_raw['Period'] = loss_raw['Period'].str.strip()
rain_raw['state']  = rain_raw['state'].str.strip()
rain_raw['period'] = rain_raw['period'].str.strip()

PERIOD_YEARS = {'2001-2005':5,'2006-2010':5,'2011-2015':5,'2016-2020':5,'2021-2023':3}
loss_raw['years']       = loss_raw['Period'].map(PERIOD_YEARS)
loss_raw['annual_loss'] = loss_raw['Total_Loss_Area_km2'] / loss_raw['years']

df = pd.merge(loss_raw, rain_raw, left_on=['State','Period'], right_on=['state','period'])

STATES  = sorted(df['State'].unique())
PERIODS = ['2001-2005','2006-2010','2011-2015','2016-2020','2021-2023']

COLORS = {
    'Assam':'#378ADD','Manipur':'#D85A30','Meghalaya':'#1D9E75',
    'Mizoram':'#BA7517','Nagaland':'#7F77DD','Sikkim':'#D4537E',
    'Tripura':'#639922','Arunachal Pradesh':'#888780'
}

# ── Expected vs Actual computation ───────────────────────────────────────────

def compute_projections(data):
    results = []
    for state in data['State'].unique():
        sdf = data[data['State']==state].copy()
        sdf['p_num'] = sdf['Period'].map({p:i+1 for i,p in enumerate(PERIODS)})
        train = sdf[sdf['p_num'] <= 4]
        test  = sdf[sdf['p_num'] == 5]
        if test.empty: continue
        slope, intercept, r, _, _ = stats.linregress(train['p_num'], train['annual_loss'])
        exp_linear   = intercept + slope * 5
        growths = train.sort_values('p_num')['annual_loss'].pct_change().dropna()
        avg_growth   = growths.mean()
        last_annual  = train[train['p_num']==4]['annual_loss'].values[0]
        exp_compound = last_annual * (1 + avg_growth)
        act_annual   = test['annual_loss'].values[0]
        act_total    = test['Total_Loss_Area_km2'].values[0]
        results.append({
            'state': state,
            'actual_annual':    round(act_annual, 1),
            'exp_linear':       round(exp_linear, 1),
            'exp_compound':     round(exp_compound, 1),
            'diff_pct':         round((act_annual - exp_linear) / exp_linear * 100, 1),
            'avg_growth_pct':   round(avg_growth * 100, 1),
            'actual_total':     round(act_total, 1),
            'exp_total_linear': round(exp_linear * 3, 1),
            'r2':               round(r**2, 3),
        })
    return pd.DataFrame(results)

proj = compute_projections(df)

# ── Pearson per state ─────────────────────────────────────────────────────────

def pearson_per_state(data):
    rows = []
    for s in data['State'].unique():
        sd = data[data['State']==s]
        r, p = stats.pearsonr(sd['rainfall_in_mm'], sd['Total_Loss_Area_km2'])
        rows.append({'state':s, 'r':round(r,3), 'p':round(p,3)})
    return pd.DataFrame(rows).sort_values('r', ascending=False)

corr_df = pearson_per_state(df)

# ── App layout ────────────────────────────────────────────────────────────────

app = dash.Dash(__name__, title="NE India Forest Loss Dashboard")

TAB_STYLE       = {'fontFamily':'Arial, sans-serif','fontSize':13}
CARD_STYLE      = {'backgroundColor':'#fff','border':'1px solid #e5e7eb',
                   'borderRadius':10,'padding':16,'marginBottom':16}
HEADER_STYLE    = {'background':'linear-gradient(135deg,#1a3a2a,#2d5a3d)',
                   'color':'white','padding':'20px 30px','borderRadius':10,'marginBottom':20}

def metric_card(label, value, color='#1a3a2a', sub=''):
    return html.Div([
        html.Div(label, style={'fontSize':11,'color':'#6b7280','marginBottom':4}),
        html.Div(value, style={'fontSize':22,'fontWeight':600,'color':color}),
        html.Div(sub,   style={'fontSize':10,'color':'#9ca3af','marginTop':2}) if sub else None,
    ], style={**CARD_STYLE,'flex':1,'minWidth':140})

app.layout = html.Div(style={'fontFamily':'Arial,sans-serif','backgroundColor':'#f3f4f6',
                              'padding':'24px','maxWidth':1200,'margin':'0 auto'}, children=[

    html.Div([
        html.H1("🌿 NE India Forest Loss & Rainfall Analysis",
                style={'margin':0,'fontSize':24,'fontWeight':700}),
        html.P("8 states · 5 periods (2001–2023) · CHIRPS rainfall + GFC forest loss",
               style={'margin':'6px 0 0','opacity':0.8,'fontSize':13}),
    ], style=HEADER_STYLE),

    dcc.Tabs(style=TAB_STYLE, children=[

        # ── TAB 1: Overview ──────────────────────────────────────────────────
        dcc.Tab(label='📊 Overview', children=[
            html.Br(),
            html.Div([
                metric_card("Overall Pearson r", "0.130", "#6b7280", "Rainfall vs Forest Loss"),
                metric_card("p-value", "0.42", "#6b7280", "Not significant"),
                metric_card("Data points", "40", "#1a3a2a", "8 states × 5 periods"),
                metric_card("Trend", "↑ Loss, ↓ Rain", "#D85A30", "Diverging over time"),
            ], style={'display':'flex','gap':12,'flexWrap':'wrap','marginBottom':16}),

            html.Div([
                html.Div([
                    html.H4("Total Forest Loss by Period (km²)", style={'margin':'0 0 10px','fontSize':13}),
                    dcc.Graph(id='loss-bar', config={'displayModeBar':False}),
                ], style={**CARD_STYLE,'flex':1}),
                html.Div([
                    html.H4("Avg Rainfall by Period (mm)", style={'margin':'0 0 10px','fontSize':13}),
                    dcc.Graph(id='rain-bar', config={'displayModeBar':False}),
                ], style={**CARD_STYLE,'flex':1}),
            ], style={'display':'flex','gap':16}),

            html.Div([
                html.H4("Rainfall vs Forest Loss — Dual Axis", style={'margin':'0 0 10px','fontSize':13}),
                dcc.Graph(id='dual-axis', config={'displayModeBar':False}),
            ], style=CARD_STYLE),
        ]),

        # ── TAB 2: Trends ────────────────────────────────────────────────────
        dcc.Tab(label='📈 State Trends', children=[
            html.Br(),
            html.Div([
                html.Label("Select states:", style={'fontSize':12,'fontWeight':600}),
                dcc.Dropdown(
                    id='state-selector',
                    options=[{'label':s,'value':s} for s in STATES],
                    value=STATES,
                    multi=True,
                    style={'fontSize':12}
                ),
            ], style={**CARD_STYLE,'paddingBottom':8}),

            html.Div([
                html.Div([
                    html.H4("Annual Forest Loss (km²/yr)", style={'margin':'0 0 8px','fontSize':13}),
                    dcc.Graph(id='trend-loss', config={'displayModeBar':False}),
                ], style={**CARD_STYLE,'flex':1}),
                html.Div([
                    html.H4("5-yr Period Rainfall (mm)", style={'margin':'0 0 8px','fontSize':13}),
                    dcc.Graph(id='trend-rain', config={'displayModeBar':False}),
                ], style={**CARD_STYLE,'flex':1}),
            ], style={'display':'flex','gap':16}),
        ]),

        # ── TAB 3: Correlation ───────────────────────────────────────────────
        dcc.Tab(label='🔗 Correlation', children=[
            html.Br(),
            html.Div([
                html.Div([
                    html.H4("Scatter: Rainfall vs Forest Loss", style={'margin':'0 0 8px','fontSize':13}),
                    dcc.Graph(id='scatter', config={'displayModeBar':False}),
                ], style={**CARD_STYLE,'flex':1}),
                html.Div([
                    html.H4("Per-state Pearson r", style={'margin':'0 0 8px','fontSize':13}),
                    dcc.Graph(id='corr-bar', config={'displayModeBar':False}),
                ], style={**CARD_STYLE,'flex':1}),
            ], style={'display':'flex','gap':16}),
        ]),

        # ── TAB 4: Expected vs Actual ────────────────────────────────────────
        dcc.Tab(label='🔮 Expected vs Actual (2021–23)', children=[
            html.Br(),
            html.Div([
                metric_card("States below projection", "6 / 8", "#1D9E75", "Actual < linear trend"),
                metric_card("Avg deviation", "−23%", "#1D9E75", "Below expected (ex-Sikkim)"),
                metric_card("Biggest slowdown", "Nagaland −47%", "#1D9E75", "vs linear trend"),
                metric_card("Only above trend", "Tripura +10%", "#D85A30", "Still accelerating"),
            ], style={'display':'flex','gap':12,'flexWrap':'wrap','marginBottom':16}),

            html.Div([
                html.Div([
                    html.H4("Actual vs Expected Annual Loss (km²/yr)", style={'margin':'0 0 8px','fontSize':13}),
                    dcc.Graph(id='proj-bar', config={'displayModeBar':False}),
                ], style={**CARD_STYLE,'flex':1}),
                html.Div([
                    html.H4("3-year Total Loss: Actual vs Expected (km²)", style={'margin':'0 0 8px','fontSize':13}),
                    dcc.Graph(id='total-bar', config={'displayModeBar':False}),
                ], style={**CARD_STYLE,'flex':1}),
            ], style={'display':'flex','gap':16}),

            html.Div([
                html.H4("Detailed Projection Table", style={'margin':'0 0 10px','fontSize':13}),
                html.Div(id='proj-table'),
            ], style=CARD_STYLE),
        ]),
    ]),
])

# ── Callbacks ─────────────────────────────────────────────────────────────────

LAYOUT_BASE = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=40,r=20,t=20,b=40), font=dict(family='Arial',size=11),
    xaxis=dict(showgrid=False, linecolor='#e5e7eb'),
    yaxis=dict(gridcolor='#f3f4f6', linecolor='#e5e7eb'),
)

@app.callback(
    Output('loss-bar','figure'), Output('rain-bar','figure'), Output('dual-axis','figure'),
    Input('loss-bar','id')
)
def overview(_):
    loss_by_p = [df[df['Period']==p]['Total_Loss_Area_km2'].sum() for p in PERIODS]
    rain_by_p = [df[df['Period']==p]['rainfall_in_mm'].mean() for p in PERIODS]

    fig_loss = go.Figure(go.Bar(x=PERIODS, y=loss_by_p,
        marker_color='#E24B4A', marker_line_width=0))
    fig_loss.update_layout(**LAYOUT_BASE, height=240)

    fig_rain = go.Figure(go.Bar(x=PERIODS, y=rain_by_p,
        marker_color='#378ADD', marker_line_width=0))
    fig_rain.update_layout(**LAYOUT_BASE, height=240)

    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(go.Bar(name='Avg Rainfall (mm)', x=PERIODS, y=rain_by_p,
        marker_color='rgba(55,138,221,0.5)', marker_line_width=0), secondary_y=False)
    fig_dual.add_trace(go.Scatter(name='Total Loss (km²)', x=PERIODS, y=loss_by_p,
        mode='lines+markers', line=dict(color='#E24B4A', width=2.5),
        marker=dict(size=7)), secondary_y=True)
    fig_dual.update_layout(**LAYOUT_BASE, height=280,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
    fig_dual.update_yaxes(title_text="Avg Rainfall (mm)", secondary_y=False,
                           gridcolor='#f3f4f6')
    fig_dual.update_yaxes(title_text="Total Loss (km²)", secondary_y=True,
                           showgrid=False)
    return fig_loss, fig_rain, fig_dual


@app.callback(
    Output('trend-loss','figure'), Output('trend-rain','figure'),
    Input('state-selector','value')
)
def state_trends(selected):
    sel = selected or STATES
    fig_loss = go.Figure()
    fig_rain = go.Figure()
    for s in sel:
        sd = df[df['State']==s].sort_values('Period')
        c  = COLORS.get(s, '#888')
        fig_loss.add_trace(go.Scatter(
            x=sd['Period'], y=sd['annual_loss'].round(1),
            name=s, mode='lines+markers',
            line=dict(color=c, width=2), marker=dict(size=5)))
        fig_rain.add_trace(go.Scatter(
            x=sd['Period'], y=sd['rainfall_in_mm'].round(0),
            name=s, mode='lines+markers',
            line=dict(color=c, width=2), marker=dict(size=5)))
    for fig in [fig_loss, fig_rain]:
        fig.update_layout(**LAYOUT_BASE, height=300,
            legend=dict(font=dict(size=10), itemsizing='constant'))
    return fig_loss, fig_rain


@app.callback(
    Output('scatter','figure'), Output('corr-bar','figure'),
    Input('scatter','id')
)
def correlation(_):
    fig_sc = go.Figure()
    for s in STATES:
        sd = df[df['State']==s]
        fig_sc.add_trace(go.Scatter(
            x=sd['rainfall_in_mm'], y=sd['Total_Loss_Area_km2'],
            mode='markers', name=s,
            marker=dict(color=COLORS.get(s,'#888'), size=9, opacity=0.85),
            text=sd['Period'], hovertemplate='%{text}<br>Rain: %{x:.0f} mm<br>Loss: %{y:.1f} km²'))
    fig_sc.update_layout(**LAYOUT_BASE, height=320,
        xaxis_title='Rainfall (mm)', yaxis_title='Forest Loss (km²)',
        legend=dict(font=dict(size=10)))

    colors = ['#1D9E75' if r < 0 else '#E24B4A' for r in corr_df['r']]
    fig_corr = go.Figure(go.Bar(
        x=corr_df['r'], y=corr_df['state'], orientation='h',
        marker_color=colors, marker_line_width=0,
        text=[f"r={r:.3f}" for r in corr_df['r']],
        textposition='outside'))
    fig_corr.add_vline(x=0, line_width=1, line_color='#9ca3af')
    fig_corr.update_layout(**LAYOUT_BASE, height=320)
    fig_corr.update_xaxes(range=[-1,1], showgrid=True, gridcolor='#f3f4f6')
    fig_corr.update_yaxes(showgrid=False)
    return fig_sc, fig_corr


@app.callback(
    Output('proj-bar','figure'), Output('total-bar','figure'), Output('proj-table','children'),
    Input('proj-bar','id')
)
def projections(_):
    p = proj.sort_values('diff_pct')

    fig_proj = go.Figure()
    fig_proj.add_trace(go.Bar(name='Expected (linear)', x=p['state'], y=p['exp_linear'],
        marker_color='rgba(55,138,221,0.4)', marker_line_color='#378ADD', marker_line_width=1))
    fig_proj.add_trace(go.Bar(name='Expected (compound)', x=p['state'], y=p['exp_compound'],
        marker_color='rgba(186,117,23,0.33)', marker_line_color='#BA7517', marker_line_width=1))
    fig_proj.add_trace(go.Bar(name='Actual', x=p['state'], y=p['actual_annual'],
        marker_color='rgba(226,75,74,0.6)', marker_line_color='#E24B4A', marker_line_width=1))
    fig_proj.update_layout(**LAYOUT_BASE, barmode='group', height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=10)),
        yaxis_title='km²/yr')

    fig_total = go.Figure()
    fig_total.add_trace(go.Bar(name='Expected (linear)', x=p['state'], y=p['exp_total_linear'],
        marker_color='rgba(55,138,221,0.4)', marker_line_color='#378ADD', marker_line_width=1))
    fig_total.add_trace(go.Bar(name='Actual', x=p['state'], y=p['actual_total'],
        marker_color='rgba(226,75,74,0.6)', marker_line_color='#E24B4A', marker_line_width=1))
    fig_total.update_layout(**LAYOUT_BASE, barmode='group', height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=10)),
        yaxis_title='km²')

    # Table
    rows = [html.Tr([
        html.Th(c, style={'padding':'7px 10px','background':'#f9fafb',
                'borderBottom':'1px solid #e5e7eb','fontSize':11,'fontWeight':600,'color':'#6b7280'})
        for c in ['State','Avg Growth/Period','Actual (km²/yr)','Expected Linear',
                  'Expected Compound','Deviation','R²']
    ])]
    for _, r in proj.sort_values('diff_pct').iterrows():
        color = '#1D9E75' if r['diff_pct'] < 0 else '#D85A30'
        badge_bg = '#E1F5EE' if r['diff_pct'] < 0 else '#FCEBEB'
        sign = '+' if r['diff_pct'] > 0 else ''
        rows.append(html.Tr([
            html.Td([
                html.Span(style={'width':8,'height':8,'borderRadius':'50%',
                    'background':COLORS.get(r['state'],'#888'),
                    'display':'inline-block','marginRight':6}),
                r['state']
            ], style={'padding':'7px 10px','fontSize':12}),
            html.Td(f"+{r['avg_growth_pct']}%", style={'padding':'7px 10px','fontSize':12}),
            html.Td(str(r['actual_annual']),     style={'padding':'7px 10px','fontSize':12,'fontWeight':600,'color':color}),
            html.Td(str(r['exp_linear']),        style={'padding':'7px 10px','fontSize':12,'color':'#6b7280'}),
            html.Td(str(r['exp_compound']),      style={'padding':'7px 10px','fontSize':12,'color':'#9ca3af'}),
            html.Td(f"{sign}{r['diff_pct']}%",  style={'padding':'5px 10px','fontSize':11,
                'fontWeight':600,'color':color,'background':badge_bg,'borderRadius':4}),
            html.Td(str(r['r2']),                style={'padding':'7px 10px','fontSize':12,'color':'#9ca3af'}),
        ], style={'borderBottom':'1px solid #f3f4f6'}))

    table = html.Table(rows, style={'width':'100%','borderCollapse':'collapse',
        'fontSize':12,'fontFamily':'Arial,sans-serif'})
    return fig_proj, fig_total, table


if __name__ == '__main__':
    print("\n✅ Dashboard running at: http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050)
