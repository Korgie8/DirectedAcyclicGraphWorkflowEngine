import time
import threading
import requests
import logging
from signalrcore.hub_connection_builder import HubConnectionBuilder

BASE_URL = "http://localhost:5147"
MISSION_ID = "AssemblyLine_Alpha"

def process_task(task_id, hub):
    # 1. Claim it immediately
    print(f"\n[Client] Claiming task: '{task_id}'...")
    hub.send("ReportTaskStarted", [MISSION_ID, task_id])
    
    # 2. Simulate the work without blocking the main event loop
    time.sleep(1.5) 
    
    # 3. Report completion
    print(f"[Client] Task '{task_id}' completed. Reporting to engine hub.")
    hub.send("ReportTaskDone", [MISSION_ID, task_id])

def execute_next_handler(args):
    ready_tasks = args[0]
    
    if not ready_tasks:
        print("\n[Client] No ready tasks available.")
        return

    for task in ready_tasks:
        task_id = task.get("id") or task.get("Id")
        # Spin up a separate thread for each task
        threading.Thread(target=process_task, args=(task_id, hub_connection)).start()

payload = [
    {"Id": "BootSensors", "Dependencies": []},
    {"Id": "PowerMotors", "Dependencies": []},
    {"Id": "MoveArm", "Dependencies": ["BootSensors", "PowerMotors"]},
    {"Id": "EngageClaw", "Dependencies": ["MoveArm"]},
    {"Id": "RetractArm", "Dependencies": ["EngageClaw"]}
]

print(f"Starting mission '{MISSION_ID}' via REST API...")
response = requests.post(f"{BASE_URL}/api/engine/start/{MISSION_ID}", json=payload)

if response.status_code != 200:
    print(f"Failed to start mission. Server responded: {response.text}")
    exit(1)

initial_ready_tasks = response.json()

hub_url = f"{BASE_URL}/engine-socket"
hub_connection = HubConnectionBuilder()\
    .with_url(hub_url)\
    .configure_logging(logging_level=logging.ERROR)\
    .build()

hub_connection.on("ExecuteNext", execute_next_handler)
hub_connection.start()

time.sleep(1) 

# Kick off initial tasks
execute_next_handler([initial_ready_tasks])

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    hub_connection.stop()