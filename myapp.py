from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget
import pandas as pd
import plotly.express as px
from datetime import datetime
from shiny.types import ImgData

# Load the data
data = pd.read_json("preprocessed_data.json")

# Convert Date to datetime without timezone info
data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)

# Get the min and max years from the data (as integers)
min_year = data['Date'].dt.year.min().astype(int)
max_year = data['Date'].dt.year.max().astype(int)

# Get unique countries (including all countries)
countries = sorted(data['Country'].unique())

# Get unique categories, filtering out None values and converting to strings
categories = ["Tout"] + sorted(str(cat) for cat in data['Category'].unique() if pd.notna(cat))

# Define the UI for the first tab (current visualization)
tab1_ui = ui.page_fluid(
    ui.div(
        ui.h2("Mots-clés les plus fréquents", style="text-align: center; margin-bottom: 20px;"),
        ui.p(
            "Le graphique interactif montre la fréquence annuelle des X mots-clés les plus fréquents selon les critères choisis "
            "(par exemple, le pays, la période temporelle, ou le journal), tels qu'ils sont dérivés des métadonnées du Dublin Core Subject "
            "et Spatial Coverage. Cette visualisation permet d'observer l'évolution de la prévalence des mots-clés au fil du temps, "
            "révélant potentiellement des tendances ou des changements dans les sujets d'intérêt. Il est important de noter que "
            "l'attribution de ces mots-clés n'est pas exhaustive. Par conséquent, l'analyse présentée ici doit être considérée comme "
            "un premier aperçu qui mérite un examen plus approfondi pour apprécier pleinement les complexités et les subtilités de "
            "l'ensemble de données.",
            style="text-align: justify; margin-bottom: 20px; padding: 0 20px;"
        ),
    ),
    output_widget("keyword_plot")
)

# Define the UI for the second tab (comparison of selected keywords)
tab2_ui = ui.div(
    ui.h2("Comparaison de mots-clés choisis", style="text-align: center; margin-bottom: 20px;"),
    ui.p(
        "Cette visualisation permet de comparer la fréquence annuelle des mots-clés sélectionnés. "
        "Choisissez jusqu'à X mots-clés pour observer leur évolution au fil du temps selon les critères choisis.",
        style="text-align: justify; margin-bottom: 20px; padding: 0 20px;"
    ),
    ui.input_selectize(
        "selected_keywords",
        "Sélectionnez les mots-clés",
        choices=[],  # We'll populate this dynamically
        multiple=True
    ),
    output_widget("comparison_plot")
)

# Define the main UI with navset_tab, page_sidebar, and navbar
app_ui = ui.page_navbar(
    ui.nav_panel("Analyse des mots-clés",
        ui.page_sidebar(
            ui.sidebar(
                ui.input_selectize("country", "Pays", 
                                   choices=["Tout"] + countries,
                                   selected="Tout"),
                ui.output_ui("newspaper_selector"),
                ui.input_select("category", "Catégorie",
                                choices=categories,
                                selected="Tout"),
                ui.input_slider("year_range", "Années", 
                                min=min_year, max=max_year, 
                                value=[min_year, max_year],
                                step=1,
                                sep=""),
                ui.input_slider("top_n", "# mots-clés", min=1, max=10, value=5, step=1),
            ),
            ui.navset_tab(
                ui.nav_panel("Mots-clés les plus fréquents", tab1_ui),
                ui.nav_panel("Comparaison de mots-clés choisis", tab2_ui),
            ),
        )
    ),
    ui.nav_spacer(),
    ui.nav_control(ui.input_dark_mode(id="dark_mode")),
    title="Collection Islam Afrique de l'Ouest",
    bg="#0062cc",
    inverse=True,
)

