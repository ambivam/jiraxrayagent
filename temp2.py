import requests
import json

# Define the base URL and the Authorization token
BASE_URL = 'https://xray.cloud.getxray.app/api/v2/graphql'
AUTH_TOKEN = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnQiOiIwYmQxNThkNC1kY2QzLTM5OTMtOTFjYy03OTdhMGI5MDA2MTYiLCJhY2NvdW50SWQiOiI3MTIwMjA6ODRlMDEyZjEtNzZkZC00Y2ZhLTkxNmMtNjE3MGNjZDQ4NDFhIiwiaXNYZWEiOmZhbHNlLCJpYXQiOjE3NDQ5NDcxMTAsImV4cCI6MTc0NTAzMzUxMCwiYXVkIjoiMzAxODQ3QjNFQzY4NEU0QUFCREYwQzIwQjYxOUEzMzMiLCJpc3MiOiJjb20ueHBhbmRpdC5wbHVnaW5zLnhyYXkiLCJzdWIiOiIzMDE4NDdCM0VDNjg0RTRBQUJERjBDMjBCNjE5QTMzMyJ9.dl4ygTNMVUCoivmH33O2_IStTlFPR6OAEO_qlG30fcQ'

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

# Function to update the test type to "Cucumber" based on the issueId
def update_test_type_to_cucumber(issue_id):
    mutation = f"""
    mutation {{
      updateTestType(issueId: "{issue_id}", testType: {{name: "Cucumber"}}) {{
        issueId
        testType {{
          name
        }}
      }}
    }}
    """

    payload = {'query': mutation}
    response = requests.post(BASE_URL, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        data = response.json()
        if data.get('data') and data['data'].get('updateTestType'):
            print(f"Test type for issue ID '{issue_id}' updated to Cucumber successfully.")
        else:
            print("Failed to update the test type.")
    else:
        print(f"Error {response.status_code}: {response.text}")

# Example usage:
issue_key = 'XTT-239'
issue_id = get_issue_id(issue_key)
print(f"Issue ID: {issue_id}")

if issue_id:
    update_test_type_to_cucumber(issue_id)
