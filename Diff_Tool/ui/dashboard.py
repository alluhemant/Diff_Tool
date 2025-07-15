import streamlit as st
import requests
import json
import uuid
from typing import Dict, List, Tuple
from difflib import unified_diff, ndiff
from html import escape
import subprocess
import webbrowser
import time
import sys
from pathlib import Path

# Add parent directory to sys.path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.config import settings

API_BASE_URL = settings.API_BASE_URL


# Sidebar: API Documentation
def show_api_endpoints():
    st.sidebar.title("API Documentation")

    with st.sidebar.expander("Compare APIs"):
        st.code(
            f"""curl -X 'POST' \\
  '{API_BASE_URL}/api/v1/compare?url1=<url1>&url2=<url2>&method=get' \\
  -H 'accept: application/json'""",
            language="bash"
        )

    with st.sidebar.expander("Get Latest Comparison"):
        st.code(
            f"""curl -X 'GET' \\
  '{API_BASE_URL}/api/v1/latest' \\
  -H 'accept: application/json'""",
            language="bash"
        )

    with st.sidebar.expander("Get History of Comparisons"):
        st.code(
            f"""curl -X 'GET' \\
  '{API_BASE_URL}/api/v1/history?limit=10' \\
  -H 'accept: application/json'""",
            language="bash"
        )


# Utility Functions

def get_latest_comparison():
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/latest")
        if response.status_code == 200:
            data = response.json()
            return {
                'tibco_response': data.get('tibco_response', ''),
                'python_response': data.get('python_response', ''),
                'id': data.get('id', str(uuid.uuid4()))
            }
        else:
            st.warning(f"No latest data. ({response.status_code})")
    except Exception as e:
        st.error(f"❌ Error fetching latest: {e}")
    return None


def get_comparison_history(limit: int = 10):
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/history", params={"limit": limit})
        if response.status_code == 200:
            data = response.json()
            return [
                {
                    'tibco_response': item.get('tibco_response', ''),
                    'python_response': item.get('python_response', ''),
                    'id': item.get('id', str(uuid.uuid4())),
                    'created_at': item.get('created_at', 'N/A'),
                    'metrics': item.get('metrics', {}),
                    'differences': item.get('differences', '')
                }
                for item in data
            ]
        else:
            st.warning(f"No history available. ({response.status_code})")
    except Exception as e:
        st.error(f"❌ Error fetching history: {e}")
    return []


def parse_diff(old_text: str, new_text: str) -> Tuple[Dict[str, List[str]], str]:
    diff = list(unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm=""))
    changes = {'added': [], 'removed': [], 'changed': []}

    for line in diff[3:]:  # Skip diff headers
        if line.startswith('+') and not line.startswith('+++'):
            changes['added'].append(line[1:].strip())
        elif line.startswith('-') and not line.startswith('---'):
            changes['removed'].append(line[1:].strip())

    # Identify changed lines appearing in both added and removed
    changes['changed'] = list(set(changes['added']) & set(changes['removed']))
    changes['added'] = [f for f in changes['added'] if f not in changes['changed']]
    changes['removed'] = [f for f in changes['removed'] if f not in changes['changed']]

    return changes, '\n'.join(diff)


def prepare_report_text(changes: Dict[str, List[str]], diff_text: str) -> str:
    content = []
    if changes['changed']:
        content.append("Changed:\n" + '\n'.join(changes['changed']))
    if changes['added']:
        content.append("Added:\n" + '\n'.join(changes['added']))
    if changes['removed']:
        content.append("Removed:\n" + '\n'.join(changes['removed']))
    content.append("\nFull Diff:\n" + diff_text)
    return '\n\n'.join(content)


def render_github_like_diff(diff_text: str):
    styled_lines = []
    for line in diff_text.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            styled_lines.append(
                f"<div style='background-color:#e6ffed;padding:2px 6px;font-family:monospace;'>{escape(line)}</div>")
        elif line.startswith('-') and not line.startswith('---'):
            styled_lines.append(
                f"<div style='background-color:#ffeef0;padding:2px 6px;font-family:monospace;'>{escape(line)}</div>")
        else:
            styled_lines.append(
                f"<div style='background-color:#f6f8fa;padding:2px 6px;font-family:monospace;'>{escape(line)}</div>")
    st.markdown("\n".join(styled_lines), unsafe_allow_html=True)


