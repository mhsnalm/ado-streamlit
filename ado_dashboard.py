import streamlit as st
import requests
import base64
import datetime
import pandas as pd
from datetime import timezone, timedelta
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="Azure DevOps PR Dashboard")

# Sidebar configuration inputs
st.sidebar.header("Configurations")

st.sidebar.info("""
**Setup Instructions:**
1. Enter your Azure DevOps organization, project, and Personal Access Token (PAT) in the fields below:
2. Select date from for analysis period
3. Click 'Fetch Pull Requests' to retrieve data
""")

# Try to get default values from secrets or environment variables
default_org = ""
default_project = ""
default_pat = ""

try:
    if "ado_organization" in st.secrets:
        default_org = st.secrets["ado_organization"]
    if "ado_project" in st.secrets:
        default_project = st.secrets["ado_project"]
    if "ado_pat" in st.secrets:
        default_pat = st.secrets["ado_pat"]
except:
    pass

# Configuration inputs
organization = st.sidebar.text_input("Organization", value=default_org)
project = st.sidebar.text_input("Project", value=default_project)
personal_access_token = st.sidebar.text_input("Personal Access Token (PAT)", value=default_pat, type="password")

# Date range selector with datetime inputs
today = datetime.datetime.now().date()

start_date = st.sidebar.date_input("Date From", value=today)

# Initialize session state for fetch button
if 'fetch_clicked' not in st.session_state:
    st.session_state.fetch_clicked = False

# Add button to fetch data in sidebar
if st.sidebar.button("Fetch Pull Requests", type="primary"):
    st.session_state.fetch_clicked = True

# Validate inputs
if not organization or not project or not personal_access_token:
    st.warning("Please provide Azure DevOps organization, project, and PAT in the sidebar to continue.")
    st.stop()

# Create authorization header
auth_header = base64.b64encode(f":{personal_access_token}".encode()).decode()

headers = {
    "Authorization": f"Basic {auth_header}",
    "Content-Type": "application/json"
}

# Main app
st.title("Azure DevOps Pull Requests")

if st.session_state.fetch_clicked:
    with st.spinner("Fetching pull requests..."):
        # Format date range for API
   
        # API URL for pull requests with date range
        url = f"https://dev.azure.com/{organization}/{project}/_apis/git/pullrequests?api-version=7.2-preview.2&searchCriteria.status=all&searchCriteria.queryTimeRangeType=created&$top=1000"
        

        url += f"&&searchCriteria.minTime={str(start_date)}"

        #st.info("Pull Requests starting from: "+str(start_date))
        
        try:
            response = requests.get(url, headers=headers, verify=False)
            
            if response.status_code == 200:
                pull_requests = response.json()["value"]
                
                if pull_requests:
                    # Extract relevant PR data
                    pr_data = []
                    for pr in pull_requests:
                        pr_data.append({
                            'PR ID': pr['pullRequestId'],
                            'Title': pr['title'],
                            'Status': pr['status'],
                            'Repository': pr['repository']['name'],
                            'Creator': pr['createdBy']['displayName'],
                            'Created Date': datetime.datetime.fromisoformat(pr['creationDate'].replace('Z', '+00:00'))
                        })
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(pr_data)
                    
                    # Format the date column
                    df['Created Date'] = df['Created Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Display success message
                    st.success(f"Found {len(df)} pull requests, since or from {str(start_date)}. Data fetched at {datetime.datetime.now()}")
                    
                    # Add filtering options
                    st.subheader("PR Filters")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        status_filter = st.multiselect("Status", options=sorted(df['Status'].unique()))
                    
                    with col2:
                        repo_filter = st.multiselect("Repository", options=sorted(df['Repository'].unique()))
                    
                    with col3:
                        creator_filter = st.multiselect("Creator", options=sorted(df['Creator'].unique()))
                    
                    # Apply filters
                    filtered_df = df.copy()
                    if status_filter:
                        filtered_df = filtered_df[filtered_df['Status'].isin(status_filter)]
                    if repo_filter:
                        filtered_df = filtered_df[filtered_df['Repository'].isin(repo_filter)]
                    if creator_filter:
                        filtered_df = filtered_df[filtered_df['Creator'].isin(creator_filter)]
                    
                    # Display the data grid
                    st.subheader("Pull Requests")
                    st.dataframe(
                        filtered_df,
                        column_config={
                            "PR ID": st.column_config.NumberColumn("PR ID", format="%d"),
                            "Title": st.column_config.TextColumn("Title"),
                            "Status": st.column_config.TextColumn("Status"),
                            "Repository": st.column_config.TextColumn("Repository"),
                            "Creator": st.column_config.TextColumn("Creator"),
                            "Created Date": st.column_config.DatetimeColumn("Created Date", format="YYYY-MM-DD HH:mm:ss")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Add download button
                    csv = filtered_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download as CSV",
                        csv,
                        "pull_requests.csv",
                        "text/csv",
                        key='download-csv'
                    )
                else:
                    st.info("No pull requests found in the selected time period.")
            else:
                st.error(f"Error: {response.status_code}")
                st.error(response.text)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

else:
    st.info("Click 'Fetch Pull Requests' to retrieve data")
    
st.sidebar.info("""Developed by Mohsin Alam""")
