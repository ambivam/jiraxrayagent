import os
import re
import json
import time
from dotenv import load_dotenv
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain.tools import BaseTool
from langchain.prompts import MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
import requests
from jira_client import create_issue
from xray_client import authenticate, add_test_steps, get_issue_id_from_key, set_cucumber_type, get_multiple_issue_ids, set_multiple_cucumber_types

# Load environment variables
load_dotenv()

# Function to parse Gherkin feature files
def parse_feature_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    scenarios = re.findall(r'Scenario:(.*?)(?=Scenario:|$)', content, re.DOTALL)
    parsed_scenarios = []
    for s in scenarios:
        lines = [line.strip() for line in s.strip().splitlines() if line.strip()]
        title = lines[0]
        steps = lines[1:]
        parsed_scenarios.append({'title': title, 'steps': steps})

    return parsed_scenarios

# Function to create Atlassian Document Format (ADF) description
def create_adf_paragraph(message):
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "text": message,
                        "type": "text"
                    }
                ]
            }
        ]
    }

# LangChain Tool to create a test in JIRA and add Xray test steps
class CreateJiraTestTool(BaseTool):
    name: str = "create_jira_test"
    description: str = "Creates a new test issue in JIRA, sets its test type, and adds scenario steps as Xray test steps"

    def _run(self, feature_file_path: str):
        scenarios = parse_feature_file(feature_file_path)
        token = authenticate()
        print(f"Authenticated with token length: {len(token)}")

        # Step 1: Create all JIRA issues first
        created_issues = []
        failed_scenarios = []
        
        print(f"Creating {len(scenarios)} JIRA test issues...")
        for scenario in scenarios:
            try:
                # Create JIRA issue with retry
                for attempt in range(3):
                    try:
                        payload = {
                            "fields": {
                                "project": {"key": os.getenv("JIRA_PROJECT_KEY")},
                                "summary": scenario['title'],
                                "description": create_adf_paragraph("Created by LangChain agent"),
                                "issuetype": {"name": "Test"}
                            }
                        }
                        response = create_issue(payload)
                        if response.status_code == 201:
                            break
                        print(f"Attempt {attempt + 1}: Status {response.status_code}")
                        time.sleep(2)
                    except Exception as e:
                        print(f"Attempt {attempt + 1} failed: {str(e)}")
                        if attempt == 2:
                            raise

                issue_data = response.json() if response.status_code == 201 else None
                issue_key = issue_data.get('key') if issue_data else None

                if issue_key:
                    print(f"Created issue: {issue_key}")
                    created_issues.append({
                        "key": issue_key,
                        "scenario": scenario
                    })
                else:
                    failed_scenarios.append(scenario['title'])
                    print(f"Failed to create issue for scenario: {scenario['title']}")

            except Exception as e:
                print(f"Error creating issue for scenario: {str(e)}")
                failed_scenarios.append(scenario['title'])
        
        # Add a significant delay to ensure all issues are created and indexed in JIRA
        print(f"Waiting for JIRA to process the created issues...")
        wait_time = 30  # Increased to 30 seconds to ensure JIRA has time to process
        print(f"Waiting {wait_time} seconds for JIRA indexing...")
        time.sleep(wait_time)
        
        # Step 2: Get all issue IDs in a single batch request
        if not created_issues:
            return "❌ No issues were created successfully."
            
        test_keys = [issue["key"] for issue in created_issues]
        print(f"Getting issue IDs for {len(test_keys)} tests...")
        
        # Add additional delay before fetching issue IDs to ensure they're available
        print("Waiting additional time before fetching issue IDs...")
        time.sleep(20)  # Additional 20 second delay before fetching IDs
        
        # Refresh the token to ensure it's valid
        print("Refreshing authentication token...")
        token = authenticate()
        print(f"Token refreshed, new token length: {len(token)}")
        
        # Implement retry mechanism for fetching issue IDs
        max_retries = 5  # Increased to 5 retries
        retry_delay = 15  # Increased to 15 seconds
        issue_id_map = {}
        
        for attempt in range(max_retries):
            print(f"Attempt {attempt + 1}/{max_retries} to fetch issue IDs...")
            issue_id_map = get_multiple_issue_ids(test_keys, token)
            
            if issue_id_map and len(issue_id_map) == len(test_keys):
                print(f"Successfully retrieved all {len(issue_id_map)} issue IDs")
                break
            elif issue_id_map:
                print(f"Retrieved {len(issue_id_map)}/{len(test_keys)} issue IDs, retrying for missing ones...")
                # Only retry for keys that weren't found
                test_keys = [key for key in test_keys if key not in issue_id_map]
            else:
                print(f"Failed to retrieve any issue IDs, retrying...")
            
            if attempt < max_retries - 1:
                # If we're still failing after multiple attempts, refresh the token again
                if attempt >= 2:
                    print("Refreshing authentication token again...")
                    token = authenticate()
                    print(f"Token refreshed, new token length: {len(token)}")
                
                print(f"Waiting {retry_delay} seconds before next attempt...")
                time.sleep(retry_delay)
        
        if not issue_id_map:
            return "❌ Failed to retrieve issue IDs for the created tests."
            
        print(f"Retrieved {len(issue_id_map)} issue IDs")
        
        # Step 3: Set Cucumber type for all tests
        issue_ids = list(issue_id_map.values())
        print(f"Setting Cucumber type for {len(issue_ids)} tests...")
        
        cucumber_results = set_multiple_cucumber_types(issue_ids, token)
        
        # Step 4: Add steps to each test
        results = []
        for issue in created_issues:
            key = issue["key"]
            scenario = issue["scenario"]
            
            if key not in issue_id_map:
                results.append(f"❌ Could not find issue ID for {key}")
                continue
                
            issue_id = issue_id_map[key]
            
            # Check if Cucumber type was set successfully
            if not cucumber_results.get(issue_id, False):
                results.append(f"❌ Failed to set Cucumber type for {key}")
                continue
                
            # Add steps
            steps = [{"action": step, "result": "Expected outcome"} for step in scenario['steps']]
            steps_response = add_test_steps(issue_id, steps, token)
            
            if "errors" in steps_response:
                results.append(f"❌ Failed to add steps for {key}")
            else:
                results.append(f"✅ Created {key} (ID: {issue_id}) with {len(steps)} steps as Cucumber test")
        
        # Add failed scenarios to results
        for title in failed_scenarios:
            results.append(f"❌ Failed to create issue for scenario: {title}")
            
        return "\n".join(results)

    def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async not supported")

# Setup LangChain agent
llm = ChatOpenAI(
    model_name="gpt-4",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

tools = [CreateJiraTestTool()]

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

agent = initialize_agent(
    tools,
    llm,
    agent="chat-conversational-react-description",
    memory=memory,
    verbose=True
)

# Example run
if __name__ == "__main__":
    input_prompt = str(input("Enter any of the following similar prompts:\n"+ str(["Parse 'features/payment.feature' and create corresponding test issues in JIRA \n",
                              "Read the feature file 'features/signup.feature' and generate JIRA tests for each scenario \n",
                              "Convert all scenarios in 'features/login.feature' into JIRA tests with steps \n",
                              "Create test cases in JIRA based on scenarios from 'features/orders.feature' \n" ])+"\n"))
    #prompt = "{Create test issues in JIRA from the scenarios in '"+input_prompt+"'}"
    prompt = input_prompt
    result = agent.run(prompt)
    print(result)