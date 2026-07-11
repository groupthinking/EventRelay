import csv
import json
import os
import re
import time
import uuid

import requests

from supabase import Client, create_client

# ==== CONFIGURATION ====
ABACUS_API_KEYS = [k.strip() for k in os.getenv('ABACUS_API_KEYS', '').split(',') if k.strip()]
if not ABACUS_API_KEYS:
    raise RuntimeError('ABACUS_API_KEYS environment variable is required (comma-separated)')
ABACUS_API_URL = 'https://api.abacus.ai'
AGENT_NAME = os.getenv('AGENT_NAME', 'abacus-agent')
API_REF_URL = 'https://abacus.ai/help/api/ref'

HEADERS = lambda api_key: {
    'apiKey': api_key,
    'Content-Type': 'application/json'
}

# ==== MCP CONTEXT ====
def create_mcp_context(operation, user=AGENT_NAME, parameters=None, parent=None):
    return {
        "contextId": f"mcp_{int(time.time())}_{uuid.uuid4().hex[:8]}",
        "operation": operation,
        "user": user,
        "timestamp": int(time.time()),
        "parameters": parameters or {},
        "parentContext": parent,
        "history": []
    }

def propagate_mcp(context, update=None):
    update = update or {}
    context = dict(context)
    context['history'] = context.get('history', []) + [update]
    context.update(update)
    return context

def log_analytics(context, result=None):
    # Log MCP context and result to a CSV file for analytics
    with open('mcp_analytics.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            context.get('timestamp'),
            context.get('contextId'),
            context.get('operation'),
            context.get('user'),
            json.dumps(context.get('parameters', {})),
            json.dumps(result) if result is not None else '',
            context.get('status', ''),
        ])

def log_mcp(context, result=None):
    print('[MCP] Context:', json.dumps(context, indent=2))
    if result is not None:
        print('[MCP] Result:', json.dumps(result, indent=2))
    log_analytics(context, result)

# ==== DOC SECTION CHECK ====
DOC_SECTIONS = [
    "overview", "use-cases", "connectors", "authentication", "getting-started-with-the-python-sdk", "api-reference", "ai_agents", "ai_chat", "algorithm", "annotations", "application_connectors", "batch_prediction", "code_completion", "custom_loss_function", "custom_metric", "database_connectors", "dataset", "deployment", "deployment_conversations", "docstore", "document_retrievers", "documentation", "eda", "external_app", "feature_drift", "feature_group", "feature_group_row_process", "feature_group_template", "file_connectors", "graph_dashboard", "holdout_analysis", "llm_apps", "model", "model_monitoring", "module", "natural_language_explanation", "organization", "pipelines", "predict", "prediction_operator", "project", "python_function", "refresh", "secrets", "streaming", "streaming_connectors", "upload", "user", "webhooks", "api-classes", "api-inputs", "documentation-chat-bot", "api-search", "how-to"
]

def check_doc_sections(mcp_context):
    results = {}
    for section in DOC_SECTIONS:
        # Try both hyphen and underscore variants
        variants = {section}
        if '-' in section:
            variants.add(section.replace('-', '_'))
        if '_' in section:
            variants.add(section.replace('_', '-'))
        for variant in variants:
            url = f"{API_REF_URL}/{variant}"
            try:
                resp = requests.get(url, timeout=5)
                results[variant] = resp.status_code
            except Exception as e:
                results[variant] = f"error: {str(e)}"
    log_mcp(propagate_mcp(mcp_context, {'operation': 'check_doc_sections', 'status': 'complete'}), results)
    return results

# ==== DYNAMIC ENDPOINT DISCOVERY ====
def discover_endpoints(mcp_context):
    try:
        resp = requests.get(API_REF_URL, timeout=10)
        resp.raise_for_status()
        # Find all /api/v0/ endpoints in the HTML
        endpoints = set(re.findall(r'/api/v0/[a-zA-Z0-9]+', resp.text))
        endpoints = list(endpoints)
        log_mcp(propagate_mcp(mcp_context, {'operation': 'discover_endpoints', 'status': 'success'}), endpoints)
        # Prioritize known useful endpoints
        prioritized = [e for e in endpoints if 'list' in e or 'get' in e]
        return prioritized or endpoints
    except Exception as e:
        log_mcp(propagate_mcp(mcp_context, {'operation': 'discover_endpoints', 'status': f'failed: {str(e)}'}))
        # Fallback to static list
        return [
            '/api/v0/listConnectors',
            '/api/v0/listProjects',
            '/api/v0/listProjectDatasets',
        ]

# ==== SELF-HEALING ENDPOINT LOGIC ====
def try_endpoints(api_key, mcp_context, endpoints):
    for endpoint in endpoints:
        try:
            response = requests.get(f'{ABACUS_API_URL}{endpoint}', headers=HEADERS(api_key))
            response.raise_for_status()
            data = response.json()
            log_mcp(propagate_mcp(mcp_context, {'endpoint': endpoint, 'status': 'success'}), data)
            return data, endpoint
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                log_mcp(propagate_mcp(mcp_context, {'endpoint': endpoint, 'status': '404 not found'}))
                continue  # Try next endpoint
            else:
                log_mcp(propagate_mcp(mcp_context, {'endpoint': endpoint, 'status': f'HTTP error {e.response.status_code}'}))
                raise
        except Exception as e:
            log_mcp(propagate_mcp(mcp_context, {'endpoint': endpoint, 'status': f'error: {str(e)}'}))
            continue
    # If all fail, escalate
    log_mcp(propagate_mcp(mcp_context, {'error': 'All endpoints failed, escalation triggered'}))
    return None, None

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://nsfrhirwsjqwhagtuaxx.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
if not SUPABASE_KEY:
    raise RuntimeError('SUPABASE_KEY environment variable is required')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upsert_to_supabase(table, records, mcp_context, ref_source=None):
    if not records:
        return
    # Add reference point to each record
    for rec in records:
        rec['ref_source'] = ref_source or 'abacus.ai'
    try:
        resp = supabase.table(table).upsert(records).execute()
        log_mcp(propagate_mcp(mcp_context, {'operation': f'upsert_{table}', 'status': 'success'}), {'count': len(records), 'response': str(resp)})
    except Exception as e:
        log_mcp(propagate_mcp(mcp_context, {'operation': f'upsert_{table}', 'status': f'error: {str(e)}'}))

