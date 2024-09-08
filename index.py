# ----- IMPORTS -----
import os
import zipfile
import io
import pandas as pd
import requests
import dash
import plotly.graph_objects as go
from dash import Dash, dcc, html, callback
import plotly.express as px
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

# ----- CUSTOM THEME ------
color_scheme = {
     'text': '#e8feff',
    'purple-dark': '#18172c',
    'purple-medium': '#4f4898',
    'purple-light': '#aea9f8',
    'maroon': '#69344b',
    'pink': '#b64693',
    'white': '#FFFFFF',
    'blue-main': '#16c1e6',
    'blue-light': '#01E5FD',
    'blue2': '#20accd',  #shades of blue
    'blue3': '#12829b', 
    'blue4': '#055b78',
    'royal-blue': '#2747b8', 
    'blue-dark': '#00243c',
    'dark-background': '#040812',
    'red': '#dd1e28'
}

'''----- 1. LOADING AND PREPROCESSING DATA ----- '''
url = 'https://stacks.stanford.edu/file/druid:yg821jf8611/yg821jf8611_pa_philadelphia_2020_04_01.csv.zip'
filename = 'pa_philadelphia_2020_04_01.csv'
r = requests.get(url)
z = zipfile.ZipFile(io.BytesIO(r.content))
z.extractall()
raw_phil = pd.read_csv(filename, sep=',')
pop_url = 'https://opendata.arcgis.com/api/v3/datasets/d0ac67bb117b42f39614bad23525a13e_0/downloads/data?format=csv&spatialRefId=4326'
pop = pd.read_csv(pop_url, index_col=0) #population data 

#If reading locally, comment out lines 34-40 and uncomment lines below
# raw_phil = pd.read_csv('data/pa_philadelphia_2020_04_01.csv')
# pop = pd.read_csv('data/Vital_Population_Cty.csv')

raw_phil['date'] = pd.to_datetime(raw_phil['date'])
raw_phil['year'] = raw_phil['date'].dt.year
clean_phil = raw_phil.drop(columns=['raw_race', 'raw_individual_contraband', 'raw_vehicle_contraband'])
clean_phil['year'] = clean_phil['date'].dt.year 


pop.drop(['SEX', 'AGE_CATEGORY', 'SOURCE', 'GEOGRAPHY'], axis=1, inplace = True)
pop = pop[(pop['YEAR'] >= 2014) & (pop['YEAR'] <= 2017)]
pop.loc[pop['RACE_ETHNICITY'] == 'Asian/PI (NH)', 'RACE_ETHNICITY'] = 'asian/pacific islander'
pop.loc[pop['RACE_ETHNICITY'] == 'Black (NH)', 'RACE_ETHNICITY'] = 'black'
pop.loc[pop['RACE_ETHNICITY'] == 'Hispanic', 'RACE_ETHNICITY'] = 'hispanic'
pop.loc[pop['RACE_ETHNICITY'] == 'White (NH)', 'RACE_ETHNICITY'] = 'white'
pop.loc[pop['RACE_ETHNICITY'] == 'Multiracial (NH)', 'RACE_ETHNICITY'] = 'other'
pop_aggregated = pop.groupby('RACE_ETHNICITY').agg({'COUNT_': 'sum'}).reset_index()
'''========================================================================================='''

''' ---- CREATING CARDS FOR MAIN PAGE ---- '''
def calculate_total_stops(data, year=None):
    if year and year != 'All':
        data = data[data['date'].dt.year == year]
    return len(data)

def calculate_searches(data, year=None):
    if year and year != 'All':
        data = data[data['date'].dt.year == year]
    return (data['search_conducted'].sum())

def calculate_arrests(data, year=None):
    if year and year != 'All':
        data = data[data['date'].dt.year == year]
    return (data['arrest_made'].sum())

def calculate_hit_rate(data, year=None):
    if year and year != 'All':
        data = data[data['date'].dt.year == year]
    search_with_contraband = data[data['search_conducted'] & data['contraband_found']]
    if len(data[data['search_conducted']]) == 0:
        return 0
    return (len(search_with_contraband) / len(data[data['search_conducted']])) * 100

