import requests
import json
from xray_client import authenticate

# Define the base URL and get the Authorization token
BASE_URL = 'https://xray.cloud.getxray.app/api/v2/graphql'
#AUTH_TOKEN = f'Bearer {authenticate()}'
AUTH_TOKEN = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnQiOiIwYmQxNThkNC1kY2QzLTM5OTMtOTFjYy03OTdhMGI5MDA2MTYiLCJhY2NvdW50SWQiOiI3MTIwMjA6ODRlMDEyZjEtNzZkZC00Y2ZhLTkxNmMtNjE3MGNjZDQ4NDFhIiwiaXNYZWEiOmZhbHNlLCJpYXQiOjE3NDQ5NDcxMTAsImV4cCI6MTc0NTAzMzUxMCwiYXVkIjoiMzAxODQ3QjNFQzY4NEU0QUFCREYwQzIwQjYxOUEzMzMiLCJpc3MiOiJjb20ueHBhbmRpdC5wbHVnaW5zLnhyYXkiLCJzdWIiOiIzMDE4NDdCM0VDNjg0RTRBQUJERjBDMjBCNjE5QTMzMyJ9.dl4ygTNMVUCoivmH33O2_IStTlFPR6OAEO_qlG30fcQ'

print(f"Authentication token length: {len(AUTH_TOKEN)}")

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
    print("THE RESPONSE IS FROM GET ISSUE ID:",response.text)

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


# Function to get the test type (kind and name)
def get_test_type(issue_id):
    query = f"""
    query {{
      getTest(issueId: "{issue_id}") {{
        testType {{
          kind
          name
        }}
      }}
    }}
    """
    payload = {'query': query}
    response = requests.post(BASE_URL, headers=headers, json=payload)
    print("THE RESPONSE IS FROM GET TEST TYPE:",response.text)

    if response.status_code == 200:
        data = response.json()
        test_type = data.get('data', {}).get('getTest', {}).get('testType')
        if test_type:
            return test_type['kind'], test_type['name']
        else:
            print(f"Could not determine test type for issue ID '{issue_id}'.")
            return None, None
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None, None
    
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

# Function to update the Gherkin steps
def update_gherkin_steps(issue_id, gherkin_steps):
    # Escape newlines for GraphQL string
    gherkin_steps_escaped = gherkin_steps.replace("\n", "\\n")
    mutation = f"""
    mutation {{
      updateGherkinTestDefinition(
        issueId: "{issue_id}",
        gherkin: "{gherkin_steps_escaped}"
      ) {{
        issueId
      }}
    }}
    """
    payload = {'query': mutation}
    response = requests.post(BASE_URL, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        if 'errors' in data:
            print("Mutation failed with errors:", json.dumps(data['errors'], indent=2))
        else:
            print(f"Gherkin steps for issue ID '{issue_id}' updated successfully.")
    else:
        print(f"Error {response.status_code}: {response.text}")

# Combined function to safely update Gherkin steps by issue key
def update_gherkin_for_issue(issue_key, gherkin_steps):
    issue_id = get_issue_id(issue_key)
    print("THE ISSUE ID IS:", issue_id)
    if not issue_id:
        return
    
    if issue_id:
        update_test_type_to_cucumber(issue_id)

    kind, name = get_test_type(issue_id)
    if kind != "Gherkin":
        print(f"Cannot update: Test type is '{name}' (kind: {kind}) — must be 'Cucumber' (gherkin)!")
        return

    update_gherkin_steps(issue_id, gherkin_steps)

# Example usage:
issue_key = 'XTT-235'
gherkin_steps = """Feature: Sample Feature
  Scenario: Example scenario
    Given a starting state
    When an action occurs
    Then an expected result is seen"""

update_gherkin_for_issue(issue_key, gherkin_steps)
