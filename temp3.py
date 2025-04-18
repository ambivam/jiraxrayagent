import requests
import json

# Define the base URL and the Authorization token
BASE_URL = 'https://xray.cloud.getxray.app/api/v2/graphql'
AUTH_TOKEN = 'Bearer YOUR_ACCESS_TOKEN_HERE'  # Replace with your token

# Headers for the requests
headers = {
    'Content-Type': 'application/json',
    'Authorization': AUTH_TOKEN
}

# Function to get the issueId based on the issue key
def get_issue_id(issue_key):
    query = f"""
    query {{
      getTests(jql: "key = '{issue_key}'", limit: 1) {{
        total
        results {{
          issueId
        }}
      }}
    }}
    """
    payload = {'query': query}
    response = requests.post(BASE_URL, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        data = response.json()
        if data.get('data') and data['data'].get('getTests') and data['data']['getTests']['results']:
            issue_id = data['data']['getTests']['results'][0]['issueId']
            return issue_id
        else:
            print(f"Issue key '{issue_key}' not found.")
            return None
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

# Function to update the Cucumber test steps (definition)
def update_cucumber_definition(issue_id, cucumber_definition):
    mutation = f"""
    mutation {{
      updateTestDefinition(issueId: "{issue_id}", definition: "{cucumber_definition.replace('"', '\\"').replace('\n', '\\n')}")
    }}
    """
    payload = {'query': mutation}
    response = requests.post(BASE_URL, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        data = response.json()
        if data.get('data') and data['data'].get('updateTestDefinition'):
            print(f"Cucumber definition for issue ID '{issue_id}' updated successfully.")
        else:
            print("Failed to update the Cucumber definition.")
    else:
        print(f"Error {response.status_code}: {response.text}")

# Example usage:
issue_key = 'XTT-241'
issue_id = get_issue_id(issue_key)

if issue_id:
    cucumber_definition = """Feature: Login functionality
  Scenario: Successful login
    Given I am on the login page
    When I enter valid credentials
    Then I should be redirected to the dashboard"""
    update_cucumber_definition(issue_id, cucumber_definition)
