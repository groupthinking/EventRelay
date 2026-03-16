import requests
import json
import time

BASE_URL = "http://localhost:8001"

def test_async_pipeline(video_url):
    print("--- Testing Async Pipeline with URL: " + video_url + " ---")
    
    # 1. Start processing
    print("1. Starting background video process...")
    res = requests.post(f"{BASE_URL}/api/v1/videos/process", json={"video_url": video_url})
    if res.status_code != 200:
        print(f"Failed to start process: {res.status_code}")
        print(res.text)
        return
        
    data = res.json()
    job_id = data.get("data", {}).get("job_id")
    if not job_id:
        print("Failed to get job_id")
        return
        
    print(f"Started job ID: {job_id}")
    
    # 2. Poll status
    print("2. Polling for completion...")
    status = "pending"
    max_retries = 30
    attempts = 0
    job_data = None
    
    while status not in ["complete", "failed"] and attempts < max_retries:
        time.sleep(5)
        res = requests.get(f"{BASE_URL}/api/v1/videos/{job_id}/status")
        if res.status_code == 200:
            job_data = res.json().get("data", {})
            status = job_data.get("status")
            progress = job_data.get("progress", 0)
            print(f"   Status: {status}, Progress: {progress}%")
        else:
            print(f"   Failed to poll status: {res.status_code}")
        attempts += 1
        
    if status != "complete":
        print(f"Job failed or timed out. Status: {status}")
        return
        
    print("Job completed successfully! Now testing event extraction...")
    
    # 3. Extract events using job_id
    res = requests.post(f"{BASE_URL}/api/v1/events/extract", json={"job_id": job_id})
    if res.status_code != 200:
        print(f"Failed to extract events: {res.status_code}")
        print(res.text)
        return
        
    events_data = res.json().get("data", {})
    events = events_data.get("events", [])
    print(f"Extracted {len(events)} events.")
    for i, evt in enumerate(events[:3]): # print up to 3
        print(f"  - [{evt.get('type')}] {evt.get('title')}")
        
    if not events:
        print("No events extracted, skipping dispatch.")
        return
        
    print("4. Testing Agent Dispatch...")
    # 4. Dispatch Agents
    dispatch_res = requests.post(f"{BASE_URL}/api/v1/agents/dispatch", json={
        "events": events[:2],
        "agent_types": ["analyzer"]
    })
    
    if dispatch_res.status_code == 200:
        dispatch_data = dispatch_res.json().get("data", {})
        dispatch_id = dispatch_data.get("dispatch_id")
        executions = dispatch_data.get("executions", [])
        print(f"Successfully dispatched agents. Dispatch ID: {dispatch_id}")
        for exe in executions:
            print(f"  - Agent ID: {exe.get('agent_id')} ({exe.get('status')})")
            
        # Poll agent status
        if executions:
            agent_id = executions[0].get('agent_id')
            print(f"Polling agent execution {agent_id}...")
            time.sleep(3)
            status_res = requests.get(f"{BASE_URL}/api/v1/agents/{agent_id}/status")
            if status_res.status_code == 200:
                print("Agent Status Response:")
                print(json.dumps(status_res.json(), indent=2)[:300] + "...")
    else:
        print(f"Failed to dispatch agents: {dispatch_res.status_code}")
        print(dispatch_res.text)

if __name__ == "__main__":
    urls = [
        "https://youtu.be/b1mjQIiH7r4?si=dr6ohW2Zu2MRO4aK",
        "https://www.youtube.com/watch?v=cNf7uVff11Y&t=2s"
    ]
    for url in urls:
        test_async_pipeline(url)