def create_card(title, value, id=None, subtitle=None):
    return dbc.Card(
         dbc.CardBody(
            [
                html.P(title, className="card-title"),
                html.H2(value, id=id, className="card-text"),
                html.P(subtitle, className="card-subtitle") if subtitle else None
            ], 
            className='card-body hazard-border'
        ),
        className="mb-2 animate__animated animate__flipInX animate__delay-2s"
    )
'''========================================================================================='''

''' ----- PLOTLY PLOTS CREATION ------'''

# 1. DENSITY HEATMAP
# This heatmap shows us the concentration of stops in different areas of Philadelphia.
location_data = clean_phil.groupby(['lat', 'lng']).size().reset_index(name='count')
dmap = px.density_mapbox(location_data,
                         lat='lat',
                         lon='lng', 
                         z='count', 
                         radius=10,
                         zoom=10,
                         mapbox_style='carto-darkmatter',
                         color_continuous_scale = [color_scheme['blue-dark'], color_scheme['blue4'], color_scheme['blue3'], color_scheme['blue-light']]
                    )
dmap.update_layout(
    paper_bgcolor='rgba(0,0,0,0)',  
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(
        visible=False 
        ),
    yaxis=dict(
        visible=False
        ),
    margin=dict(l=0, r=0, t=35, b=0)
    )

# 2. STOPS BY TIME OF DAY 
# This chart splits the time of stops into 'day' and 'night' categories to see which hours are more active. 

clean_phil['time'] = pd.to_datetime(clean_phil['time'], format='%H:%M:%S').dt.time
clean_phil['hour_24'] = pd.to_datetime(clean_phil['time'].astype(str)).dt.hour 
clean_phil['hour_12'] = clean_phil['hour_24'].apply(lambda x: x if x == 12 else x % 12)
clean_phil['period'] = clean_phil['hour_24'].apply(lambda x: 'Day' if 6 <= x < 18 else 'Night') 
stops_by_hour = clean_phil.groupby(['hour_12', 'period']).size().reset_index(name='number_of_stops')
day_data = stops_by_hour[stops_by_hour['period'] == 'Day']
night_data = stops_by_hour[stops_by_hour['period'] == 'Night']

daynight = go.Figure()
daynight.add_trace(go.Scatter(x=day_data['hour_12'], y=day_data['number_of_stops'],
                         mode='lines+markers', name='Day', line=dict(color=color_scheme['blue3'])))
daynight.add_trace(go.Scatter(x=night_data['hour_12'], y=night_data['number_of_stops'],
                         mode='lines+markers', name='Night', line=dict(color=color_scheme['blue-light'])))

# Add a glow effect for the traces
daynight.add_trace(go.Scatter(
    x=night_data['hour_12'], 
    y=night_data['number_of_stops'],
    name='Day Stops',
    mode='lines+markers', 
    line=dict(width=8, color='rgba(150, 240, 254, 0.2)'),  
    showlegend=False
))
daynight.add_trace(go.Scatter(
    x=day_data['hour_12'], 
    y=day_data['number_of_stops'],
    name='Night Stops',
    mode='lines+markers', 
    line=dict(width=8, color='rgba(32, 172, 205, 0.2)'),  
    showlegend=False
))
daynight.update_layout(
    title_font_color=color_scheme['text'],
    legend_font_color=color_scheme['blue4'],
    xaxis_title='Hour of Day',
    xaxis_title_font=dict(
        family='Inconsolata',          
        color=color_scheme['blue3'] 
    ),
    xaxis=dict(tickmode='array', 
               tickvals=list(range(1, 13)), 
               gridcolor=color_scheme['blue4'],  
               zeroline=False,   
               linecolor=color_scheme['blue4'],  
               tickcolor=color_scheme['blue3'], 
               tickfont=dict(color=color_scheme['blue3'])), 

    yaxis=dict(gridcolor=color_scheme['blue4'], 
               linecolor=color_scheme['blue4'],
               zeroline=False,  
               tickcolor=color_scheme['blue3'],  
               tickfont=dict(color=color_scheme['blue3']), 
               ),
    legend_title='Time Period',
    paper_bgcolor='rgba(0,0,0,0)', 
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=35, b=0),
    font=dict(
    family="Inconsolata",
    size=15)
    )