# Define the server logic
def server(input, output, session):

    @output
    @render.ui
    def newspaper_selector():
        selected_country = input.country()
        if selected_country == "Tout":
            newspapers = sorted(data['Newspaper'].unique())
        else:
            newspapers = sorted(data[data['Country'] == selected_country]['Newspaper'].unique())
        
        return ui.input_checkbox_group(
            "newspapers",
            "Journaux",
            choices=newspapers,
            selected=newspapers  # Select all newspapers by default
        )

    @render_widget
    def keyword_plot():
        # Get the number of top keywords from the numeric input
        top_n = input.top_n()
        
        # Get the selected year range
        start_year, end_year = input.year_range()
        
        # Get the selected country
        selected_country = input.country()
        
        # Get the selected newspapers
        selected_newspapers = input.newspapers()
        
        # Get the selected category
        selected_category = input.category()
        
        # Filter data based on the selected year range
        date_filtered_data = data[(data['Date'].dt.year >= start_year) & 
                                  (data['Date'].dt.year <= end_year)]
        
        # Filter by country if a specific country is selected
        if selected_country != "Tout":
            date_filtered_data = date_filtered_data[date_filtered_data['Country'] == selected_country]
        
        # Filter by newspapers if any are selected
        if selected_newspapers:
            date_filtered_data = date_filtered_data[date_filtered_data['Newspaper'].isin(selected_newspapers)]
        
        # Filter by category if a specific category is selected
        if selected_category != "Tout":
            date_filtered_data = date_filtered_data[date_filtered_data['Category'] == selected_category]
        
        # Define excluded keywords
        excluded_keywords = ["Bénin", "Togo", "Burkina Faso"]
        
        # Count occurrences of each subject within the filtered data, excluding the specified keywords
        subject_counts = date_filtered_data[~date_filtered_data['Subject'].isin(excluded_keywords)]['Subject'].value_counts()
        
        # Get the top N subjects
        top_n_subjects = subject_counts.nlargest(top_n).index.tolist()
        
        # Filter data for top N subjects
        filtered_data = date_filtered_data[date_filtered_data['Subject'].isin(top_n_subjects)]
        
        # Group by Year and Subject, count occurrences
        grouped_data = filtered_data.groupby([filtered_data['Date'].dt.year, 'Subject']).size().reset_index(name='Count')
        grouped_data.rename(columns={grouped_data.columns[0]: 'Year'}, inplace=True)
        
        country_title = f" in {selected_country}" if selected_country != "Tout" else ""
        newspaper_title = f" ({', '.join(selected_newspapers)})" if selected_newspapers else ""
        category_title = f" for {selected_category}" if selected_category != "Tout" else ""
        fig = px.line(grouped_data, x='Year', y='Count', color='Subject',
                      title=f'Prevalence of Top {top_n} Keywords{country_title}{newspaper_title}{category_title} ({start_year} - {end_year})')
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

    @reactive.Effect
    @reactive.event(input.country, input.newspapers, input.category, input.top_n)
    def update_keyword_choices():
        # Filter data based on current selections
        filtered_data = data

        if input.country() != "Tout":
            filtered_data = filtered_data[filtered_data['Country'] == input.country()]
        
        if input.newspapers():
            filtered_data = filtered_data[filtered_data['Newspaper'].isin(input.newspapers())]
        
        if input.category() != "Tout":
            filtered_data = filtered_data[filtered_data['Category'] == input.category()]

        # Get unique subjects, excluding the ones we don't want
        excluded_keywords = ["Bénin", "Togo", "Burkina Faso"]
        unique_subjects = filtered_data['Subject'].value_counts().nlargest(input.top_n()).index.tolist()
        unique_subjects = [subj for subj in unique_subjects if subj not in excluded_keywords]

        # Update the choices for the keyword selector
        ui.update_selectize("selected_keywords", choices=unique_subjects, selected=[])

    @render_widget
    def comparison_plot():
        selected_keywords = input.selected_keywords()
        if not selected_keywords:
            return px.scatter(title=f"Veuillez sélectionner jusqu'à {input.top_n()} mots-clés")

        # Get the selected year range
        start_year, end_year = input.year_range()
        
        # Filter data based on the selected criteria
        filtered_data = data[(data['Date'].dt.year >= start_year) & 
                             (data['Date'].dt.year <= end_year)]
        
        if input.country() != "Tout":
            filtered_data = filtered_data[filtered_data['Country'] == input.country()]
        
        if input.newspapers():
            filtered_data = filtered_data[filtered_data['Newspaper'].isin(input.newspapers())]
        
        if input.category() != "Tout":
            filtered_data = filtered_data[filtered_data['Category'] == input.category()]
        
        # Filter for selected keywords
        keyword_data = filtered_data[filtered_data['Subject'].isin(selected_keywords)]
        
        # Group by Year and Subject, count occurrences
        grouped_data = keyword_data.groupby([keyword_data['Date'].dt.year, 'Subject']).size().reset_index(name='Count')
        grouped_data.rename(columns={grouped_data.columns[0]: 'Year'}, inplace=True)
        
        country_title = f" in {input.country()}" if input.country() != "Tout" else ""
        newspaper_title = f" ({', '.join(input.newspapers())})" if input.newspapers() else ""
        category_title = f" for {input.category()}" if input.category() != "Tout" else ""
        
        fig = px.line(grouped_data, x='Year', y='Count', color='Subject',
                      title=f'Comparaison des mots-clés sélectionnés{country_title}{newspaper_title}{category_title} ({start_year} - {end_year})')
        fig.update_layout(
            xaxis_title='Année', 
            yaxis_title='Fréquence',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="Black",
                borderwidth=1
            )
        )
        return fig

# Create and run the app
app = App(app_ui, server)