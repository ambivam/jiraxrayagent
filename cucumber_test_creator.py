import os
import time
from xray_client import authenticate, get_issue_id_from_key, set_cucumber_type, add_test_steps
from jira_client import create_issue

def create_cucumber_test(scenario, token):
    """Create a test in JIRA and set it up as a Cucumber test"""
    # Create JIRA test issue
    payload = {
        "fields": {
            "project": {"key": os.getenv("JIRA_PROJECT_KEY")},
            "summary": scenario['title'],
            "description": "Cucumber test created from feature file",
            "issuetype": {"name": "Test"}
        }
    }
    
    response = create_issue(payload)
    if response.status_code != 201:
        return None, f"Failed to create issue: {response.text}"
        
    issue_key = response.json()['key']
    
    # Get issue ID with retry
    for attempt in range(3):
        issue_id = get_issue_id_from_key(issue_key, token)
        if issue_id:
            break
        print(f"Retrying to get issue ID... (attempt {attempt + 1}/3)")
        time.sleep(2)
    
    if not issue_id:
        return None, f"Failed to get issue ID for {issue_key} after retries"
    
    # Set test type to Cucumber
    if not set_cucumber_type(issue_id, token):
        return None, f"Failed to set Cucumber type for {issue_key}"
    
    # Add steps
    steps = [{"action": step, "result": "Expected outcome"} for step in scenario['steps']]
    step_response = add_test_steps(issue_id, steps, token)
    
    if "errors" in step_response:
        return None, f"Failed to add steps for {issue_key}"
        
    return issue_key, None
