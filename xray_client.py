import requests
import os
from dotenv import load_dotenv

load_dotenv()

XRAY_CLIENT_ID = os.getenv("XRAY_CLIENT_ID")
XRAY_CLIENT_SECRET = os.getenv("XRAY_CLIENT_SECRET")

XRAY_API_BASE = "https://xray.cloud.getxray.app/api/v2"

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
    response = requests.post(graphql_url, headers=headers, json={"query": query})
    return response

def add_test_steps(test_key, steps_payload, token):
    steps_graphql = ",".join([
        f'{{ action: "{step["action"]}", data: "{step.get("data", "")}", result: "{step["result"]}" }}'
        for step in steps_payload
    ])

    query = f'''
    mutation {{
      updateTest(
        issueId: "{test_key}",
        steps: [{steps_graphql}]
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

def get_test_by_key(test_key, token):
    """
    Get detailed information about a specific test by its key using GraphQL.
    
    Args:
        test_key (str): The Jira key of the test (e.g., XTT-20)
        token (str): Authentication token for Xray API
        
    Returns:
        Response object with test details including steps, type, and Jira fields
    """
    query = f'''
    query {{
      getTests(jql: "key = {test_key}", limit: 1) {{
        results {{
          issueId
          testType {{
            name
            kind
          }}
          steps {{
            id
            data
            action
            result
            attachments {{
              id
              filename
            }}
          }}
          jira(fields: ["key", "summary", "description", "priority", "status"]) 
        }}
      }}
    }}
    '''
    return graphql_request(query, token)

