import requests
import pandas as pd
import json
from tqdm.auto import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Function to fetch data from a single item set
def fetch_data(api_url, item_set_id, api_key, api_identity):
    page = 1
    items = []
    while True:
        response = requests.get(
            f"{api_url}/items",
            params={"item_set_id": item_set_id, "page": page},
            headers={"X-Api-Key": api_key, "X-Api-Identity": api_identity}
        )
        data = response.json()
        if data:
            items.extend(data)
            page += 1
        else:
            break
    return items

# Function to fetch and process data for all item sets in a country
def fetch_and_process_data(api_url, item_sets, api_key, api_identity):
    all_items = []
    # Use ThreadPoolExecutor to parallelize requests
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_id = {executor.submit(fetch_data, api_url, id, api_key, api_identity): id for id in item_sets}
        for future in tqdm(as_completed(future_to_id), total=len(item_sets), desc="Fetching data"):
            all_items.extend(future.result())
    
    # Process items to extract subjects and date
    processed_data = []
    for item in tqdm(all_items, desc="Processing items"):
        subjects = [sub['display_title'] for sub in item.get('dcterms:subject', []) if sub.get('display_title')]
        date = item.get('dcterms:date', [{}])[0].get('@value')
        for subject in subjects:
            processed_data.append({
                'Subject': subject,
                'Date': date,  # Keep as string for JSON serialization
                'Country': item.get('country', '')  # Assuming there's a 'country' field in the API response
            })
    
    return processed_data

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

    all_data = []
    for country, item_sets in country_item_sets.items():
        print(f"Processing data for {country}...")
        country_data = fetch_and_process_data(api_url, item_sets, api_key, api_identity)
        all_data.extend(country_data)
        print(f"Processed {len(country_data)} items for {country}")

    # Save all data to a single JSON file
    with open("preprocessed_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print("Data processing complete. Results saved to preprocessed_data.json")