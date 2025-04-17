import streamlit as st
import os
from langchain_jira_agent import CreateJiraTestTool, parse_feature_file

st.set_page_config(page_title="JIRA Test Creator", layout="wide")

st.title("JIRA Test Case Creator")
st.write("Select a feature file to create JIRA test cases from Gherkin scenarios")

# Setup feature files directory
FEATURES_DIR = "features"
if not os.path.exists(FEATURES_DIR):
    os.makedirs(FEATURES_DIR)

# Get list of feature files
feature_files = [f for f in os.listdir(FEATURES_DIR) if f.endswith('.feature')]

if not feature_files:
    st.warning("No feature files found in the 'features' directory. Please add some .feature files.")
else:
    # File selector
    selected_file = st.selectbox(
        "Select a feature file",
        feature_files,
        format_func=lambda x: x.replace('.feature', '')
    )

    # Show file preview
    if selected_file:
        with open(os.path.join(FEATURES_DIR, selected_file), 'r') as file:
            content = file.read()
            with st.expander("Preview Feature File", expanded=False):
                st.code(content, language='gherkin')

    # Process button
    if st.button("Create JIRA Test Cases"):
        with st.spinner('Processing...'):
            try:
                tool = CreateJiraTestTool()
                result = tool._run(os.path.join(FEATURES_DIR, selected_file))
                
                # Display results
                for line in result.split('\n'):
                    if '✅' in line:
                        st.success(line)
                    elif '❌' in line:
                        st.error(line)
                    else:
                        st.info(line)
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