# 3. DISPARITY RATIO BETWEEN STOPS AND POPULATION OF EACH RACE
stop_counts = clean_phil.groupby('subject_race').size().reset_index(name='stop_count') #stop count per race
total_stops = stop_counts['stop_count'].sum()
stop_counts['stop_proportion'] = stop_counts['stop_count'] / total_stops

pop['RACE_ETHNICITY'] = pop['RACE_ETHNICITY'].str.strip()  # Remove any extra spaces
pop_aggregated = pop.groupby('RACE_ETHNICITY').agg({'COUNT_': 'sum'}).reset_index()
total_population = pop_aggregated['COUNT_'].sum()

stop_counts['subject_race'] = stop_counts['subject_race'].str.lower()
pop_aggregated['RACE_ETHNICITY'] = pop_aggregated['RACE_ETHNICITY'].str.lower()

merged_data = pd.merge(stop_counts, pop_aggregated, left_on='subject_race', right_on='RACE_ETHNICITY')
merged_data['population_proportion'] = merged_data['COUNT_'] / total_population
merged_data['disparity_ratio'] = merged_data['stop_proportion'] / merged_data['population_proportion']

popdis = go.Figure(data=[
    go.Bar(name='Stop Proportion', x=merged_data['subject_race'], y=merged_data['stop_proportion'],
           text=[f"{p:.2%}" for p in merged_data['stop_proportion']],
            textposition='outside',  
            textfont=dict(color=color_scheme['blue-light']),  
           marker=dict(color=color_scheme['blue-light'])),
    
    go.Bar(name='Population Proportion', x=merged_data['subject_race'], y=merged_data['population_proportion'],
           text=[f"{p:.2%}" for p in merged_data['population_proportion']],
            textposition='outside', 
            textfont=dict(color=color_scheme['blue-light']), 
           marker=dict(color=color_scheme['blue4']))
           ])

# Add an annotation
black_index = merged_data[merged_data['subject_race'].str.lower() == 'black'].index[0]
popdis.add_annotation(
    x=merged_data['subject_race'][black_index],  # X-axis location
    y=max(merged_data['stop_proportion'][black_index], merged_data['population_proportion'][black_index]) + 0.02,  # Y-axis location, a bit above the bar
    text=f"Disparity Ratio: {merged_data['disparity_ratio'][black_index]:.2f}",  # Text showing the disparity ratio
    showarrow=True,
    arrowhead=2,
    ax=40,  # X offset for the arrow
    ay=-40,  # Y offset for the arrow
    font=dict(family='Inconsolata',color=color_scheme['red'], size=15),  
    arrowcolor=color_scheme['red']
)
popdis.update_layout(
    barmode='group',
    xaxis_title='Race',
    yaxis_title='Proportion',
    showlegend=False,
    xaxis_title_font_color=color_scheme['blue3'],
    yaxis_title_font_color=color_scheme['blue3'],
    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
    plot_bgcolor='rgba(0,0,0,0)',  
    title_font_color=color_scheme['text'],
    legend_font_color=color_scheme['blue4'],
    xaxis=dict(showgrid=False, 
               tickfont=dict(color=color_scheme['blue3']),
               tickvals=[0, 1, 2, 3, 4], 
               ticktext=['Asian/PA', 'Black', 'Hispanic', 'Other', 'White']),  
    yaxis=dict(showgrid=False, 
               tickfont=dict(color=color_scheme['blue3'])),  # Set y-axis label color
    margin=dict(l=0, r=0, t=40, b=0),
    font=dict(family="Inconsolata", size=15)
)

# 4. STOPS, SEARCHES, ARRESTS, AND FRISKS DONUT CHARTS 
search_data = clean_phil[clean_phil['search_conducted'] == True].groupby('subject_race').size().reset_index(name='search_data')
arrest_data = clean_phil[clean_phil['arrest_made'] == True].groupby('subject_race').size().reset_index(name='arrest_data')
frisk_data = clean_phil[clean_phil['frisk_performed'] == True].groupby('subject_race').size().reset_index(name='frisk_data')