def render_split_diff(old: str, new: str):
    """Render side-by-side diff view"""
    left_lines = old.splitlines()
    right_lines = new.splitlines()
    diffs = list(ndiff(left_lines, right_lines))

    table_style = """
    <style>
    .diff-wrapper {
        overflow-x: auto;
        border: 1px solid #ccc;
        max-width: 100%;
        padding: 10px;
    }
    .diff-table {
        border-collapse: collapse;
        width: 100%;
        font-family: monospace;
        table-layout: fixed;
    }
    .diff-table th, .diff-table td {
        padding: 6px 10px;
        vertical-align: top;
        word-wrap: break-word;
        border: 1px solid #ddd;
        white-space: pre-wrap;
    }
    .diff-add {
        background-color: #e6ffed;
    }
    .diff-remove {
        background-color: #ffeef0;
    }
    .diff-context {
        background-color: #f6f8fa;
    }
    .diff-empty {
        background-color: #fff;
    }
    </style>
    """

    html = [table_style, "<div class='diff-wrapper'>", "<table class='diff-table'>",
            "<tr><th>TIBCO</th><th>Python</th></tr>"]

    for line in diffs:
        tag = line[0]
        content = escape(line[2:])
        if tag == ' ':
            left_cell = f"<td class='diff-context'>{content}</td>"
            right_cell = f"<td class='diff-context'>{content}</td>"
        elif tag == '-':
            left_cell = f"<td class='diff-remove'>{content}</td>"
            right_cell = f"<td class='diff-empty'></td>"
        elif tag == '+':
            left_cell = f"<td class='diff-empty'></td>"
            right_cell = f"<td class='diff-add'>{content}</td>"
        else:
            continue
        html.append(f"<tr>{left_cell}{right_cell}</tr>")

    html.append("</table></div>")
    st.markdown("\n".join(html), unsafe_allow_html=True)


def start_locust():
    """Starts Locust load testing server and opens dashboard in browser."""
    try:
        locust_file_path = Path(__file__).resolve().parent.parent / "locustfile.py"

        cmd = [
            "locust",
            "-f", str(locust_file_path),
            "--host", "http://localhost:8000",
            "--web-port", "8089"
        ]

        subprocess.Popen(cmd)
        time.sleep(2)  # Wait a bit for the server to start
        webbrowser.open("http://localhost:8089")
        st.success("✅ Locust dashboard started at [http://localhost:8089](http://localhost:8089)")
    except Exception as e:
        st.error(f"❌ Failed to start Locust: {e}")


# Parameters

def manage_parameters(param_key: str, title: str) -> Dict[str, str]:
    st.subheader(title)

    if param_key not in st.session_state:
        st.session_state[param_key] = [{"key": "", "value": ""}]

    params = []

    for i, param in enumerate(st.session_state[param_key]):
        cols = st.columns([0.4, 0.4, 0.2])
        with cols[0]:
            key = st.text_input(f"Key_{param_key}_{i}",
                                value=param["key"],
                                placeholder="Parameter name",
                                key=f"key_{param_key}_{i}")
        with cols[1]:
            value = st.text_input(f"Value_{param_key}_{i}",
                                  value=param["value"],
                                  placeholder="Parameter value",
                                  key=f"value_{param_key}_{i}")
        with cols[2]:
            if st.button("❌", key=f"remove_{param_key}_{i}"):
                continue

        params.append({"key": key, "value": value})

    if st.button("➕ Add Parameter", key=f"add_{param_key}"):
        params.append({"key": "", "value": ""})

    st.session_state[param_key] = params

    # Filter out empty keys
    return {p["key"]: p["value"] for p in params if p["key"].strip()}


# Display Comparison Result

