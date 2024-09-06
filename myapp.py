from shiny import App, ui
from shinywidgets import output_widget, render_widget
import pandas as pd
import plotly.express as px

# Load the data
data = pd.read_json("preprocessed_data.json")

# Convert Date to datetime without timezone info
data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)

# Count occurrences of each subject
subject_counts = data['Subject'].value_counts()

# Get the top 10 subjects
top_10_subjects = subject_counts.nlargest(10).index.tolist()

# Filter data for top 10 subjects
filtered_data = data[data['Subject'].isin(top_10_subjects)]

# Group by Year and Subject, count occurrences
grouped_data = filtered_data.groupby([filtered_data['Date'].dt.year, 'Subject']).size().reset_index(name='Count')
grouped_data.rename(columns={grouped_data.columns[0]: 'Year'}, inplace=True)

# Define the UI
app_ui = ui.page_fluid(
    ui.h1("IWAC analyse des mots clés"),
    output_widget("keyword_plot")
)

# Define the server logic
def server(input, output, session):
    @render_widget
    def keyword_plot():
        fig = px.line(grouped_data, x='Year', y='Count', color='Subject',
                      title='Prevalence of Top 10 Keywords Over Time')
        fig.update_layout(xaxis_title='Year', yaxis_title='Frequency')
        return fig

# Create and run the app
app = App(app_ui, server)
