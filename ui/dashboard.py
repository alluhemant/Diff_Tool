import streamlit as st
import requests
import json
import uuid
from typing import Dict, List, Tuple, Optional
from difflib import unified_diff, ndiff
from html import escape
import time
import sys
from pathlib import Path
import xml.dom.minidom

# Adding the parent directory to sys.path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.config import settings
from app.core.compare import detect_content_type

API_BASE_URL = settings.API_BASE_URL


# --- HELPER FUNCTIONS FOR API CALLS ---
def get_latest_comparison() -> Optional[Dict]:
    """Fetches the most recent comparison result from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/latest")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            st.info("No comparisons found in history.")
            return None
        else:
            st.error(f"Failed to fetch latest result: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return None


def get_comparison_history() -> List[Dict]:
    """Fetches the comparison history from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/history")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch history: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return []


# --- UI AND FORMATTING HELPER FUNCTIONS ---

def pretty_format_response(content: str, content_type: Optional[str]) -> str:
    if not content:
        return ""
    ct = content_type if content_type else detect_content_type(content)
    if 'json' in ct:
        try:
            parsed_json = json.loads(content)
            return json.dumps(parsed_json, indent=2, sort_keys=True)
        except json.JSONDecodeError:
            return content
    if 'xml' in ct:
        try:
            dom = xml.dom.minidom.parseString(content)
            return dom.toprettyxml()
        except Exception:
            return content
    return content


def parse_diff(old_text: str, new_text: str) -> str:
    diff = list(unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm=""))
    return '\n'.join(diff)


def prepare_report_text(diff_text: str) -> str:
    return "Full Diff Report:\n\n" + diff_text


def render_github_like_diff(diff_text: str):
    if not diff_text.strip() or "No differences found" in diff_text:
        st.success("✅ No differences found after formatting.")
        return
    styled_lines = []
    for line in diff_text.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            styled_lines.append(
                f"<div style='background-color:#e6ffed; padding:2px 6px; font-family:monospace; white-space:pre-wrap;'>{escape(line)}</div>")
        elif line.startswith('-') and not line.startswith('---'):
            styled_lines.append(
                f"<div style='background-color:#ffeef0; padding:2px 6px; font-family:monospace; white-space:pre-wrap;'>{escape(line)}</div>")
        else:
            styled_lines.append(
                f"<div style='background-color:#f6f8fa; padding:2px 6px; font-family:monospace; white-space:pre-wrap;'>{escape(line)}</div>")
    st.markdown("\n".join(styled_lines), unsafe_allow_html=True)


def render_split_diff(old: str, new: str):
    diffs = list(ndiff(old.splitlines(), new.splitlines()))
    if not any(d.startswith('+') or d.startswith('-') for d in diffs):
        st.success("✅ No differences found after formatting.")
        return
    table_style = """
    <style>
    .diff-wrapper { overflow-x: auto; border: 1px solid #ccc; }
    .diff-table { border-collapse: collapse; width: 100%; font-family: monospace; table-layout: fixed; }
    .diff-table th, .diff-table td { padding: 4px 8px; vertical-align: top; border: 1px solid #ddd; white-space: pre-wrap; word-wrap: break-word; }
    .diff-add { background-color: #e6ffed; }
    .diff-remove { background-color: #ffeef0; }
    .diff-context { background-color: #f6f8fa; }
    .diff-empty { background-color: #fafbfc; }
    </style>
    """
    html = [table_style, "<div class='diff-wrapper'><table class='diff-table'>"]
    html.append("<tr><th>Source</th><th>Target</th></tr>")
    i = 0
    while i < len(diffs):
        line = diffs[i]
        tag = line[0]
        content = escape(line[2:])
        if tag == ' ':
            html.append(f"<tr><td class='diff-context'>{content}</td><td class='diff-context'>{content}</td></tr>")
            i += 1
        elif tag == '-':
            if i + 1 < len(diffs) and diffs[i + 1][0] == '+':
                next_content = escape(diffs[i + 1][2:])
                html.append(f"<tr><td class='diff-remove'>{content}</td><td class='diff-add'>{next_content}</td></tr>")
                i += 2
            else:
                html.append(f"<tr><td class='diff-remove'>{content}</td><td class='diff-empty'></td></tr>")
                i += 1
        elif tag == '+':
            html.append(f"<tr><td class='diff-empty'></td><td class='diff-add'>{content}</td></tr>")
            i += 1
        else:
            i += 1
    html.append("</table></div>")
    st.markdown("\n".join(html), unsafe_allow_html=True)