fig_search = px.pie(search_data, names='subject_race', values='search_data', 
                   title='Searches by Race',
                   hole=0.4, 
                   labels={'total_searches': 'Total Searches'},
                   color='subject_race', 
                   color_discrete_sequence=[color_scheme['blue3'], color_scheme['blue-light'], color_scheme['blue-main'], color_scheme['blue2'], color_scheme['blue4']])

fig_stop = px.pie(stop_counts, names='subject_race', values='stop_count', 
                   title='Stops by Race',
                   hole=0.4, 
                   labels={'stops_total': 'Total Stops'},
                   color='subject_race',
                   color_discrete_sequence=[color_scheme['blue3'], color_scheme['blue-light'], color_scheme['blue-main'], color_scheme['blue2'], color_scheme['blue4']])

fig_frisk = px.pie(frisk_data, names='subject_race', values='frisk_data', 
                   title='Frisks by Race',
                   hole=0.4, 
                   labels={'total_frisks': 'Total Frisks'},
                   color='subject_race',
                   color_discrete_sequence=[color_scheme['blue3'], color_scheme['blue-light'], color_scheme['blue-main'], color_scheme['blue2'], color_scheme['blue4']])

fig_arrest = px.pie(arrest_data, names='subject_race', values='arrest_data', 
                   title='Arrests by Race',
                   hole=0.4, 
                   labels={'total_arrests': 'Arrests Total'},
                   color='subject_race',
                   color_discrete_sequence=[color_scheme['blue3'], color_scheme['blue-light'], color_scheme['blue-main'], color_scheme['blue2'], color_scheme['blue4']])

fig_search.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
        plot_bgcolor='rgba(0,0,0,0)',  
        showlegend=False,      
        title_font_color=color_scheme['text'],
        margin=dict(l=0, r=0, t=40, b=0),
        font=dict(
        family="Inconsolata",
        size=13,
        ),
        title_font=dict(weight=700)
    )
fig_arrest.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
        plot_bgcolor='rgba(0,0,0,0)',  
        showlegend=False,      
        title_font_color=color_scheme['text'],
        margin=dict(l=0, r=0, t=40, b=0),
         font=dict(
        family="Inconsolata",
        size=13, 
        ),
        title_font=dict(weight=700)
    )
fig_frisk.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
        plot_bgcolor='rgba(0,0,0,0)',  
        showlegend=False,      
        title_font_color=color_scheme['text'],
        margin=dict(l=0, r=0, t=40, b=0),
         font=dict(
        family="Inconsolata",
        size=13, 
        ),
        title_font=dict(weight=700)
    )
fig_stop.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
        plot_bgcolor='rgba(0,0,0,0)',  
        showlegend=False,      
        title_font_color=color_scheme['text'],
        margin=dict(l=3, r=3, t=40, b=0),
         font=dict(
        family="Inconsolata",
        size=13, 
        ),
        title_font=dict(weight=700)
    )

# 5. SEARCH EFFECTIVENESS FUNNEL CHART (prep)
filtered_phil = clean_phil[clean_phil['date'].dt.year != 2018]
filtered_phil['year'] = filtered_phil['date'].dt.year
filtered_data_race = filtered_phil[~filtered_phil['subject_race'].str.lower().isin(['unknown', 'other'])]
search_data = filtered_data_race[filtered_data_race['search_conducted'] == 1]

# 6. CONTRABAND DISCOVERY RATE 
contraband_rates = search_data.groupby('subject_race').apply(
    lambda x: (x['contraband_found'].sum() / len(x)) * 100
).reset_index(name='contraband_rate')
search_counts = search_data['subject_race'].value_counts().reset_index()
search_counts.columns = ['subject_race', 'total_searches']

