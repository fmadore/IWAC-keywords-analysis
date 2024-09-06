from shiny import App, ui, render
from shinywidgets import output_widget, render_widget
import pandas as pd
import plotly.express as px

# Load the data
data = pd.read_json("preprocessed_data.json")

# Convert Date to datetime without timezone info
data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)

# Count occurrences of each subject
subject_counts = data['Subject'].value_counts()

# Define the UI
app_ui = ui.page_fluid(
    ui.h1("IWAC analyse des mots clés"),
    ui.input_numeric("top_n", "Number of top keywords to display", 10, min=1, max=20),
    output_widget("keyword_plot")
)

# Define the server logic
def server(input, output, session):
    @render_widget
    def keyword_plot():
        # Get the number of top keywords from the numeric input
        top_n = input.top_n()
        
        # Get the top N subjects
        top_n_subjects = subject_counts.nlargest(top_n).index.tolist()
        
        # Filter data for top N subjects
        filtered_data = data[data['Subject'].isin(top_n_subjects)]
        
        # Group by Year and Subject, count occurrences
        grouped_data = filtered_data.groupby([filtered_data['Date'].dt.year, 'Subject']).size().reset_index(name='Count')
        grouped_data.rename(columns={grouped_data.columns[0]: 'Year'}, inplace=True)
        
        fig = px.line(grouped_data, x='Year', y='Count', color='Subject',
                      title=f'Prevalence of Top {top_n} Keywords Over Time')
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
