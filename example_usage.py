from cucumber_manager import CucumberTestManager
from xray_client import authenticate
from dotenv import load_dotenv
import os

load_dotenv()

def update_test_with_cucumber_steps(issue_key: str, steps: list):
    token = authenticate()
    print(f"Authenticating with Xray... Token length: {len(token)}")
    
    manager = CucumberTestManager(
        base_url='https://xray.cloud.getxray.app/api/v2/graphql',
        auth_token=token
    )
    
    issue_id = manager.get_issue_id(issue_key)
    if not issue_id:
        print(f"Failed to find issue {issue_key}")
        return False
    
    print(f"Found issue ID: {issue_id}")
    
    # Process steps and update directly using issue_id
    scenario_steps = [{"action": step, "result": "Expected outcome"} for step in steps]
    success = manager.add_steps(issue_id, scenario_steps)
    
    if success:
        print(f"✅ Updated {issue_key} with {len(steps)} steps")
    else:
        print(f"❌ Failed to update {issue_key}")
    
    return success

# Example usage:
if __name__ == "__main__":
    test_key = "XTT-243"
    test_steps = [
        "Given I am on the todo application",
        "When I enter a new todo item",
        "Then I should see the item in the list"
    ]
    
    success = update_test_with_cucumber_steps(test_key, test_steps)
    if not success:
        print("Failed to update test. Check the logs above for details.")