def show_comparison_result(comp: Dict, idx: int = 0):
    if not comp.get("tibco_response") or not comp.get("python_response"):
        st.warning("Incomplete comparison data.")
        return

    diff_mode = st.radio(
        "View Mode",
        ["Unified", "Split"],
        horizontal=True,
        key=f"view_mode_{comp['id']}_{idx}"  # include idx here to ensure uniqueness
    )
    changes, diff_text = parse_diff(comp['tibco_response'], comp['python_response'])
    report_text = prepare_report_text(changes, diff_text)

    with st.expander("Diff View", expanded=False):
        if diff_mode == "Unified":
            render_github_like_diff(diff_text)
        else:
            render_split_diff(comp["tibco_response"], comp["python_response"])

    with st.expander("Raw Responses"):
        col1, col2 = st.columns(2)
        with col1:
            st.code(
                comp['tibco_response'],
                language="xml" if comp["tibco_response"].strip().startswith('<') else "json"
            )
        with col2:
            st.code(
                comp['python_response'],
                language="xml" if comp["python_response"].strip().startswith('<') else "json"
            )

    st.download_button(
        "Download Diff Report",
        report_text,
        file_name="diff_report.txt",
        key=f"download_diff_{comp.get('id', '')}"
    )


# Main Dashboard
def show_dashboard():
    st.set_page_config(layout="wide", page_title="Response Comparison Dashboard")
    show_api_endpoints()
    st.title("Response Comparison Dashboard")

    # URL inputs
    col1, col2 = st.columns(2)
    with col1:
        url1 = st.text_input("URL 1", placeholder="http://example.com/api/v1/endpoint")
    with col2:
        url2 = st.text_input("URL 2", placeholder="http://example.com/api/v2/endpoint")

    # HTTP method selection
    method = st.radio("HTTP Method", ["GET", "POST"], horizontal=True)

    # URL parameters management
    with st.expander("URL 1 Parameters", expanded=False):
        params1 = manage_parameters("url1_params", "URL 1 Parameters")

    with st.expander("URL 2 Parameters", expanded=False):
        params2 = manage_parameters("url2_params", "URL 2 Parameters")

    # POST body input
    post_body = ""
    if method == "POST":
        post_body = st.text_area("Request Body (JSON/XML)", height=200)

    # Action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚀 Run Comparison", use_container_width=True):
            if url1 and url2:
                try:
                    request_params = {
                        "url1": url1,
                        "url2": url2,
                        "method": method.lower(),
                        "url1_params": json.dumps(params1),
                        "url2_params": json.dumps(params2),
                    }

                    headers = {}
                    json_body = None
                    data_body = None

                    if method == "POST":
                        body_text = post_body.strip()
                        if body_text:
                            try:
                                json_body = json.loads(body_text)
                                headers['Content-Type'] = 'application/json'
                            except ValueError:
                                data_body = body_text
                                headers['Content-Type'] = 'application/xml'

                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/compare",
                        params=request_params,
                        json=json_body,
                        data=data_body,
                        headers=headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.session_state["latest"] = {
                            'tibco_response': result.get('tibco_response', ''),
                            'python_response': result.get('python_response', ''),
                            'id': result.get('id', str(uuid.uuid4()))
                        }
                        # Refresh history automatically after successful comparison
                        st.session_state["history"] = get_comparison_history()
                        st.success("Comparison successful!")
                    else:
                        try:
                            detail = response.json().get("detail", "")
                        except Exception:
                            detail = response.text
                        st.error(f"❌ Comparison failed ({response.status_code}): {detail}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Please provide both URLs")

    with col2:
        if st.button("🔄 Fetch Latest", use_container_width=True):
            st.session_state["latest"] = get_latest_comparison()

    with col3:
        if st.button("📜 View History", use_container_width=True):
            st.session_state["history"] = get_comparison_history()

    # Display latest comparison result
    st.markdown("---")
    st.header("Latest Comparison")
    latest = st.session_state.get("latest")
    if latest:
        show_comparison_result(latest)
    else:
        st.info("No comparison results available. Run a comparison first.")

    # Display comparison history
    st.markdown("---")
    st.header("Comparison History")
    history = st.session_state.get("history", [])
    for idx, item in enumerate(history):
        with st.expander(f"Comparison #{idx + 1} - {item.get('created_at', '')}"):
            st.write(f"Metrics: {item.get('metrics', {})}")
            show_comparison_result(item)


# Sidebar: Load Testing
with st.sidebar:
    st.markdown("---")
    st.subheader("🚀 Load Testing")
    if st.button("📊 Launch Locust Load Test"):
        start_locust()


if __name__ == "__main__":
    show_dashboard()
