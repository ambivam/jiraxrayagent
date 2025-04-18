from xray_client import authenticate, get_issue_id_by_key
token = authenticate()
print(token )
issue_id = get_issue_id_by_key("XTT-241", token)
print("Issue ID:", issue_id)
