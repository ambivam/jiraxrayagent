import os
import re
import json
from dotenv import load_dotenv
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain.tools import BaseTool
from langchain.prompts import MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
import requests
from jira_client import create_issue
from xray_client import authenticate, add_test_steps

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

    def set_test_type_graphql(self, issue_key: str, test_type: str, token: str):
        # First, get the numeric ID for the issue
        get_issue_query = {
            "query": f"""
            query {{
                getTests(jql: "key = {issue_key}", limit: 1) {{
                    results {{
                        issueId
                    }}
                }}
            }}
            """
        }
        
        url = "https://xray.cloud.getxray.app/api/v2/graphql"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            # Get numeric ID first
            id_response = requests.post(url, headers=headers, json=get_issue_query)
            id_response.raise_for_status()
            id_data = id_response.json()
            
            if "errors" in id_data:
                return id_data
                
            issue_id = id_data.get("data", {}).get("getTests", {}).get("results", [{}])[0].get("issueId")
            if not issue_id:
                return {"errors": [{"message": f"Could not find numeric ID for issue {issue_key}"}]}
                
            # Now update test type using numeric ID
            mutation = {
                "query": f"""
                mutation {{
                    updateTestType(
                        issueId: "{issue_id}",
                        testType: {{ name: "{test_type}" }}
                    ) {{
                        testType {{
                            name
                        }}
                    }}
                }}
                """
            }
            
            response = requests.post(url, headers=headers, json=mutation)
            response.raise_for_status()
            return response.json()
                    
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            return {"errors": [{"message": f"Request failed: {str(e)}"}]}

    def _run(self, feature_file_path: str):
        scenarios = parse_feature_file(feature_file_path)
        token = authenticate()
        print(f"Token: {token}")

        results = []
        for scenario in scenarios:
            # Create JIRA issue
            payload = {
                "fields": {
                    "project": {"key": os.getenv("JIRA_PROJECT_KEY")},
                    "summary": scenario['title'],
                    "description": create_adf_paragraph("Created by LangChain agent"),
                    "issuetype": {"name": "Test"}
                }
            }

            response = create_issue(payload)
            issue_key = response.json().get('key')

            if issue_key:
                # Set test type using GraphQL mutation with improved response handling
                graphql_response = self.set_test_type_graphql(issue_key, "Cucumber", token)
                
                if "errors" in graphql_response:
                    error_msg = graphql_response["errors"][0]["message"]
                    results.append(f"❌ Failed to set test type for {issue_key}: {error_msg}")
                    continue

                # Convert scenario steps to Xray test steps
                steps_payload = []
                for step in scenario['steps']:
                    steps_payload.append({
                        "action": step,
                        "result": "Expected outcome"
                    })

                add_steps_response = add_test_steps(issue_key, steps_payload, token)
                if add_steps_response.status_code != 200 or "errors" in add_steps_response.json():
                    results.append(f"❌ Failed to add steps for {issue_key}: {add_steps_response.json().get('errors')}")
                else:
                    results.append(f"✅ Created {issue_key} with {len(steps_payload)} Xray test steps (type: Cucumber)")

            else:
                results.append(f"❌ Failed to create issue for scenario: {scenario['title']}")

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