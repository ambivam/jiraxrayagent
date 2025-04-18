import requests
import json
from typing import List, Dict, Optional

class CucumberTestManager:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth_token}'
        }

    def get_issue_id(self, issue_key: str) -> Optional[str]:
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
        print(f"Sending query: {json.dumps(payload)}")
        response = requests.post(self.base_url, headers=self.headers, data=json.dumps(payload))

        if response.status_code == 200:
            data = response.json()
            if data.get('data') and data['data'].get('getTests') and data['data']['getTests'].get('results'):
                return data['data']['getTests']['results'][0]['issueId']
        print(f"Response: {response.text}")
        return None

    def set_cucumber_type(self, issue_id: str) -> bool:
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
        response = requests.post(self.base_url, headers=self.headers, data=json.dumps(payload))
        return response.status_code == 200

    def add_steps(self, issue_id: str, steps: List[Dict[str, str]]) -> bool:
        steps_data = ",".join([
            f'{{action: "{step["action"]}", data: "", result: "{step.get("result", "Expected result")}"}}'
            for step in steps
        ])
        
        mutation = {
            'query': f'''
            mutation {{
              updateTest(issueId: "{issue_id}", steps: [{steps_data}]) {{
                steps {{ action result }}
              }}
            }}
            '''
        }
        
        response = requests.post(self.base_url, headers=self.headers, json=mutation)
        return response.status_code == 200

    def update_test_with_steps(self, issue_key: str, steps: List[Dict[str, str]]) -> bool:
        """Main method to update test type and add steps"""
        issue_id = self.get_issue_id(issue_key)
        if not issue_id:
            print(f"❌ Could not find issue ID for {issue_key}")
            return False
            
        if not self.set_cucumber_type(issue_id):
            print(f"❌ Failed to set Cucumber type for {issue_key}")
            return False
            
        if not self.add_steps(issue_id, steps):
            print(f"❌ Failed to add steps for {issue_key}")
            return False
            
        print(f"✅ Successfully updated {issue_key} with {len(steps)} steps")
        return True
