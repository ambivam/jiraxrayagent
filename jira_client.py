import requests
from requests.auth import HTTPBasicAuth
import os
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


def create_issue(payload):
    response = requests.post(f"{JIRA_URL}/rest/api/3/issue", headers=headers, auth=auth, json=payload)
    return response

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