def run_multistep_workflow(api_key, mcp_context):
    # Step 1: Fetch data from Abacus.ai (list projects)
    endpoints = ['/api/v0/listProjects']
    fetch_ctx = propagate_mcp(mcp_context, {'operation': 'fetch_projects'})
    data, endpoint = try_endpoints(api_key, fetch_ctx, endpoints)
    if not data or 'projects' not in data:
        print('No projects data found.')
    else:
        # Step 2: Process data (summarize project count)
        projects = data['projects']
        summary = f"Total projects: {len(projects)}"
        process_ctx = propagate_mcp(fetch_ctx, {'operation': 'summarize_projects', 'project_count': len(projects)})
        log_mcp(process_ctx, {'summary': summary})
        print('Summary:', summary)
        # Step 3: Store in Supabase
        upsert_to_supabase('projects', projects, process_ctx, ref_source='abacus.ai')

    # Step 4: Fetch and upsert chats
    chat_ctx = propagate_mcp(mcp_context, {'operation': 'fetch_chats'})
    chat_data, chat_endpoint = try_endpoints(api_key, chat_ctx, ['/api/v0/listChats'])
    if chat_data and 'chats' in chat_data:
        upsert_to_supabase('chats', chat_data['chats'], chat_ctx, ref_source='abacus.ai')
        log_mcp(propagate_mcp(chat_ctx, {'operation': 'upsert_chats', 'status': 'complete'}), {'count': len(chat_data['chats'])})
    else:
        log_mcp(propagate_mcp(chat_ctx, {'operation': 'upsert_chats', 'status': 'no data'}))

    # Step 5: Fetch and upsert files
    file_ctx = propagate_mcp(mcp_context, {'operation': 'fetch_files'})
    file_data, file_endpoint = try_endpoints(api_key, file_ctx, ['/api/v0/listFiles'])
    if file_data and 'files' in file_data:
        upsert_to_supabase('files', file_data['files'], file_ctx, ref_source='abacus.ai')
        log_mcp(propagate_mcp(file_ctx, {'operation': 'upsert_files', 'status': 'complete'}), {'count': len(file_data['files'])})
    else:
        log_mcp(propagate_mcp(file_ctx, {'operation': 'upsert_files', 'status': 'no data'}))

    # Step 6: Fetch and upsert media
    media_ctx = propagate_mcp(mcp_context, {'operation': 'fetch_media'})
    media_data, media_endpoint = try_endpoints(api_key, media_ctx, ['/api/v0/listMedia'])
    if media_data and 'media' in media_data:
        upsert_to_supabase('media', media_data['media'], media_ctx, ref_source='abacus.ai')
        log_mcp(propagate_mcp(media_ctx, {'operation': 'upsert_media', 'status': 'complete'}), {'count': len(media_data['media'])})
    else:
        log_mcp(propagate_mcp(media_ctx, {'operation': 'upsert_media', 'status': 'no data'}))

    # Step 7: (Placeholder) Send summary notification (e.g., Slack/email)
    notify_ctx = propagate_mcp(mcp_context, {'operation': 'notify_summary'})
    log_mcp(notify_ctx, {'notification': 'Summary notification would be sent here.'})
    print('Notification step complete (placeholder).')

def main_agent():
    # Load or create MCP context
    mcp_env = os.getenv('MCP_CONTEXT')
    if mcp_env:
        mcp_context = json.loads(mcp_env)
    else:
        mcp_context = create_mcp_context('agent_start')
    log_mcp(mcp_context)

    print(f"🚀 Agent Started: {AGENT_NAME} Cycling API Keys...")

    # Check doc sections
    doc_section_results = check_doc_sections(mcp_context)
    print(f"🔎 Doc section status: {doc_section_results}")

    endpoints = discover_endpoints(mcp_context)
    print(f"🔎 Discovered endpoints: {endpoints}")

    for idx, api_key in enumerate(ABACUS_API_KEYS, start=1):
        if not api_key.strip():
            continue
        # Never log key material (even a prefix); reference the key by index only.
        print(f"\n🔑 Using API Key #{idx}")
        try:
            data, endpoint = try_endpoints(api_key, mcp_context, endpoints)
            if data is None:
                print(f"⚠️ All endpoints failed for API Key #{idx}")
                continue
            print(f"✅ Success with endpoint {endpoint}. Data: {json.dumps(data)[:200]}...")
            # Run multi-step workflow for demonstration
            run_multistep_workflow(api_key, mcp_context)
        except Exception as e:
            print(f"❌ API Key #{idx} failed: {str(e)}")
    print("\n🎯 Agent Cycle Complete!")

if __name__ == "__main__":
    main_agent()
