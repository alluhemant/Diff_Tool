import streamlit as st
import requests
import json
import uuid
from typing import Dict, List, Tuple, Optional
from difflib import unified_diff, ndiff
from html import escape
import subprocess
import webbrowser
import time
import sys
from pathlib import Path

# Adding the parent directory to sys.path for imports
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


def get_latest_comparison():
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/latest")
        if response.status_code == 200:
            data = response.json()
            return {
                'tibco_response': data.get('tibco_response', ''),
                'python_response': data.get('python_response', ''),
                'id': data.get('id', str(uuid.uuid4())),
                'content_type1': data.get('content_type1'),
                'content_type2': data.get('content_type2'),
                'metrics': data.get('metrics', {}),
                'differences': data.get('differences', ''),
                'created_at': data.get('created_at', 'N/A')
            }
        else:
            st.warning(f"No latest data. ({response.status_code})")
    except Exception as e:
        st.error(f"Error fetching latest: {e}")
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
                    'differences': item.get('differences', ''),
                    'content_type1': item.get('content_type1'),
                    'content_type2': item.get('content_type2')
                }
                for item in data
            ]
        else:
            st.warning(f"No history available. ({response.status_code})")
    except Exception as e:
        st.error(f"Error fetching history: {e}")
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
        st.success("Locust dashboard started at [http://localhost:8089](http://localhost:8089)")
    except Exception as e:
        st.error(f"Failed to start Locust: {e}")


# Parameters
def manage_parameters(param_key: str, title: str) -> Dict[str, str]:
    st.subheader(title)

    if param_key not in st.session_state:
        st.session_state[param_key] = [{"key": "", "value": ""}]

    params = []

    for i, param in enumerate(st.session_state[param_key]):
        cols = st.columns([0.4, 0.4, 0.2])
        with cols[0]:
            key = st.text_input("Key",
                                value=param["key"],
                                placeholder="Parameter name",
                                key=f"key_input_{param_key}_{i}")
        with cols[1]:
            value = st.text_input("Value",
                                  value=param["value"],
                                  placeholder="Parameter value",
                                  key=f"value_input_{param_key}_{i}")
        with cols[2]:
            if st.button("❌", key=f"remove_{param_key}_{i}"):
                continue

        params.append({"key": key, "value": value})

    if st.button("➕ Add Parameter", key=f"add_{param_key}"):
        params.append({"key": "", "value": ""})

    st.session_state[param_key] = params

    return {p["key"]: p["value"] for p in params if p["key"].strip()}


def detect_and_render_response(content: str, content_type: Optional[str], key: str):
    # Helps to detect and render response based on a content type"""
    if not content:
        st.warning("Empty response")
        return

    # we are trying to auto-detect if content_type not provided.
    if not content_type:
        if content.strip().startswith('{') or content.strip().startswith('['):
            content_type = 'application/json'
        elif content.strip().startswith('<'):
            content_type = 'application/xml'

    try:
        if content_type and 'json' in content_type:
            try:
                parsed = json.loads(content)
                st.json(parsed)
                return
            except json.JSONDecodeError:
                pass

        if content_type and 'xml' in content_type:
            st.code(content, language='xml')
            return

        # fallback to plain text with syntax highlighting.
        st.code(content, language='text')
    except Exception as e:
        st.error(f"Failed to render content: {str(e)}")
        st.code(content, language='text')


def show_comparison_result(comp: Dict, idx: int = 0):
    unique_id = comp.get('id', str(idx))

    if not comp.get("tibco_response") or not comp.get("python_response"):
        missing = []
        if not comp.get("tibco_response"):
            missing.append("TIBCO response")
        if not comp.get("python_response"):
            missing.append("Python response")
        st.warning(f"Incomplete comparison data (missing: {', '.join(missing)})")

        with st.expander(f"Debug Details {unique_id}"):
            st.json({k: v for k, v in comp.items() if k not in ['tibco_response', 'python_response']})
        return

    # Fix: ensuring the unique key using id + idx + suffix
    unique_key = f"view_mode_{comp.get('id', str(uuid.uuid4()))}_{idx}_key"
    diff_mode = st.radio("View Mode", ["Unified", "Split"], key=unique_key)
    changes, diff_text = parse_diff(comp['tibco_response'], comp['python_response'])
    report_text = prepare_report_text(changes, diff_text)

    with st.expander(f"Diff View  {unique_id}", expanded=False):
        if diff_mode == "Unified":
            render_github_like_diff(diff_text)
        else:
            render_split_diff(comp["tibco_response"], comp["python_response"])

    with st.expander(f"Raw Responses {unique_id}"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"URL 1 Response ({comp.get('content_type1', 'N/A')})")
            detect_and_render_response(
                comp['tibco_response'],
                comp.get('content_type1'),
                f"tibco_res_{unique_id}"
            )
        with col2:
            st.subheader(f"URL 2 Response ({comp.get('content_type2', 'N/A')})")
            detect_and_render_response(
                comp['python_response'],
                comp.get('content_type2'),
                f"python_res_{unique_id}"
            )

    st.download_button(
        "Download Diff Report",
        report_text,
        file_name=f"diff_report_{unique_id}.txt",
        key=f"download_diff_{unique_id}"
    )


