import requests
import os
import json
import subprocess
import shlex
import time
from dotenv import load_dotenv

load_dotenv()

XRAY_CLIENT_ID = os.getenv("XRAY_CLIENT_ID")
XRAY_CLIENT_SECRET = os.getenv("XRAY_CLIENT_SECRET")

XRAY_API_BASE = "https://xray.cloud.getxray.app/api/v2"
BASE_URL = 'https://xray.cloud.getxray.app/api/v2/graphql'

def authenticate():
    response = requests.post(
        f"{XRAY_API_BASE}/authenticate",
        json={"client_id": XRAY_CLIENT_ID, "client_secret": XRAY_CLIENT_SECRET}
    )
    #return response.json()
    return response.text

def graphql_request(query, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    graphql_url = f"{XRAY_API_BASE}/graphql"
    try:
        response = requests.post(graphql_url, headers=headers, json={"query": query})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"GraphQL request failed: {str(e)}")
        print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
        return {"errors": [{"message": str(e)}]}
    except ValueError as e:
        print(f"JSON decode error: {str(e)}")
        print(f"Response content: {response.text}")
        return {"errors": [{"message": "Invalid JSON response"}]}

def graphql_request_with_retry(url, headers, payload, max_retries=3, delay=2):
    """Make GraphQL request with retry logic for 503 errors"""
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 503:
                if attempt < max_retries - 1:
                    print(f"503 error, retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
            return response
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"Request failed, retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            raise
    return response

def add_test_steps(issue_id, steps_payload, token):
    steps_graphql = ",".join([
        f'{{action: "{step["action"]}", data: "", result: "{step.get("result", "Expected outcome")}"}}'
        for step in steps_payload
    ])

    query = f'''
    mutation {{
        updateTest(
            issueId: "{issue_id}",
            steps: [{steps_graphql}]
        ) {{
            steps {{
                action
                data
                result
            }}
        }}
    }}
    '''
    return graphql_request(query, token)

def get_test_steps(test_key, token):
    """
    Get detailed information about test steps using GraphQL.
    
    Args:
        test_key (str): The Jira key of the test (e.g., XTT-20)
        token (str): Authentication token for Xray API
        
    Returns:
        Response object with test steps and related information
    """
    query = f'''
    query {{
      getTest(issueId: "{test_key}") {{
        issueId
        testType {{
          name
          kind
        }}
        steps {{
          id
          action
          data
          result
          attachments {{
            id
            filename
          }}
        }}
        jira(fields: ["key", "summary", "description", "priority", "status"]) 
      }}
    }}
    '''
    return graphql_request(query, token)

def delete_test_steps(test_key, token):
    query = f'''
    mutation {{
      updateTest(
        issueId: "{test_key}",
        steps: []
      ) {{
        test {{
          issueId
          steps {{
            action
            data
            result
          }}
        }}
      }}
    }}
    '''
    return graphql_request(query, token)

def get_issue_id_direct(test_key: str, token: str) -> str:
    """Get issue ID using a direct GraphQL query with the exact format from the successful curl command"""
    try:
        # This is the exact query format that worked in the curl command
        url = f"{XRAY_API_BASE}/graphql"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Create the exact payload format that worked in the curl command
        payload = {
            "query": f"query {{ getTests(jql: \"key = {test_key}\", limit: 1) {{ results {{ issueId }} }} }}"
        }
        
        print(f"Sending GraphQL query for key {test_key}")
        print(f"Payload: {json.dumps(payload)}")
        
        # Make the request
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        response_text = response.text
        print(f"Response text: {response_text[:200]}..." if len(response_text) > 200 else response_text)
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]["getTests"]["results"]:
                issue_id = data["data"]["getTests"]["results"][0]["issueId"]
                print(f"Successfully retrieved issue ID: {issue_id} for key: {test_key}")
                return issue_id
            else:
                print(f"No results found in response for key: {test_key}")
                print(f"Full response: {json.dumps(data)}")
        else:
            print(f"Error response: {response.status_code} - {response.text}")
        
        return None
    except Exception as e:
        print(f"Error in GraphQL query: {str(e)}")
        return None

def get_issue_id_from_key(test_key: str, token: str) -> str:
    """Get numeric issueId using the test key"""
    query = {"query": f"""query {{ getTests(jql: "key = {test_key}", limit: 1) {{ results {{ issueId }} }} }}"""}
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = graphql_request_with_retry(f"{XRAY_API_BASE}/graphql", headers, query)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("getTests", {}).get("results", [{}])[0].get("issueId")
        return None
    except Exception as e:
        print(f"Error getting issue ID: {str(e)}")
        return None

# Build Cucumber steps
def build_gherkin(scenario):
    gherkin = f"  Scenario: {scenario['title']}\n"    
    for step in scenario['steps']:
        gherkin += f"    {step}\n"
    return gherkin

# Function to get the issueId based on the issue key
def get_issue_id(issue_key: str, token: str) -> str:
    print("INTO get_issue_id")
    token = token.strip('"') 
    headers = {
        "Authorization": f'Bearer {token}',
        "Content-Type": "application/json"
    }

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
    print("THE TOKEN USED IS :",token)
    print("THE HEADERS ARE :",headers)
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

