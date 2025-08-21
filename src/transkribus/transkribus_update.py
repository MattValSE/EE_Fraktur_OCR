import os
import requests
import json
import time
from dotenv import load_dotenv

# Load username and password from a .env file
load_dotenv()

USERNAME = os.getenv("API_USERNAME")
PASSWORD = os.getenv("API_PASSWORD")

#print("Username:", USERNAME)
#print("Password:", PASSWORD)

TOKEN_FILE = "token.json"

def authenticate():
    """Authenticate and get a new access token"""
    url = "https://account.readcoop.eu/auth/realms/readcoop/protocol/openid-connect/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    print("data...")
    data = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "client_id": "transkribus-api-client"
    }
    print("Authenticating...")
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        tokens = response.json()
        # Add a custom 'expires_at' field
        tokens['expires_at'] = time.time() + tokens.get('expires_in', 3600) - 60  # 60 sec early
        # Save to file
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        return tokens["access_token"]
    else:
        print("Authentication failed:", response.status_code)
        print(response.text)
        raise Exception("Failed to authenticate")

def get_access_token():
    """Load existing token or authenticate if needed"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            tokens = json.load(f)
            if tokens.get("expires_at", 0) > time.time():
                return tokens["access_token"]
            else:
                print("Access token expired, refreshing...")
    else:
        print("No access token found, authenticating...")
    return authenticate()

def update_transcription(collection_id, doc_id, page_nr, page_xml_path, status="IN_PROGRESS", overwrite=False):
    """
    Update a PAGE XML file for a document page in Transkribus.

    Args:
        collection_id (str): The collection ID.
        doc_id (str): The document ID.
        page_nr (int): The page number.
        page_xml_path (str): Path to the PAGE XML file to upload.
        status (str): The edit status (e.g., NEW, IN_PROGRESS, DONE, FINAL).
        overwrite (bool): Whether to overwrite the recent version.
    """
    url = f"https://transkribus.eu/TrpServer/rest/collections/{collection_id}/{doc_id}/{page_nr}/text"
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/xml"
    }
    params = {
        "status": status,
        "overwrite": str(overwrite).lower()  # Convert boolean to "true" or "false"
    }

    # Read the PAGE XML file
    with open(page_xml_path, "r", encoding="utf-8") as file:
        page_xml_content = file.read()

    print(f"Uploading PAGE XML for page {page_nr} in document {doc_id} (collection {collection_id})...")
    response = requests.post(url, headers=headers, params=params, data=page_xml_content.encode('utf-8'))

    if response.status_code == 200:
        print(f"Successfully updated transcription for page {page_nr}.")
    else:
        print(f"Failed to update transcription: {response.status_code}")
        print(response.text)

# Usage example:
access_token = get_access_token()
#print("Access token:", access_token)
# Now you can use it
headers = {
    "Authorization": f"Bearer {access_token}"
}

with open("src/data/transkribus.csv", "r") as f:
    lines = f.readlines()
    for line in lines[1:]:
        elements = line.strip().split(",")
        if int(elements[3]) >= 50:
            #print(elements)
        
            collection_id = ""  # Replace with your collection ID
            doc_id = elements[2]      # Replace with your document ID
            page_nr = elements[1]              # Replace with the page number you want to update
            page_xml_path = f"src/datasets/bronze/scanned/{elements[0]}/transkribus/page.xml"  # Replace with the path to your PAGE XML file
            status = "FINAL"     # Edit status (e.g., NEW, IN_PROGRESS, DONE, FINAL)
            overwrite = True           # Whether to overwrite the recent version
            update_transcription(collection_id, doc_id, page_nr, page_xml_path, status, overwrite)
        else:
            collection_id = ""  # Replace with your collection ID
            doc_id = elements[2]      # Replace with your document ID
            page_nr = elements[1]              # Replace with the page number you want to update
            page_xml_path = f"src/datasets/bronze/scanned/{elements[0]}/transkribus/page.xml"  # Replace with the path to your PAGE XML file
            status = "IN_PROGRESS"     # Edit status (e.g., NEW, IN_PROGRESS, DONE, FINAL)
            overwrite = True           # Whether to overwrite the recent version
            update_transcription(collection_id, doc_id, page_nr, page_xml_path, status, overwrite)




        
        
            

#response = requests.get("POST https://transkribus.eu/TrpServer/rest/collections/2014515/8115992/1/text", headers=headers)
#print(response.status_code, response.text)