def manage_parameters(param_key: str, title: str) -> Dict[str, str]:
    st.subheader(title)
    if param_key not in st.session_state:
        st.session_state[param_key] = []
    param_list = st.session_state[param_key]
    for i, param_dict in enumerate(param_list):
        cols = st.columns([5, 5, 1])
        param_list[i]['key'] = cols[0].text_input("Key", value=param_dict.get('key', ''), key=f"key_{param_key}_{i}")
        param_list[i]['value'] = cols[1].text_input("Value", value=param_dict.get('value', ''),
                                                    key=f"value_{param_key}_{i}")
        if cols[2].button("❌", key=f"del_{param_key}_{i}"):
            del st.session_state[param_key][i]
            st.rerun()
    if st.button("➕ Add Parameter", key=f"add_{param_key}"):
        st.session_state[param_key].append({"key": "", "value": ""})
        st.rerun()
    return {p["key"]: p["value"] for p in st.session_state[param_key] if p.get("key")}


def manage_authentication(key_prefix: str) -> Dict:
    st.subheader(f"{key_prefix.title()} API Authentication")
    auth_type = st.radio(
        "Auth Type",
        ("No Auth", "Basic Auth", "Bearer Token"),
        key=f"auth_type_{key_prefix}",
        horizontal=True
    )
    auth_config = {}
    if auth_type == "Basic Auth":
        username = st.text_input("Username", key=f"username_{key_prefix}")
        password = st.text_input("Password", type="password", key=f"password_{key_prefix}")
        auth_config = {
            "auth_type": "basic",
            "basic": {"username": username, "password": password}
        }
    elif auth_type == "Bearer Token":
        token = st.text_input("Token", type="password", key=f"token_{key_prefix}")
        auth_config = {
            "auth_type": "bearer",
            "bearer": {"token": token}
        }
    else:
        auth_config = {"auth_type": "no_auth"}
    return auth_config


def detect_and_render_response(content: str, content_type: Optional[str], key: str):
    if not content:
        st.warning("Empty response")
        return
    ct = content_type if content_type else detect_content_type(content)
    if 'json' in ct:
        try:
            st.json(json.loads(content))
        except json.JSONDecodeError:
            st.code(content, language='text')
    elif 'xml' in ct:
        st.code(content, language='xml')
    else:
        st.code(content, language='text')


def show_comparison_result(comp: Dict, idx: any):
    unique_id = comp.get('id', str(idx))
    source_resp = comp.get('source_response', comp.get('tibco_response', ''))
    target_resp = comp.get('target_response', comp.get('python_response', ''))

    formatted_source = pretty_format_response(source_resp, comp.get('content_type1'))
    formatted_target = pretty_format_response(target_resp, comp.get('content_type2'))

    diff_text = parse_diff(formatted_source, formatted_target)
    report_text = prepare_report_text(diff_text)
    unique_key = f"view_mode_{unique_id}"
    diff_mode = st.radio("View Mode", ["Unified", "Split"], key=unique_key, horizontal=True)

    with st.expander(f"Diff View - {unique_id}", expanded=True):
        if diff_mode == "Unified":
            render_github_like_diff(diff_text)
        else:
            render_split_diff(formatted_source, formatted_target)

    with st.expander(f"Raw Responses - {unique_id}"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"Source Response ({comp.get('content_type1', 'N/A')})")
            detect_and_render_response(source_resp, comp.get('content_type1'), f"source_res_{unique_id}")
        with col2:
            st.subheader(f"Target Response ({comp.get('content_type2', 'N/A')})")
            detect_and_render_response(target_resp, comp.get('content_type2'), f"target_res_{unique_id}")

    st.download_button("Download Diff Report", report_text, file_name=f"diff_report_{unique_id}.txt",
                       key=f"download_diff_{unique_id}")