# Function to update the test type to "Cucumber" based on the issueId
def update_test_type_to_cucumber(issue_id,token):
    print( "****************************INTO update_test_type_to_cucumber****************************")
    result = False
    token = token.strip('"') 
    headers = {
        "Authorization": f'Bearer {token}',
        "Content-Type": "application/json"
    }

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
            result = True
            print(f"Test type for issue ID '{issue_id}' updated to Cucumber successfully.")
        else:
            print("Failed to update the test type.")
            result = False
    else:
        print(f"Error {response.status_code}: {response.text}")
        result = False
    return result


def get_multiple_issue_ids(test_keys: list, token: str) -> dict:
    """Get numeric issueIds for multiple test keys in a single query
    
    Args:
        test_keys (list): List of Jira test keys (e.g., ['XTT-1', 'XTT-2'])
        token (str): Authentication token for Xray API
        
    Returns:
        dict: Dictionary mapping test keys to their issueIds
    """
    if not test_keys:
        return {}
    
    # Process each key individually using the successful method
    # This is more reliable than trying to batch them together
    result_map = {}
    for test_key in test_keys:
        try:
            print(f"\n{'='*50}\nProcessing test key: {test_key}\n{'='*50}")
            issue_id = get_issue_id_from_key(test_key, token)
            if issue_id:
                result_map[test_key] = issue_id
                print(f"Added {test_key} -> {issue_id} to result map")
            else:
                print(f"Failed to get issue ID for {test_key}")
        except Exception as e:
            print(f"Error processing key {test_key}: {str(e)}")
    
    print(f"\nFinal result map: {result_map}")
    return result_map

def set_cucumber_type(issue_id: str, token: str):
    """Set test type to Cucumber using numeric issueId"""
    query = {"query": f"""mutation {{ updateTestType(issueId: "{issue_id}", testType: {{ name: "Cucumber" }}) {{ testType {{ name }} }} }}"""}
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(f"{XRAY_API_BASE}/graphql", headers=headers, json=query)
        return response.status_code == 200 and "errors" not in response.json()
    except Exception as e:
        print(f"Error setting Cucumber type: {str(e)}")
        return False

def set_multiple_cucumber_types(issue_ids: list, token: str) -> dict:
    """Set test type to Cucumber for multiple tests
    
    Args:
        issue_ids (list): List of numeric issue IDs
        token (str): Authentication token for Xray API
        
    Returns:
        dict: Dictionary mapping issue IDs to success status
    """
    results = {}
    
    for issue_id in issue_ids:
        try:
            success = set_cucumber_type(issue_id, token)
            results[issue_id] = success
        except Exception as e:
            print(f"Error setting Cucumber type for {issue_id}: {str(e)}")
            results[issue_id] = False
    
    return results

def setup_test(test_key: str, token: str):
    """Complete test setup: get ID and set Cucumber type"""
    issue_id = get_issue_id_from_key(test_key, token)
    if issue_id:
        type_response = set_cucumber_type(issue_id, token)
        if type_response:
            return {"success": True, "issue_id": issue_id}
    return {"success": False, "message": "Failed to setup test"}


def get_issue_id_by_key(test_key, token):
    query = f'''
    query {{
      getTests(jql: "key = {test_key}", limit: 1) {{
        results {{
          issueId
        }}
      }}
    }}
    '''
    json_data = graphql_request(query, token)

    if json_data is None:
        print("❌ No response from GraphQL API.")
        return None

    if "errors" in json_data:
        print("❌ GraphQL returned errors:", json_data["errors"])
        return None

    results = json_data['data']['getTests']['results']
    if not results:
        print("❌ No test found with key", test_key)
        return None

    issue_id = results[0]['issueId']
    return issue_id


# Function to get the test type (kind and name)
def get_test_type(issue_id,token):
    print("************************************INTO get_test_type*********************************")
    token = token.strip('"') 
    headers = {
        "Authorization": f'Bearer {token}',
        "Content-Type": "application/json"
    }
    
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


# Function to update the Gherkin steps
def update_gherkin_steps(issue_id, gherkin_steps,token):
    print("************************************INTO update_gherkin_steps*********************************")
    token = token.strip('"') 
    headers = {
        "Authorization": f'Bearer {token}',
        "Content-Type": "application/json"
    }

    # Escape newlines for GraphQL string
    #gherkin_steps_escaped = gherkin_steps.replace("\n", "\\n")
    #gherkin_steps_escaped = gherkin_steps.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
    gherkin_steps_escaped = json.dumps(gherkin_steps)

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
def update_gherkin_for_issue(issue_key, gherkin_steps,token):
    print("INTO update_gherkin_for_issue")
    issue_id = get_issue_id(issue_key,token)
    print("THE ISSUE ID IS:", issue_id)
    if not issue_id:
        return
    
    if issue_id:
        update_test_type_to_cucumber(issue_id,token)

    kind, name = get_test_type(issue_id,token)
    if kind != "Gherkin":
        print(f"Cannot update: Test type is '{name}' (kind: {kind}) — must be 'Cucumber' (gherkin)!")
        return

    update_gherkin_steps(issue_id, gherkin_steps,token)