contraband_rates_yearly = search_data.groupby(['year', 'subject_race']).apply(
    lambda x: round((x['contraband_found'].sum() / len(x)) * 100, 2)
).reset_index(name='contraband_rate')
search_counts_yearly = search_data.groupby(['year', 'subject_race']).size().reset_index(name='total_searches')
outcome_test_data = pd.merge(contraband_rates_yearly, search_counts_yearly, on=['year', 'subject_race'])
fig = px.bar(
    outcome_test_data, 
    x='subject_race', 
    y='contraband_rate',
    color='subject_race',
    text='contraband_rate',
    labels={'contraband_rate': 'Contraband Discovery Rate (%)'},
    animation_frame='year', 
    color_discrete_sequence=[color_scheme['blue-light'], color_scheme['blue4']],
    range_y=[0, outcome_test_data['contraband_rate'].max() * 1.2]  # Adjust y-axis range to accommodate all values
)
fig.update_layout(
    xaxis_title='Race',
    yaxis_title='Contraband Rate (%)',
    margin=dict(l=0, r=0, t=40, b=0),
    title_font_color=color_scheme['text'],
    xaxis=dict(gridcolor=color_scheme['blue4'], 
                tickvals=[0, 1, 2, 3, 4], 
                ticktext=['Asian/PA', 'Black', 'Hispanic', 'White'], 
    linecolor=color_scheme['blue3'],  
    tickcolor=color_scheme['blue3'],  
    tickfont=dict(color=color_scheme['blue3'])), 
    yaxis=dict( gridcolor=color_scheme['blue3'], linecolor=color_scheme['blue3'],
    tickcolor=color_scheme['blue3'], 
    tickfont=dict(color=color_scheme['blue3'])),
    yaxis_title_font_color=color_scheme['blue3'],
    xaxis_title_font_color=color_scheme['blue3'],
    paper_bgcolor='rgba(0,0,0,0)',  
    plot_bgcolor='rgba(0,0,0,0)',
    sliders=[{
        'currentvalue': {
            'font': {
                'color': color_scheme['blue3']  # Change this to your desired color
            }
        },
        'tickcolor': color_scheme['blue3'],  # Change the tick color
        'font': {
            'color': color_scheme['blue3']  # Change the color of the tick labels (years)
        }
    }],
    font=dict(
    family="Inconsolata",
    size=15),
    showlegend=False,
)

''' ------------ SEARCHES, ARRESTS, AND FRISKS BY RACE OVER TIME ------------'''
outcomes = ['arrest_made', 'frisk_performed', 'search_conducted']
saf = filtered_phil.melt(id_vars=['year', 'subject_race'], value_vars=outcomes, var_name='outcome', value_name='count')
saf = saf.groupby(['year', 'subject_race', 'outcome']).sum().reset_index()
saf['outcome'] = pd.Categorical(
    saf['outcome'],
    categories=['search_conducted', 'frisk_performed', 'arrest_made'],
    ordered=True
)
# Create the stacked bar chart
saf_fig = px.bar(
    saf, 
    x='year', 
    y='count', 
    color='subject_race', 
    facet_col='outcome',
    color_discrete_sequence=[color_scheme['blue-light'], color_scheme['blue2'], color_scheme['blue3'], color_scheme['blue4']])
saf_fig.update_layout(
    margin=dict(l=0, r=0, t=40, b=0),
    title_font_color=color_scheme['text'],
    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(
        family="Inconsolata",
        size=15
    ),
     hoverlabel=dict(
        bgcolor='black',
        font_size=15,
        font_family="Karla"
    ),
    showlegend=False)
for axis in saf_fig.layout:
    if axis.startswith('xaxis') or axis.startswith('yaxis'):
        saf_fig.layout[axis].update(
           gridcolor=color_scheme['blue4'], 
            linecolor=color_scheme['blue3'],  
            tickcolor=color_scheme['blue3'],  
            tickfont=dict(color=color_scheme['blue3']),
            title_font=dict(color=color_scheme['blue3'])
        )
# Ensure that 'Year' and 'Count' are capitalized across all facets
for i in range(1, len(outcomes)+1): 
    saf_fig.update_layout({
        f'xaxis{i}_title_text': 'Year',
        f'yaxis{i}_title_text': 'Count'
    })
saf_fig.for_each_annotation(lambda a: a.update(text=a.text.split('=')[1], font=dict(color=color_scheme['blue3'])))
'''========================================================================================='''


