from shiny import App, ui, render
from shinywidgets import output_widget, render_widget
import pandas as pd
import plotly.express as px
from datetime import datetime

# Load the data
data = pd.read_json("preprocessed_data.json")

# Convert Date to datetime without timezone info
data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)

# Get the min and max years from the data (as integers)
min_year = data['Date'].dt.year.min().astype(int)
max_year = data['Date'].dt.year.max().astype(int)

# Get unique countries
countries = sorted(data['Country'].unique())

# Define the UI
app_ui = ui.page_fluid(
    ui.h1("IWAC analyse des mots clés"),
    ui.layout_columns(
        ui.column(3,
            ui.input_selectize("country", "Select a country", 
                               choices=["All"] + countries,
                               selected="All")
        ),
        ui.column(3, 
            ui.input_numeric("top_n", "Number of top keywords to display", 10, min=1, max=20),
        ),
        ui.column(6, 
            ui.input_slider("year_range", "Select year range", 
                            min=min_year, max=max_year, 
                            value=[min_year, max_year],
                            step=1,
                            sep=""),
        ),
    ),
    output_widget("keyword_plot")
)

# Define the server logic
def server(input, output, session):
    @render_widget
    def keyword_plot():
        # Get the number of top keywords from the numeric input
        top_n = input.top_n()
        
        # Get the selected year range
        start_year, end_year = input.year_range()
        
        # Get the selected country
        selected_country = input.country()
        
        # Filter data based on the selected year range
        date_filtered_data = data[(data['Date'].dt.year >= start_year) & (data['Date'].dt.year <= end_year)]
        
        # Filter by country if a specific country is selected
        if selected_country != "All":
            date_filtered_data = date_filtered_data[date_filtered_data['Country'] == selected_country]
        
        # Count occurrences of each subject within the filtered data
        subject_counts = date_filtered_data['Subject'].value_counts()
        
        # Get the top N subjects
        top_n_subjects = subject_counts.nlargest(top_n).index.tolist()
        
        # Filter data for top N subjects
        filtered_data = date_filtered_data[date_filtered_data['Subject'].isin(top_n_subjects)]
        
        # Group by Year and Subject, count occurrences
        grouped_data = filtered_data.groupby([filtered_data['Date'].dt.year, 'Subject']).size().reset_index(name='Count')
        grouped_data.rename(columns={grouped_data.columns[0]: 'Year'}, inplace=True)
        
        country_title = f" in {selected_country}" if selected_country != "All" else ""
        fig = px.line(grouped_data, x='Year', y='Count', color='Subject',
                      title=f'Prevalence of Top {top_n} Keywords{country_title} ({start_year} - {end_year})')
        fig.update_layout(
            xaxis_title='Year', 
            yaxis_title='Frequency',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.8)",  # semi-transparent white background
                bordercolor="Black",
                borderwidth=1
            )
        )
        return fig

# Create and run the app
app = App(app_ui, server)
