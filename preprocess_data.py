import requests
import pandas as pd
import json
from tqdm.auto import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Function to fetch all pages from an API endpoint
def fetch_all_pages(api_url, params, headers):
    all_items = []
    page = 1
    while True:
        params['page'] = page
        response = requests.get(api_url, params=params, headers=headers)
        data = response.json()
        if not data:
            break
        all_items.extend(data)
        page += 1
    return all_items

# Function to fetch data from a single item set
def fetch_data(api_url, item_set_id, api_key, api_identity):
    params = {"item_set_id": item_set_id}
    headers = {"X-Api-Key": api_key, "X-Api-Identity": api_identity}
    return fetch_all_pages(f"{api_url}/items", params, headers)

# Function to fetch and process data for all item sets in a country
def fetch_and_process_data(api_url, item_sets, api_key, api_identity):
    all_items = []
    # Use ThreadPoolExecutor to parallelize requests
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_id = {executor.submit(fetch_data, api_url, id, api_key, api_identity): id for id in item_sets}
        for future in tqdm(as_completed(future_to_id), total=len(item_sets), desc="Fetching data"):
            all_items.extend(future.result())
    
    # Process items to extract subjects, date, newspaper, and country
    processed_data = []
    for item in tqdm(all_items, desc="Processing items"):
        subjects = []
        for sub in item.get('dcterms:subject', []):
            subject_info = {
                'display_title': sub.get('display_title') or sub.get('@value'),
                'value_resource_id': sub.get('value_resource_id')
            }
            subjects.append(subject_info)
        
        date = item.get('dcterms:date', [{}])[0].get('@value')
        newspaper = item.get('dcterms:publisher', [{}])[0].get('display_title', '')
        item_set_id = item.get('o:item_set', [{}])[0].get('o:id', '')
        country = item_set_to_country.get(str(item_set_id), '')
        
        for subject in subjects:
            processed_data.append({
                'Subject': subject['display_title'],
                'value_resource_id': subject['value_resource_id'],
                'Date': date,
                'Country': country,
                'Newspaper': newspaper
            })
    
    return processed_data

# Function to fetch category mappings
def fetch_category_mappings(api_url, item_set_id, api_key, api_identity):
    params = {"item_set_id": item_set_id}
    headers = {"X-Api-Key": api_key, "X-Api-Identity": api_identity}
    items = fetch_all_pages(f"{api_url}/items", params, headers)
    return {str(item['o:id']): item['dcterms:title'][0]['@value'] for item in items if 'dcterms:title' in item}

# Main execution
if __name__ == "__main__":
    api_url = "https://iwac.frederickmadore.com/api"
    api_key = os.getenv("OMEKA_API_KEY")
    api_identity = os.getenv("OMEKA_API_IDENTITY")
    
    country_item_sets = {
        "Bénin": ["2187", "2188", "2189"],
        "Burkina Faso": ["2200", "2215", "2214", "2207", "2201"],
        "Togo": ["5498", "5499"]
    }

    item_set_to_country = {item_set: country for country, item_sets in country_item_sets.items() for item_set in item_sets}

    # Fetch category mappings
    print("Fetching category mappings...")
    associations = fetch_category_mappings(api_url, "854", api_key, api_identity)
    emplacements = fetch_category_mappings(api_url, "268", api_key, api_identity)
    evenements = fetch_category_mappings(api_url, "2", api_key, api_identity)
    sujets = fetch_category_mappings(api_url, "1", api_key, api_identity)
    individus = fetch_category_mappings(api_url, "266", api_key, api_identity)

    all_data = []
    for country, item_sets in country_item_sets.items():
        print(f"Processing data for {country}...")
        country_data = fetch_and_process_data(api_url, item_sets, api_key, api_identity)
        all_data.extend(country_data)
        print(f"Processed {len(country_data)} items for {country}")

    # Map value_resource_id to categories
    for item in tqdm(all_data, desc="Mapping categories"):
        value_resource_id = str(item['value_resource_id'])
        if value_resource_id in associations:
            item['Category'] = 'Association'
        elif value_resource_id in emplacements:
            item['Category'] = 'Emplacement'
        elif value_resource_id in evenements:
            item['Category'] = 'Évènement'
        elif value_resource_id in sujets:
            item['Category'] = 'Sujet'
        elif value_resource_id in individus:
            item['Category'] = 'Individu'
        else:
            item['Category'] = None
        
        # Remove the value_resource_id from the final output
        del item['value_resource_id']

    # Save all data to a single JSON file
    with open("preprocessed_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print("Data processing complete. Results saved to preprocessed_data.json")