# --- Main App ---
def show_dashboard():
    st.set_page_config(layout="wide", page_title="API Response Comparison Dashboard")
    st.title("⚡ API Response Comparison Dashboard")

    input_tab, results_tab = st.tabs(["🔍 New Comparison", "📊 Results & History"])

    with input_tab:
        st.header("Configure API Requests")
        col1, col2 = st.columns(2)

        url1 = col1.text_input("**Source API URL**", placeholder="http://example.com/source-api", key="url1_input")
        url2 = col2.text_input("**Target API URL**", placeholder="http://example.com/target-api", key="url2_input")
        method = st.radio("**HTTP Method**", ["GET", "POST"], horizontal=True, key="http_method_radio")

        with st.expander("**Authentication**"):
            auth_col1, auth_col2 = st.columns(2)
            with auth_col1:
                source_auth_config = manage_authentication("source")
            with auth_col2:
                target_auth_config = manage_authentication("target")

        with st.expander("**Parameters & Request Bodies**"):
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                params1 = manage_parameters("url1_params", "Source API Parameters")
                st.markdown("**Source API Body**")
                body1 = st.text_area("Body for Source API", height=150, key="body1_text_area")
            with p_col2:
                params2 = manage_parameters("url2_params", "Target API Parameters")
                st.markdown("**Target API Body**")
                body2 = st.text_area("Body for Target API", height=150, key="body2_text_area")

        st.header("Run Comparison")
        if st.button("🚀 **Compare API Responses**", use_container_width=True):
            if not url1 or not url2:
                st.warning("Please provide both Source and Target API URLs.")
            else:
                with st.spinner("Comparing APIs..."):
                    try:
                        payload = {
                            "method": method.lower(),
                            "source_url": url1,
                            "target_url": url2,
                            "source_params": params1,
                            "target_params": params2,
                            "source_body": body1.strip() if body1.strip() else None,
                            "target_body": body2.strip() if body2.strip() else None,
                            "source_auth": source_auth_config,
                            "target_auth": target_auth_config
                        }

                        response = requests.post(f"{API_BASE_URL}/api/v1/compare", json=payload)

                        if response.status_code == 200:
                            result = response.json()
                            st.session_state["latest"] = result
                            if "history" not in st.session_state:
                                st.session_state["history"] = []
                            st.session_state["history"].insert(0, result)
                            st.success("Comparison successful! View results in the 'Results & History' tab.")
                        else:
                            st.error(f"API Comparison failed ({response.status_code}): {response.text}")
                    except Exception as e:
                        st.error(f"Error during API comparison: {str(e)}")

        st.header("Direct Body Comparison")
        with st.expander("**Direct Body Comparison**"):
            d_col1, d_col2 = st.columns(2)
            direct_body1 = d_col1.text_area("**Source Body**", height=150, key="direct_body1")
            direct_body2 = d_col2.text_area("**Target Body**", height=150, key="direct_body2")

            if st.button("🔍 Compare Bodies Directly", use_container_width=True):
                if not direct_body1.strip() or not direct_body2.strip():
                    st.warning("Please provide content in both bodies.")
                else:
                    with st.spinner("Comparing bodies..."):
                        direct_result = {
                            'source_response': direct_body1,
                            'target_response': direct_body2,
                            'id': f"direct_{str(uuid.uuid4())[:8]}",
                            'content_type1': detect_content_type(direct_body1),
                            'content_type2': detect_content_type(direct_body2),
                        }
                        st.session_state["latest"] = direct_result
                        if "history" not in st.session_state:
                            st.session_state["history"] = []
                        st.session_state["history"].insert(0, direct_result)
                        st.success("Direct body comparison successful! View results.")

    with results_tab:
        st.header("Results & History")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 **Fetch Latest**", use_container_width=True, key="fetch_latest_button"):
                with st.spinner("Fetching latest comparison..."):
                    latest_result = get_latest_comparison()
                    if latest_result:
                        st.session_state["latest"] = latest_result
                        st.success("Fetched the latest result.")

        with col2:
            if st.button("📜 **View Full History**", use_container_width=True, key="view_history_button"):
                with st.spinner("Fetching comparison history..."):
                    st.session_state["history"] = get_comparison_history()
                    st.success("History updated.")

        st.markdown("---")

        st.subheader("Latest Comparison Result")
        latest = st.session_state.get("latest")
        if latest:
            show_comparison_result(latest, "latest_result")
        else:
            st.info("No comparison results available. Run a new comparison or fetch the latest.")

        st.subheader("Comparison History")
        history = st.session_state.get("history", [])
        if not history:
            st.info("No history to display. Run a comparison or view history.")
        else:
            for i, item in enumerate(history):
                if latest and item.get("id") == latest.get("id"):
                    continue
                timestamp = item.get('created_at', f"Item {i}")
                with st.expander(f"ID: {item.get('id', 'N/A')} | Timestamp: {timestamp}"):
                    show_comparison_result(item, item.get('id', i))


if __name__ == "__main__":
    show_dashboard()