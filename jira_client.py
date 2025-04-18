import os
import base64
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

JIRA_URL = os.getenv("JIRA_BASE_URL")
JIRA_USER = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)

def get_basic_auth():
    auth_str = f"{os.getenv('JIRA_EMAIL')}:{os.getenv('JIRA_API_TOKEN')}"
    return base64.b64encode(auth_str.encode()).decode()

def create_issue(payload):
    try:
        url = f"{os.getenv('JIRA_BASE_URL')}/rest/api/3/issue"
        headers = {
            "Authorization": f"Basic {get_basic_auth()}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        print(f"Making request to JIRA: {url}")
        print(f"Using auth: {headers['Authorization'][:20]}...")
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 401:
            print("Authentication failed. Please check JIRA credentials.")
        elif response.status_code not in [200, 201]:
            print(f"JIRA error: {response.status_code} - {response.text}")
        
        return response
        
    except Exception as e:
        print(f"Error creating JIRA issue: {str(e)}")
        raise

def update_issue(issue_key, payload):
    response = requests.put(f"{JIRA_URL}/rest/api/3/issue/{issue_key}", headers=headers, auth=auth, json=payload)
    return response

def get_issue(issue_key):
    response = requests.get(f"{JIRA_URL}/rest/api/3/issue/{issue_key}", headers=headers, auth=auth)
    return response

def delete_issue(issue_key):
    response = requests.delete(f"{JIRA_URL}/rest/api/3/issue/{issue_key}", headers=headers, auth=auth)
    return response

def debug_jira_issue(issue_key):
    response = requests.get(f"{JIRA_URL}/rest/api/3/issue/{issue_key}", headers=headers, auth=auth)
    return response