# Main Dashboard =======================================================================


def show_dashboard():
    st.set_page_config(layout="wide", page_title="API Response Comparison Dashboard",
                       page_icon="https://cdn-icons-png.flaticon.com/512/5968/5968872.png")
    show_api_endpoints()
    st.title("⚡ API Response Comparison Dashboard")

    # URL inputs
    col1, col2 = st.columns(2)
    with col1:
        url1 = st.text_input("URL 1",
                             placeholder="http://example.com/api/v1/endpoint",
                             key="url1_input")
    with col2:
        url2 = st.text_input("URL 2",
                             placeholder="http://example.com/api/v2/endpoint",
                             key="url2_input")

    # HTTP method selection
    method = st.radio("HTTP Method", ["GET", "POST"],
                      horizontal=True,
                      key="http_method_radio")

    # URL parameters management
    with st.expander("URL 1 Parameters", expanded=False):
        params1 = manage_parameters("url1_params", "URL 1 Parameters")

    with st.expander("URL 2 Parameters", expanded=False):
        params2 = manage_parameters("url2_params", "URL 2 Parameters")

    # Request bodies
    # st.subheader("Request Bodies", key="request_bodies_header")
    with st.expander("Request Bodies", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**URL 1 Body**")
            body1 = st.text_area(
                "Request Body for URL 1 (JSON/XML)",
                height=200,
                key="body1_text_area",
                help="Enter JSON or XML content for URL 1 request"
            )
        with col2:
            st.markdown("**URL 2 Body**")
            body2 = st.text_area(
                "Request Body for URL 2 (JSON/XML)",
                height=200,
                key="body2_text_area",
                help="Enter JSON or XML content for URL 2 request"
            )

    # Action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚀 Run Comparison",
                     use_container_width=True,
                     key="run_comparison_button"):
            if url1 and url2:
                try:
                    request_params = {
                        "url1": url1,
                        "url2": url2,
                        "method": method.lower(),
                        "url1_params": json.dumps(params1),
                        "url2_params": json.dumps(params2),
                    }

                    # Add bodies to params if provided
                    if body1.strip():
                        request_params["body1"] = body1.strip()
                    if body2.strip():
                        request_params["body2"] = body2.strip()

                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/compare",
                        params=request_params
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.session_state["latest"] = {
                            'tibco_response': result.get('tibco_response', ''),
                            'python_response': result.get('python_response', ''),
                            'id': result.get('id', str(uuid.uuid4())),
                            'content_type1': result.get('content_type1'),
                            'content_type2': result.get('content_type2'),
                            'metrics': result.get('metrics', {}),
                            'differences': result.get('differences', ''),
                            'created_at': result.get('created_at', 'N/A')
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
        if st.button("🔄 Fetch Latest",
                     use_container_width=True,
                     key="fetch_latest_button"):
            st.session_state["latest"] = get_latest_comparison()

    with col3:
        if st.button("📜 View History",
                     use_container_width=True,
                     key="view_history_button"):
            st.session_state["history"] = get_comparison_history()

    st.markdown("---")
    with st.expander("Direct Body Comparison", expanded=False):
        # st.header("Direct Body Comparison")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Body 1**")
            direct_body1 = st.text_area(
                "Direct Body 1 (JSON/XML)",
                height=200,
                key="direct_body1_text_area",
                help="Enter JSON or XML content for direct comparison"
            )
        with col2:
            st.markdown("**Body 2**")
            direct_body2 = st.text_area(
                "Direct Body 2 (JSON/XML)",
                height=200,
                key="direct_body2_text_area",
                help="Enter JSON or XML content for direct comparison"
            )

        if st.button("🔍 Compare Bodies Directly", key="compare_bodies_button"):
            if direct_body1 and direct_body2:
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/compare/body",
                        json={
                            "body1": direct_body1,
                            "body2": direct_body2
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.session_state["latest"] = {
                            'tibco_response': result.get('tibco_response', ''),
                            'python_response': result.get('python_response', ''),
                            'id': result.get('id', str(uuid.uuid4())),
                            'content_type1': result.get('content_type1'),
                            'content_type2': result.get('content_type2'),
                            'metrics': result.get('metrics', {}),
                            'differences': result.get('differences', ''),
                            'created_at': result.get('created_at', 'N/A')
                        }
                        # Refresh history automatically after successful comparison
                        st.session_state["history"] = get_comparison_history()
                        st.success("Direct body comparison successful!")
                    else:
                        try:
                            detail = response.json().get("detail", "")
                        except Exception:
                            detail = response.text
                        st.error(f"Direct comparison failed ({response.status_code}): {detail}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Please provide both bodies for comparison")

    # Display latest comparison result
    st.markdown("---")
    st.header("Latest Comparison")
    latest = st.session_state.get("latest")
    if latest:
        show_comparison_result(latest, idx=9999)
    else:
        st.info("No comparison results available. Run a comparison first.")

    # Display comparison history
    st.markdown("---")
    st.header("Comparison History")
    history = st.session_state.get("history", [])
    for idx, item in enumerate(history):
        # Skip rendering the latest again if it's the same as first history item
        if latest and item.get("id") == latest.get("id"):
            continue

        with st.expander(f"Comparison #{idx + 1} - {item.get('created_at', '')}"):
            st.write(f"Metrics: {item.get('metrics', {})}")
            show_comparison_result(item, idx)


# Sidebar: Load Testing
with st.sidebar:
    st.markdown("---")
    # st.subheader("🚀 Load Testing", key="load_testing_header")
    st.subheader("⚡ Load Testing")
    if st.button("📊 Launch Locust Load Test", key="locust_button"):
        start_locust()

    # Add debug expander at the bottom of the sidebar
    st.markdown("---")
    st.subheader("⚡ Debug Endpoints")
    debug_expander = st.expander("🔧 Debug Information", expanded=False)

    with debug_expander:
        # Get the latest comparison data if available
        latest = st.session_state.get("latest", {})
        history = st.session_state.get("history", [])
        latest_id = latest.get('id', None) if latest else None

        st.write("### System Status")
        status_col1, status_col2 = st.columns(2)

        with status_col1:
            st.write("**API Status:**")
            try:
                # Check API status by making a simple request
                response = requests.get(f"{API_BASE_URL}/api/v1/latest")
                if response.status_code == 200:
                    st.success("✅ Operational")
                else:
                    st.error(f"❌ API Error: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Connection Failed: {str(e)}")

            st.write("**Last Fetched:**")
            if history:
                last_fetched = history[0].get('created_at', 'Unknown') if history else 'Never'
                st.write(last_fetched)
            else:
                st.write("Never")

        with status_col2:
            st.write("**Data Counts:**")
            st.write(f"History: {len(history)}")
            st.write(f"Latest ID: {latest_id or 'None'}")

        st.write("### Verification Tools")

        if st.button("Verify API Endpoints", key="verify_api_button"):
            try:
                st.write("#### History Endpoint")
                history_resp = requests.get(f"{API_BASE_URL}/api/v1/history?limit=5")
                if history_resp.status_code == 200:
                    history_data = history_resp.json()
                    st.success(f"✅ Returned {len(history_data)} comparisons")
                    st.json({
                        "sample_ids": [x.get('id') for x in history_data],
                        "first_item": {k: v for k, v in history_data[0].items()
                                       if k in ['id', 'created_at']} if history_data else None
                    })
                else:
                    st.error(f"❌ Failed: {history_resp.status_code}")

                st.write("#### Latest Endpoint")
                latest_resp = requests.get(f"{API_BASE_URL}/api/v1/latest")
                if latest_resp.status_code == 200:
                    latest_data = latest_resp.json()
                    st.success("✅ Operational")
                    st.json({
                        "id": latest_data.get('id'),
                        "created_at": latest_data.get('created_at')
                    })
                else:
                    st.error(f"❌ Failed: {latest_resp.status_code}")

            except Exception as e:
                st.error(f"Verification failed: {str(e)}")

        if st.button("Check Data Consistency", key="consistency_button"):
            try:
                history = requests.get(f"{API_BASE_URL}/api/v1/history?limit=1").json()
                latest = requests.get(f"{API_BASE_URL}/api/v1/latest").json()

                st.write("#### Consistency Report")
                cols = st.columns(3)

                with cols[0]:
                    st.write("**History**")
                    st.write(f"Count: {len(history)}")
                    st.write(f"First ID: {history[0]['id'] if history else 'None'}")

                with cols[1]:
                    st.write("**Latest**")
                    st.write(f"ID: {latest.get('id', 'None')}")

                with cols[2]:
                    st.write("**Match**")
                    if history and latest:
                        match = history[0]['id'] == latest['id']
                        st.write("✅" if match else "❌")
                        st.write("Consistent" if match else "Inconsistent")
                    else:
                        st.write("No data")

            except Exception as e:
                st.error(f"Check failed: {str(e)}")

if __name__ == "__main__":
    show_dashboard()
