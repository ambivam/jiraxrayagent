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
from xray_client import authenticate, add_test_steps, build_gherkin, get_issue_id, get_issue_id_from_key, set_cucumber_type, get_multiple_issue_ids, set_multiple_cucumber_types, update_gherkin_for_issue, update_test_type_to_cucumber
from cucumber_test_creator import create_cucumber_test

# Load environment variables
load_dotenv()

BASE_URL = 'https://xray.cloud.getxray.app/api/v2/graphql'

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
    description: str = "Creates new test issues in JIRA from one or more feature files"

    def process_feature_file(self, feature_file_path: str, token: str) -> list:
        scenarios = parse_feature_file(feature_file_path)
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
                print("*******************THE ISSUE KEY IS:*********************************", issue_key)
                if not issue_key:
                    results.append("❌ No issue key in response")
                    continue

                # Get issue ID and set as Cucumber
                issue_id = get_issue_id(issue_key, token)
                print("*******************THE ISSUE ID IS:*********************************", issue_id)
                if not issue_id:
                    results.append(f"❌ Failed to get issue ID for {issue_key}")
                    continue

                # Set as Cucumber test
                if not update_test_type_to_cucumber(issue_id, token):
                    results.append(f"❌ Failed to set Cucumber type for {issue_key}")
                    continue

                # Add steps                
                gherkin_steps = build_gherkin(scenario)
                # Wrap in triple quotes
                #formatted_gherkin = f"""\"\"\"\n{gherkin_steps}\"\"\""""  
                formatted_gherkin = f"""{gherkin_steps}"""             
                update_gherkin_for_issue(issue_key, formatted_gherkin,token)

                results.append(f"✅ Created Cucumber test {issue_key} with {len(scenario['steps'])} steps")

            except Exception as e:
                print(f"Error processing scenario: {str(e)}")
                results.append(f"❌ Error: {str(e)}")
        return results

    def _run(self, feature_files_input: str):
        token = authenticate()
        print(f"Token received, length: {len(token)}")

        # Handle multiple feature files
        feature_files = [f.strip() for f in feature_files_input.split(',')]
        all_results = []
        
        for feature_file in feature_files:
            is_valid, result = validate_feature_file(feature_file)
            if not is_valid:
                all_results.append(f"❌ {result}")
                continue
                
            print(f"\nProcessing feature file: {result}")
            try:
                results = self.process_feature_file(result, token)
                all_results.extend(results)
            except Exception as e:
                all_results.append(f"❌ Error processing {result}: {str(e)}")

        return "\n".join(all_results)

    def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async not supported")

def validate_feature_file(file_path: str) -> tuple[bool, str]:
    """Validate that feature file exists and is readable"""
    if not file_path.endswith('.feature'):
        return False, f"'{file_path}' is not a feature file"
    
    # Add 'features/' prefix if not present
    if not file_path.startswith('features/'):
        file_path = f"features/{file_path}"
    
    try:
        with open(file_path, 'r') as f:
            f.read()
        return True, file_path
    except FileNotFoundError:
        return False, f"File not found: {file_path}"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

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

def parse_natural_language_input(input_text: str) -> list:
    """Extract feature file paths from natural language input"""
    # Common patterns for feature files
    feature_pattern = r'(?:\'|")?(?:features/[\w-]+\.feature|[\w-]+\.feature)(?:\'|")?'
    feature_files = re.findall(feature_pattern, input_text)
    
    # If no files found, check if user just typed the name
    if not feature_files:
        words = input_text.split()
        feature_files = [f"features/{word}.feature" for word in words if word.lower() not in 
                        {'create', 'test', 'cases', 'from', 'the', 'file', 'and', 'using', 'with'}]
    
    return list(set(feature_files))  # Remove duplicates

if __name__ == "__main__":
    print("Enter your request in natural language. Examples:")
    print("- Create tests from todo.feature")
    print("- Process features/login.feature and features/signup.feature")
    print("- Convert scenarios from payment.feature")
    
    user_input = input("\nWhat would you like to do? ")
    feature_files = parse_natural_language_input(user_input)
    
    if not feature_files:
        print("❌ No feature files detected in your input. Please try again.")
    else:
        print(f"\nDetected feature files: {', '.join(feature_files)}")
        # Validate files before processing
        valid_files = []
        for file in feature_files:
            is_valid, result = validate_feature_file(file)
            if is_valid:
                valid_files.append(result)
            else:
                print(f"❌ {result}")
        
        if valid_files:
            result = agent.run(", ".join(valid_files))
            print(result)
        else:
            print("❌ No valid feature files found. Please check file paths and try again.")