''' ---- MAIN DASH APP ----- '''
app =dash.Dash( __name__, title='Policing the Police',  meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ], external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.layout = dbc.Container(children=[
     dcc.Tabs(id='tabs', className='tabs mb-0', value='tab-1', children=[
         # ----- TITLE TAB -----
        dcc.Tab(label='1', className='tab p-0',  children=[
            dbc.Row(className='vh-100 d-flex flex-column', children=[
                html.Div(
                    className=' text-center',
                    children=[
                        html.Img(src='/assets/images/vecteezy_police-beacon-clipart-design-illustration_9380930.png',  style={'width': '60%'}),
                        html.H1(className='mt-3 animate__animated animate__zoomIn', children=['Policing the Police']),
                        html.P(className='h4 fw-bold animate__animated animate__zoomIn', children=['Analyzing Racial Disparities in Philadelphia Traffic Stops']),
                        html.P(className='h5 animate__animated animate__zoomIn', children=['By: Fatima Khan']),
                    ], style={'margin-top': '13%'}
                )]
              )
            ]),
          
          # ----- OVERVIEW TAB  -----
        dcc.Tab(label='2', className='tab p-0', children=[
            dbc.Row([
                html.Span(className='page-title', children=[
                    html.Span('Overview')])
                    ]), 
            dbc.Row(className='card-container p-2', children=[
                dbc.Col(className='col-md-12', children=[
                    dcc.Dropdown(
                        id='year-dropdown',
                        placeholder='Select year',
                        options=[
                            {'label': 'All', 'value': 'All'},
                            {'label': 2014, 'value': 2014},
                            {'label': 2015, 'value': 2015},
                            {'label': 2016, 'value': 2016},
                            {'label': 2017, 'value': 2017}
                        ],
                    value='All',  # Default value
                    style={'width': '150px'}, 
                    className='dropdown-year mb-1'
                    )
                ]),
                # CARDS 
                dbc.Col(create_card("Total Stops", calculate_total_stops(clean_phil), id="total-stops"), md=3),
                dbc.Col(create_card("Searches", f"{calculate_searches(clean_phil):.2f}%", id="search-rate"), md=3),
                dbc.Col(create_card("Arrests", f"{calculate_arrests(clean_phil):.2f}%", id="arrest-rate"), md=3),
                dbc.Col(create_card("Hit Rate", f"{calculate_hit_rate(clean_phil):.2f}%", id="hit-rate"), md=3)
            ]),
            dbc.Row(className='mt-2 justify-content-center', children=[
                dbc.Col(className='card-container p-1', width=7, children=[
                    html.Span(className='chart-title ms-4 pt-1 mb-1', 
                              children=[html.Span('Stops by the Hour')]),
                    dcc.Graph(figure=daynight, config={'displayModeBar': False}, style={'height': '45vh'})
                ]),
                dbc.Col(className='card-container p-1', width=5, children=[
                    html.Span(className='chart-title ms-4 pt-1 mb-1', 
                              children=[html.Span('Geospatial Analysis')]),
                    html.P(className='ms-4 pt-1 mb-1', children=['High-intensity areas: 50-75% population = Black or Hispanic.']),
                    dcc.Graph(figure=dmap, config={'displayModeBar': False}, style={'height': '45vh'})
                ])
            ])
          ]), 
        # ----- HISTORICAL SIGNIFICANCE TAB  -----
        dcc.Tab(label='3', className='tab p-0', children=[
            dbc.Row([
                html.Span(className='page-title', children=[
                    html.Span('Historical Significance')])
            ]),
            dbc.Row([
            dbc.Col(className='d-flex flex-column justify-content-center', width=5, children=[
                html.Span(className='chart-title mb-2', children=[
                    html.Span(className='h4', children=['The Outcome Test'])]),
                html.P(className='animate__animated animate__fadeInLeft animate__delay-2s pt-1 ', children=['Proposed by Nobel prize winning economist Gary Becker to test discrimination in search decisions. ']),
                html.P(className='animate__animated animate__fadeInLeft animate__delay-2s', children=['The Idea: If contraband is found on minorities at the same rate as White drivers, it means that officers do not discriminate. If minorities have a lower rate, it implies that officers are searching minorities on the basis of less evidence.']),                
                html.P(className='animate__animated animate__fadeInLeft animate__delay-2s', children=['Shooting of Michael Brown and BLM movement(2014): caused increased scrutiny on police practices.']),
                html.P(className='animate__animated animate__fadeInLeft animate__delay-2s', children=['Freddie Gray Protests (2015): led to a more aggressive law enforcement approach. However, the decline after may suggest policy changes.'])
            ]),
            dbc.Col(width=7, children=[
                html.Span(className='chart-title ms-4 pt-1 mb-1', 
                              children=[html.Span('Contraband Discovery Rates')]),
                    dcc.Graph(id='outcome-test-chart',config={'displayModeBar': False}, figure=fig, style={'height': '50vh'})
                ])
            ]), 
            dbc.Row([
                dbc.Col(width=12, children=[
                    html.Span(className='chart-title pt-1 mb-1', 
                              children=[html.Span('Stop Progression by Race')]),
                    dcc.Graph(figure=saf_fig, config={'displayModeBar': False}, style={'height': '35vh'})
                ])
            ])
        ]),

          # ----- RACIAL BREAKDOWN TAB -----
          dcc.Tab(label='4', className='tab p-0', children=[
            dbc.Row([
                html.Span(className='page-title', children=[
                    html.Span('Racial Breakdown')])
            ]),
            dbc.Row( children=[
                dbc.Col(className='p-1 card-container', md=3, children=[
                        dcc.Dropdown(
                        id='chart-dropdown', className='dropdown-year', options=[
                        {'label': 'Stops', 'value': 'stop'},
                        {'label': 'Searches', 'value': 'search'},
                        {'label': 'Frisks', 'value': 'frisk'},
                        {'label': 'Arrests', 'value': 'arrest'}
                    ], 
                    value='stop', 
                    placeholder='Select...'),
                    dcc.Graph(id='donut-chart', config={'displayModeBar': False}, style={'height': '50vh'}),
                    html.P(className='ms-4 pt-1 mb-1 mt-3 animate__animated animate__fadeInLeft animate__delay-2s', children=['Majority of stops and outcomes involve Black individuals']),
                    html.P(className='ms-4 pt-1 mb-1 animate__animated animate__fadeInLeft animate__delay-2s', children=['Not proportional to population share (20.8%)']),

                ]), 
                dbc.Col(width=9, className=' p-1 card-container',  children=[
                    dcc.Dropdown(
                       id='race-dropdown',
                        placeholder='Select race...',  
                        options=[{'label': 'Black', 'value': 'black'},
                                 {'label': 'White', 'value': 'white'},
                                 {'label': 'Hispanic', 'value': 'hispanic'},
                                 {'label': 'Asian/PA', 'value': 'asian/pacific islander'}],
                        # value=clean_phil['subject_race'].unique()[0],  # Default value
                        style={'width': '150px'}, 
                        className='dropdown-year'
                ),
                    html.Span(className='chart-title ms-4 pt-1 mb-1', 
                              children=[html.Span('Progression from Stop to Arrested')]),
                    html.P(className='ms-4 pt-1 mb-1 animate__animated animate__fadeInLeft animate__delay-2s', children=['Search → Arrest progression rate highest among White individuals (44.5%) and lowest among Black individuals (31.1%), suggesting more selective searches for White individuals.']),
                    dcc.Graph(id='funnel-chart', config={'displayModeBar': False}, style={'height': '30vh'}),
                    html.Span(className='chart-title ms-4 pt-1 mb-1', 
                              children=[html.Span('Stop vs Population Proportion')]),
                    html.P(className='ms-4 pt-1 mb-1 animate__animated animate__fadeInLeft animate__delay-2s', children=['The disparity ratio (3.21) indicates Black individuals are stopped 3x more than their population proportion.']),
                    dcc.Graph(figure=popdis, config={'displayModeBar': False}, style={'height': '35vh'})
                ])
            ])
        ]),
        dcc.Tab(label='5', className='tab p-0', children=[
            dbc.Row(className='vh-100 d-flex flex-column', children=[
                 html.Div(
                    className=' text-center',
                    children=[
                    html.Img(src='/assets/images/vecteezy_police-beacon-clipart-design-illustration_9380930.png',  style={'width': '60%'}),
                    html.H1(className='mt-3', children=['Thank You! 😊']),
                    html.P(className='lead fw-bold mb-0', children=['Data Sources:']),
                    html.A('The Stanford Open Policing Project', href='https://openpolicing.stanford.edu/',
                            target='_blank', 
                            style={'fontSize': '20px', 'color': color_scheme['text']}
                    ),
                    html.Br(),
                     html.A('U.S. Census Bureau', href='https://www.census.gov/data.html',
                            target='_blank', 
                            style={'fontSize': '20px', 'color': color_scheme['text']}
                    ),
                    html.P(className='lead fw-bold mb-0 mt-3', children=['Get in Touch:']),
                    html.A('✉️ Email ', href='fatima.k215@gmail.com',
                            target='_blank',  # Opens the link in a new tab
                            style={'fontSize': '20px', 'color': color_scheme['text']}
                    ),
                    html.A(' 💼 LinkedIn  ', href='https://www.linkedin.com/in/fatimakay/',
                            target='_blank',
                            style={'fontSize': '20px', 'color': color_scheme['text']}
                    ),
                    html.A(' 🌐 Website ', href='https://fatimakay.github.io/',
                            target='_blank',
                            style={'fontSize': '20px', 'color': color_scheme['text']}
                    ),

                ], style={'margin-top': '13%'}
                )
              ])
        ])
     ])
])


