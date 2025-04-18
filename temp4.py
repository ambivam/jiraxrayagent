import requests
import json

# GraphQL endpoint URL
url = "https://xray.cloud.getxray.app/api/v2/graphql"

# Authorization token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnQiOiIwYmQxNThkNC1kY2QzLTM5OTMtOTFjYy03OTdhMGI5MDA2MTYiLCJhY2NvdW50SWQiOiI3MTIwMjA6ODRlMDEyZjEtNzZkZC00Y2ZhLTkxNmMtNjE3MGNjZDQ4NDFhIiwiaXNYZWEiOmZhbHNlLCJpYXQiOjE3NDQ5NDcxMTAsImV4cCI6MTc0NTAzMzUxMCwiYXVkIjoiMzAxODQ3QjNFQzY4NEU0QUFCREYwQzIwQjYxOUEzMzMiLCJpc3MiOiJjb20ueHBhbmRpdC5wbHVnaW5zLnhyYXkiLCJzdWIiOiIzMDE4NDdCM0VDNjg0RTRBQUJERjBDMjBCNjE5QTMzMyJ9.dl4ygTNMVUCoivmH33O2_IStTlFPR6OAEO_qlG30fcQ"

# GraphQL mutation query with escaped newlines
mutation = """
mutation {
  updateGherkinTestDefinition(
    issueId: "10415",
    gherkin: "Feature: My feature\\nScenario: Example\\nGiven I do something\\nThen I see something"
  ) {
    issueId
  }
}
"""

# Headers with Authorization
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

# Data payload to send with the request
data = {
    "query": mutation
}

# Make the POST request
response = requests.post(url, headers=headers, json=data)

# Check for success and print the response
if response.status_code == 200:
    print("Mutation successful:", json.dumps(response.json(), indent=2))
else:
    print("Error:", response.status_code, response.text)
