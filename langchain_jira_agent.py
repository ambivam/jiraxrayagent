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
from cucumber_test_creator import create_cucumber_test

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

def create_adf_description(text: str) -> dict:
    """Create description in Atlassian Document Format"""
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": text
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
        print(f"Token received, length: {len(token)}")

        results = []
        for scenario in scenarios:
            try:
                # Create JIRA issue
                payload = {
                    "fields": {
                        "project": {"key": os.getenv("JIRA_PROJECT_KEY")},
                        "summary": scenario['title'],
                        "description": {
                            "version": 1,
                            "type": "doc",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "Created by LangChain agent"
                                        }
                                    ]
                                }
                            ]
                        },
                        "issuetype": {"name": "Test"}
                    }
                }

                response = create_issue(payload)
                if response.status_code not in [200, 201]:
                    results.append(f"❌ Failed to create issue: {response.text}")
                    continue

                issue_data = response.json()
                issue_key = issue_data.get('key')
                if not issue_key:
                    results.append("❌ No issue key in response")
                    continue

                # Get issue ID and set as Cucumber
                issue_id = get_issue_id_from_key(issue_key, token)
                if not issue_id:
                    results.append(f"❌ Failed to get issue ID for {issue_key}")
                    continue

                # Set as Cucumber test
                if not set_cucumber_type(issue_id, token):
                    results.append(f"❌ Failed to set Cucumber type for {issue_key}")
                    continue

                # Add steps
                steps = [{"action": step, "result": "Expected outcome"} for step in scenario['steps']]
                steps_response = add_test_steps(issue_id, steps, token)
                if "errors" in steps_response:
                    results.append(f"❌ Failed to add steps for {issue_key}")
                    continue

                results.append(f"✅ Created Cucumber test {issue_key} with {len(steps)} steps")

            except Exception as e:
                print(f"Error processing scenario: {str(e)}")
                results.append(f"❌ Error: {str(e)}")

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