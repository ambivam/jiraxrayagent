from dotenv import load_dotenv
from langchain.agents import initialize_agent, Tool
#from langchain_community.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI

from langchain.tools import BaseTool
from langchain.prompts import MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from jira_client import create_issue
from xray_client import authenticate, add_test_steps
import os
import re

load_dotenv()

llm = ChatOpenAI(
    model_name="gpt-4",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Function to parse scenarios from a feature file
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

# LangChain Tool to create a test in JIRA
class CreateJiraTestTool(BaseTool):
    name: str = "create_jira_test"
    description: str = "Creates a new test issue in JIRA and adds steps to it"

    def _run(self, feature_file_path: str):
        scenarios = parse_feature_file(feature_file_path)
        #token = authenticate().get('token')
        token = authenticate()

        results = []
        for scenario in scenarios:
            payload = {
                            "fields": {
                                "project": {"key": os.getenv("JIRA_PROJECT_KEY")},
                                "summary": scenario['title'],
                                "description": {
                                    "type": "doc",
                                    "version": 1,
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "text": scenario['title'],
                                                    "type": "text"
                                                }
                                            ]
                                        }
                                    ]
                                },
                                "issuetype": {"name": "Test"}
                            }
            }
            response = create_issue(payload)
            issue_key = response.json().get('key')
            print("THE ISSUE KEY IS :",response.json())
            
            if issue_key:
                steps_payload = []
                for step in scenario['steps']:
                    steps_payload.append({
                        "action": step,
                        "result": "Expected outcome to be defined"
                    })
                add_test_steps(issue_key, steps_payload, token)
                results.append(f"Created {issue_key} with {len(steps_payload)} steps")

        return "\n".join(results)

    def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async not supported")

# Set up LangChain agent
llm = ChatOpenAI(model_name="gpt-4", temperature=0)

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
