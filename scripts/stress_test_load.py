
import threading
import requests
import time
import random
import sys

# Configuration
BASE_URL = "http://localhost"
NUM_TECH = 12
TEST_DURATION_SEC = 20
TARGET_INCIDENT_ID = 1

def simulate_tech(tech_id):
    username = f"test_tech_{tech_id}"
    password = "password123"
    
    session = requests.Session()
    
    try:
        # 1. Establish session and GET cookie
        resp = session.get(f"{BASE_URL}/")
        print(f"Tech {tech_id}: Initial hit cookies: {session.cookies.get_dict()}")
        
        # 2. GET Login page for CSRF
        r = session.get(f"{BASE_URL}/login")
        csrf_token = ""
        if 'name="csrf_token" value="' in r.text:
            csrf_token = r.text.split('name="csrf_token" value="')[1].split('"')[0]
        
        if not csrf_token:
            print(f"Tech {tech_id}: CSRF token NOT FOUND")
            return

        # 3. POST Login
        r = session.post(f"{BASE_URL}/login", data={
            "username": username,
            "password": password,
            "csrf_token": csrf_token
        }, allow_redirects=True)
        
        if "Tableau de bord" not in r.text and "Dashboard" not in r.text:
            print(f"Tech {tech_id}: Login failed. Response: {r.status_code}. Content: {r.text[:200]}")
            return
            
        print(f"Tech {tech_id}: Logged in.")
    except Exception as e:
        print(f"Tech {tech_id}: Error: {e}")
        return

    start_time = time.time()
    stats = {"success": 0, "conflict": 0, "error": 0}
    
    while time.time() - start_time < TEST_DURATION_SEC:
        try:
            r = session.get(f"{BASE_URL}/") 
            version = None
            if f'data-incident-id="{TARGET_INCIDENT_ID}"' in r.text:
                block = r.text.split(f'data-incident-id="{TARGET_INCIDENT_ID}"')[1]
                if 'data-version="' in block:
                    version = block.split('data-version="')[1].split('"')[0]
            
            if version is None:
                stats["error"] += 1
                time.sleep(1)
                continue

            note_content = f"Update by Tech {tech_id} at {time.strftime('%H:%M:%S')}"
            update_url = f"{BASE_URL}/incident/edit_note_inline/{TARGET_INCIDENT_ID}"
            
            csrf_token = ""
            if 'name="csrf_token" value="' in r.text:
                csrf_token = r.text.split('name="csrf_token" value="')[1].split('"')[0]

            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "X-Incident-Version": version,
                "X-CSRFToken": csrf_token
            }
            
            update_data = {
                "note": note_content,
                "note_type": "tech",
                "csrf_token": csrf_token
            }
            
            r_update = session.post(update_url, data=update_data, headers=headers)
            
            if r_update.status_code == 200:
                stats["success"] += 1
            elif r_update.status_code == 409:
                stats["conflict"] += 1
            else:
                stats["error"] += 1
                
        except Exception as e:
            stats["error"] += 1
            
        time.sleep(random.uniform(0.5, 1.5))

    print(f"Tech {tech_id} Finished. Stats: {stats}")

def run_stress_test():
    threads = []
    print(f"Starting stress test with {NUM_TECH} technicians for {TEST_DURATION_SEC}s...")
    for i in range(1, NUM_TECH + 1):
        t = threading.Thread(target=simulate_tech, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.1)
        
    for t in threads:
        t.join()
    print("Stress test completed.")

if __name__ == "__main__":
    run_stress_test()