# ----- CALLBACKS -----
@app.callback(
        [
        Output('total-stops', 'children'),
        Output('search-rate', 'children'),
        Output('arrest-rate', 'children'),
        Output('hit-rate', 'children')
        ],
        [Input('year-dropdown', 'value')]

)
def update_stats(selected_year):
    if selected_year == 'All':
        # Compute metrics for all years
        total_stops = f"{calculate_total_stops(clean_phil, selected_year)}"
        search_rate = f"{calculate_searches(clean_phil, selected_year)}"
        arrest_rate = f"{calculate_arrests(clean_phil, selected_year)}"
        hit_rate = f"{calculate_hit_rate(clean_phil, selected_year):.2f}%"
    else:
   # Calculate metrics
        total_stops = f"{calculate_total_stops(clean_phil, selected_year)}"
        search_rate = f"{calculate_searches(clean_phil, selected_year)}%"
        arrest_rate = f"{calculate_arrests(clean_phil, selected_year)}%"
        hit_rate = f"{calculate_hit_rate(clean_phil, selected_year):.2f}%"

    return  total_stops, search_rate, arrest_rate, hit_rate

@app.callback(
    Output('funnel-chart', 'figure'),
    [Input('race-dropdown', 'value')]
)
def update_charts(selected_race):
    race_data = filtered_data_race[filtered_data_race['subject_race'] == selected_race]
    total_stops = len(race_data)
    total_searches_and_frisks = race_data['search_conducted'].sum() + race_data['frisk_performed'].sum()
    total_arrests = race_data['arrest_made'].sum()

    funnel_data = pd.DataFrame({
        'Stage': ['Stopped', 'Searched/Frisked', 'Arrested'],
        'Number': [total_stops, total_searches_and_frisks, total_arrests]
    })
    fig = px.funnel(funnel_data, 
                    x='Number', 
                    y='Stage', 
                    color_discrete_sequence=[color_scheme['blue-light']])
    fig.update_layout(
        funnelmode="stack",
        title_font_color=color_scheme['text'],
        legend_font_color=color_scheme['blue3'],
        yaxis_title_font_color=color_scheme['blue3'],
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',  
        yaxis=dict(showgrid=False, tickfont=dict(color=color_scheme['blue3'])),  # Set y-axis label color
        margin=dict(l=0, r=0, t=40, b=0),
        font=dict(
            family="Inconsolata",
            size=15)
        )
    return fig

@app.callback(
    Output('donut-chart', 'figure'),
    [Input('chart-dropdown', 'value')]
)
def update_donut(selected_value):
    if selected_value == 'search':
        return fig_search
    elif selected_value == 'stop':
        return fig_stop
    elif selected_value == 'frisk':
        return fig_frisk
    elif selected_value == 'arrest':
        return fig_arrest

#serve th dash app
if __name__ == '__main__':
     port = int(os.environ.get('PORT', 8050))  # Default to 8050 if PORT is not set
     app.run_server(port=port, debug=True, use_reloader=False)
