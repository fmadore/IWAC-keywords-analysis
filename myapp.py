from shiny import App, ui, render
import pandas as pd
import plotly.express as px

# Load the data
data = pd.read_json("preprocessed_data.json")

# Convert Date to datetime
data['Date'] = pd.to_datetime(data['Date'])

# Count occurrences of each subject
subject_counts = data['Subject'].value_counts()

# Get the top 10 subjects
top_10_subjects = subject_counts.nlargest(10).index.tolist()

# Filter data for top 10 subjects
filtered_data = data[data['Subject'].isin(top_10_subjects)]

# Group by Date and Subject, count occurrences
grouped_data = filtered_data.groupby([filtered_data['Date'].dt.to_period('Y'), 'Subject']).size().reset_index(name='Count')
grouped_data['Date'] = grouped_data['Date'].dt.to_timestamp()

# Define the UI
app_ui = ui.page_fluid(
    ui.h1("IWAC analyse des mots clés"),
    ui.output_plot("keyword_plot")
)

# Define the server logic
def server(input, output, session):
    @output
    @render.plot
    def keyword_plot():
        fig = px.line(grouped_data, x='Date', y='Count', color='Subject',
                      title='Prevalence of Top 10 Keywords Over Time')
        fig.update_layout(xaxis_title='Year', yaxis_title='Frequency')
        return fig

# Create and run the app
app = App(app_ui, server)