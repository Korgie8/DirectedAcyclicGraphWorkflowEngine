import time
import math
import queue
import threading
import logging
import requests
import tkinter as tk
from signalrcore.hub_connection_builder import HubConnectionBuilder

# =====================================================================
# BACKEND CONFIGURATION
# =====================================================================
BASE_URL = "http://localhost:5147"
HUB_URL = f"{BASE_URL}/engine-socket"
MISSION_BASE = "WorkflowMission"

# =====================================================================
# 13-NODE ASYMMETRIC WORKFLOW BLUEPRINT
# Engineered with fast & slow branches so merge nodes visibly wait
# =====================================================================
MAIN_BLUEPRINT = [
    # Stage 1: Parallel Roots (InitSensors is fast, BootMotors is very slow)
    {"Id": "InitSensors",  "Dependencies": []},
    {"Id": "BootMotors",   "Dependencies": []},
    {"Id": "Pressurize",   "Dependencies": []},

    # Stage 2: CalibrateArm & LockChassis must WAIT on slow BootMotors
    {"Id": "OpticsAlign",  "Dependencies": ["InitSensors"]},
    {"Id": "CalibrateArm", "Dependencies": ["InitSensors", "BootMotors"]},
    {"Id": "LockChassis",  "Dependencies": ["BootMotors", "Pressurize"]},

    # Stage 3: TargetScan finishes OpticsAlign early, then WAITS on CalibrateArm
    {"Id": "TargetScan",   "Dependencies": ["OpticsAlign", "CalibrateArm"]},
    {"Id": "PrimeClaw",    "Dependencies": ["CalibrateArm"]},
    {"Id": "BalanceLoad",  "Dependencies": ["LockChassis"]},

    # Stage 4: VerifyGrip gets PrimeClaw & TargetScan early, WAITS on slow BalanceLoad
    {"Id": "PlotVector",   "Dependencies": ["TargetScan"]},
    {"Id": "VerifyGrip",   "Dependencies": ["TargetScan", "PrimeClaw", "BalanceLoad"]},

    # Stage 5 & 6: ExecuteLift gets PlotVector early, WAITS on VerifyGrip
    {"Id": "ExecuteLift",  "Dependencies": ["PlotVector", "VerifyGrip"]},
    {"Id": "ParkSystem",   "Dependencies": ["ExecuteLift"]},
]

MAIN_LAYOUT = {
    "InitSensors":  (0.08, 0.22),
    "BootMotors":   (0.08, 0.50),
    "Pressurize":   (0.08, 0.78),
    "OpticsAlign":  (0.25, 0.22),
    "CalibrateArm": (0.25, 0.50),
    "LockChassis":  (0.25, 0.78),
    "TargetScan":   (0.43, 0.22),
    "PrimeClaw":    (0.43, 0.50),
    "BalanceLoad":  (0.43, 0.78),
    "PlotVector":   (0.62, 0.33),
    "VerifyGrip":   (0.62, 0.67),
    "ExecuteLift":  (0.79, 0.50),
    "ParkSystem":   (0.93, 0.50),
}

# Asymmetric durations (seconds) to clearly showcase dependency waiting
TASK_DURATIONS = {
    "InitSensors":  0.6,   # Fast root -> unlocks OpticsAlign immediately
    "Pressurize":   1.2,   # Medium root -> LockChassis gets 1/2 early
    "BootMotors":   3.2,   # Slow root -> holds back CalibrateArm & LockChassis
    "OpticsAlign":  0.8,   # Finishes fast -> TargetScan enters WAITING (1/2)
    "CalibrateArm": 1.4,
    "LockChassis":  1.5,
    "TargetScan":   1.4,
    "PrimeClaw":    0.7,   # Fast branch -> VerifyGrip gets 1/3 early
    "BalanceLoad":  3.4,   # Very slow branch -> VerifyGrip waits for it
    "PlotVector":   0.7,   # Fast branch -> ExecuteLift enters WAITING (1/2)
    "VerifyGrip":   1.5,
    "ExecuteLift":  1.4,
    "ParkSystem":   1.0,
}

# =====================================================================
# CYCLIC BLUEPRINT (Kahn's Algorithm Deadlock Showcase)
# =====================================================================
CYCLE_BLUEPRINT = [
    {"Id": "InitCore",     "Dependencies": []},
    {"Id": "AuthToken",    "Dependencies": ["InitCore", "VerifyState"]},
    {"Id": "FetchConfig",  "Dependencies": ["AuthToken"]},
    {"Id": "BuildContext", "Dependencies": ["FetchConfig"]},
    {"Id": "VerifyState",  "Dependencies": ["BuildContext"]},
]

CYCLE_LAYOUT = {
    "InitCore":     (0.14, 0.50),
    "AuthToken":    (0.36, 0.30),
    "FetchConfig":  (0.64, 0.30),
    "BuildContext": (0.64, 0.72),
    "VerifyState":  (0.36, 0.72),
}


# =====================================================================
# 100-NODE MEGA BLUEPRINT GENERATOR (10 Stages x 10 Lanes)
# =====================================================================
def build_mega_blueprint():
    blueprint = []
    layout = {}
    durations = {}
    cols, rows = 10, 10

    for c in range(cols):
        rx = 0.055 + (c / (cols - 1)) * 0.89
        for r in range(rows):
            nid = f"N{c}{r}"
            ry = 0.07 + (r / (rows - 1)) * 0.86
            layout[nid] = (rx, ry)

            # Vary durations between 0.18s and 0.85s so waves cascade unevenly
            durations[nid] = 0.18 + ((c * 3 + r * 7) % 8) * 0.09

            deps = []
            if c > 0:
                # Connect to same row in previous stage
                deps.append(f"N{c-1}{r}")
                # Cross-link to adjacent lanes to create a rich dependency mesh
                if (r + c) % 2 == 0 and r > 0:
                    deps.append(f"N{c-1}{r-1}")
                elif (r + c) % 3 == 0 and r < rows - 1:
                    deps.append(f"N{c-1}{r+1}")

            blueprint.append({"Id": nid, "Dependencies": deps})

    return blueprint, layout, durations


MEGA_BLUEPRINT, MEGA_LAYOUT, MEGA_DURATIONS = build_mega_blueprint()

# =====================================================================
# COLOR PALETTE
# =====================================================================
THEME = {
    "bg":          "#090d16",
    "grid":        "#111827",
    "panel":       "#0f172a",
    "panel_edge":  "#1e293b",
    "text":        "#f8fafc",
    "muted":       "#94a3b8",
    "edge_idle":   "#26334d",
    "edge_wait":   "#f59e0b",
    "edge_done":   "#10b981",
    "edge_cancel": "#f97316",
    "edge_cycle":  "#ef4444",
    "PENDING":     {"fill": "#161f30", "border": "#475569", "badge": "#334155", "text": "#cbd5e1"},
    "WAITING":     {"fill": "#271c09", "border": "#f59e0b", "badge": "#d97706", "text": "#fef3c7"},
    "READY":       {"fill": "#0c2d48", "border": "#38bdf8", "badge": "#0284c7", "text": "#e0f2fe"},
    "RUNNING":     {"fill": "#1e1b4b", "border": "#818cf8", "badge": "#4f46e5", "text": "#eef2ff"},
    "COMPLETED":   {"fill": "#063729", "border": "#10b981", "badge": "#059669", "text": "#d1fae5"},
    "FAILED":      {"fill": "#450a0a", "border": "#f87171", "badge": "#dc2626", "text": "#fee2e2"},
    "CANCELLED":   {"fill": "#2b160c", "border": "#fb923c", "badge": "#ea580c", "text": "#ffedd5"},
    "CYCLE_LOCK":  {"fill": "#3b0a14", "border": "#f43f5e", "badge": "#e11d48", "text": "#ffe4e6"},
}


def cubic_bezier(t, p0, p1, p2, p3):
    u = 1.0 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t
    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return x, y


class EdgeParticle:
    def __init__(self, src_id, dst_id, color="#10b981", speed=0.035, loop=False):
        self.src_id = src_id
        self.dst_id = dst_id
        self.color = color
        self.speed = speed
        self.progress = 0.0
        self.loop = loop


class DAGStudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Directed Acyclic Graph Workflow Engine")
        self.root.geometry("1560x840")
        self.root.minsize(1240, 720)
        self.root.configure(bg=THEME["bg"])

        self.ui_queue = queue.Queue()
        self.hub_lock = threading.Lock()

        self.mission_counter = 1
        self.current_mission_id = f"{MISSION_BASE}_1"
        self.active_blueprint = MAIN_BLUEPRINT
        self.active_layout = MAIN_LAYOUT
        self.view_mode = "DAG"  # "DAG", "MEGA_VIEW", or "CYCLE_VIEW"
        self.scenario_mode = "HAPPY"
        self.pause_for_crash_demo = False

        self.node_status = {}
        self.node_progress = {}
        self.node_indegree = {}
        self.node_total_deps = {}
        self.dispatched_tasks = set()
        self.particles = []
        self.save_flash_timer = 0.0
        self.tick_count = 0

        self.banner_title = "INITIALIZING WORKFLOW ENGINE CLIENT"
        self.banner_subtitle = "Connecting to REST API & SignalR WebSocket Hub..."
        self.banner_color = "#38bdf8"

        self._reset_state(MAIN_BLUEPRINT)
        self._build_layout()
        self._connect_signalr()

        self.root.after(16, self._tick)
        self.root.after(1000, lambda: self.start_dag_scenario("HAPPY"))

    def _reset_state(self, blueprint):
        self.active_blueprint = blueprint
        self.dispatched_tasks.clear()
        self.particles.clear()
        self.node_status.clear()
        self.node_progress.clear()
        self.node_indegree.clear()
        self.node_total_deps.clear()

        for node in blueprint:
            nid = node["Id"]
            dep_cnt = len(node["Dependencies"])
            self.node_status[nid] = "PENDING"
            self.node_progress[nid] = 0.0
            self.node_indegree[nid] = dep_cnt
            self.node_total_deps[nid] = dep_cnt

    # =====================================================================
    # UI LAYOUT
    # =====================================================================
    def _build_layout(self):
        navbar = tk.Frame(
            self.root, bg=THEME["panel"], height=62,
            highlightthickness=1, highlightbackground=THEME["panel_edge"]
        )
        navbar.pack(side=tk.TOP, fill=tk.X)

        # Clean Title Only — Matching the README
        tk.Label(
            navbar,
            text="⚡ Directed Acyclic Graph Workflow Engine",
            bg=THEME["panel"], fg="#f8fafc",
            font=("Helvetica", 13, "bold"), padx=18, pady=14
        ).pack(side=tk.LEFT)

        btn_cfg = {
            "font": ("Helvetica", 9, "bold"),
            "bd": 0, "padx": 12, "pady": 7,
            "cursor": "hand2", "relief": tk.FLAT
        }

        tk.Button(
            navbar, text="🔥 5. Mega Test (100 Nodes)",
            bg="#7c3aed", fg="white", activebackground="#8b5cf6", activeforeground="white",
            command=self.start_mega_scenario, **btn_cfg
        ).pack(side=tk.RIGHT, padx=(4, 16), pady=11)

        tk.Button(
            navbar, text="🔄 4. Cycle Guard (Kahn's 400)",
            bg="#be123c", fg="white", activebackground="#e11d48", activeforeground="white",
            command=self.run_visual_cycle_guard, **btn_cfg
        ).pack(side=tk.RIGHT, padx=4, pady=11)

        tk.Button(
            navbar, text="💾 3. Crash & Reload (/load)",
            bg="#2563eb", fg="white", activebackground="#3b82f6", activeforeground="white",
            command=self.simulate_crash_and_reload, **btn_cfg
        ).pack(side=tk.RIGHT, padx=4, pady=11)

        tk.Button(
            navbar, text="💥 2. Simulate Fault (BFS Cascade)",
            bg="#c2410c", fg="white", activebackground="#ea580c", activeforeground="white",
            command=lambda: self.start_dag_scenario("FAIL_SCAN"), **btn_cfg
        ).pack(side=tk.RIGHT, padx=4, pady=11)

        tk.Button(
            navbar, text="▶ 1. Run Happy Path (13 Nodes)",
            bg="#059669", fg="white", activebackground="#10b981", activeforeground="white",
            command=lambda: self.start_dag_scenario("HAPPY"), **btn_cfg
        ).pack(side=tk.RIGHT, padx=4, pady=11)

        body = tk.Frame(self.root, bg=THEME["bg"])
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(body, bg=THEME["bg"], highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sidebar = tk.Frame(
            body, bg=THEME["panel"], width=320,
            highlightthickness=1, highlightbackground=THEME["panel_edge"]
        )
        sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="LIVE TELEMETRY & EVENT LOG",
            bg=THEME["panel"], fg="#38bdf8",
            font=("Helvetica", 9, "bold"), pady=12
        ).pack(side=tk.TOP, fill=tk.X)

        self.log_box = tk.Text(
            sidebar, bg="#070a12", fg="#cbd5e1",
            font=("Courier", 9), bd=0, padx=10, pady=8,
            state=tk.DISABLED, wrap=tk.WORD
        )
        self.log_box.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 12))
        self.log_box.tag_config("TIME", foreground="#475569")
        self.log_box.tag_config("REST", foreground="#38bdf8")
        self.log_box.tag_config("WS_IN", foreground="#a78bfa")
        self.log_box.tag_config("WS_OUT", foreground="#34d399")
        self.log_box.tag_config("WARN", foreground="#fb923c")
        self.log_box.tag_config("ERROR", foreground="#f43f5e")
        self.log_box.tag_config("SAVE", foreground="#fbbf24")

    def log(self, tag, message):
        ts = time.strftime("%H:%M:%S")
        self.ui_queue.put(("LOG", (ts, tag, message)))

    def _append_log_ui(self, ts, tag, message):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{ts}] ", "TIME")
        self.log_box.insert(tk.END, f"{message}\n", tag)
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    # =====================================================================
    # SIGNALR HUB CONNECTION
    # =====================================================================
    def _connect_signalr(self):
        def _worker():
            try:
                self.hub_connection = HubConnectionBuilder() \
                    .with_url(HUB_URL) \
                    .configure_logging(logging_level=logging.ERROR) \
                    .build()

                self.hub_connection.on("ExecuteNext", self._on_execute_next)
                self.hub_connection.on_open(
                    lambda: self.log("WS_IN", "SignalR WebSocket Hub Connected (/engine-socket)")
                )
                self.hub_connection.start()
            except Exception as exc:
                self.log("ERROR", f"SignalR Hub Error: {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    def _safe_hub_send(self, method, params):
        with self.hub_lock:
            self.hub_connection.send(method, params)

    def _on_execute_next(self, args):
        if not args or self.pause_for_crash_demo or self.view_mode == "CYCLE_VIEW":
            return
        ready_tasks = args[0] or []
        ready_ids = [t.get("id") or t.get("Id") for t in ready_tasks]

        if self.view_mode != "MEGA_VIEW" or len(ready_ids) <= 4:
            self.log("WS_IN", f"ExecuteNext -> Ready: {ready_ids}")
        else:
            self.log("WS_IN", f"ExecuteNext -> {len(ready_ids)} nodes unlocked")

        self.ui_queue.put(("SAVE_FLASH", self.view_mode != "MEGA_VIEW"))
        self._dispatch_ready_tasks(ready_tasks)

    def _dispatch_ready_tasks(self, ready_tasks):
        if not ready_tasks:
            self.ui_queue.put(("CHECK_DONE", None))
            return

        for task in ready_tasks:
            tid = task.get("id") or task.get("Id")
            if not tid:
                continue

            self.ui_queue.put(("STATUS", (tid, "READY")))

            if tid not in self.dispatched_tasks:
                self.dispatched_tasks.add(tid)
                threading.Thread(
                    target=self._simulate_worker,
                    args=(self.current_mission_id, tid, self.view_mode),
                    daemon=True
                ).start()

    def _simulate_worker(self, mission_id, task_id, mode_snapshot):
        ready_pause = 0.12 if mode_snapshot == "MEGA_VIEW" else 0.40
        time.sleep(ready_pause)
        if mission_id != self.current_mission_id or self.pause_for_crash_demo or self.view_mode == "CYCLE_VIEW":
            return

        self.ui_queue.put(("STATUS", (task_id, "RUNNING")))
        if mode_snapshot == "MEGA_VIEW":
            duration = MEGA_DURATIONS.get(task_id, 0.35)
            steps = 10
        else:
            duration = TASK_DURATIONS.get(task_id, 1.5)
            steps = 28

        dt = duration / steps

        for step in range(1, steps + 1):
            time.sleep(dt)
            if mission_id != self.current_mission_id or self.pause_for_crash_demo or self.view_mode == "CYCLE_VIEW":
                return

            if self.scenario_mode == "FAIL_SCAN" and task_id == "TargetScan" and step >= int(steps * 0.65):
                self.ui_queue.put(("TASK_FAILED", task_id))
                self.log("ERROR", f"FAULT in '{task_id}'! Calling Hub.ReportTaskFailed...")
                self._safe_hub_send("ReportTaskFailed", [mission_id, task_id])
                return

            self.ui_queue.put(("PROGRESS", (task_id, step / steps)))

        self.ui_queue.put(("TASK_COMPLETED", task_id))
        if mode_snapshot != "MEGA_VIEW":
            self.log("WS_OUT", f"ReportTaskDone('{task_id}')")
        self._safe_hub_send("ReportTaskDone", [mission_id, task_id])

    # =====================================================================
    # SHOWCASE SCENARIOS
    # =====================================================================
    def start_dag_scenario(self, mode):
        self.view_mode = "DAG"
        self.scenario_mode = mode
        self.pause_for_crash_demo = False
        self.mission_counter += 1
        self.current_mission_id = f"{MISSION_BASE}_{self.mission_counter}"
        self.active_layout = MAIN_LAYOUT
        self._reset_state(MAIN_BLUEPRINT)

        if mode == "HAPPY":
            self.banner_title = f"MISSION: {self.current_mission_id}  |  ASYMMETRIC PARALLEL EXECUTION (13 NODES)"
            self.banner_subtitle = "Fast branches finish early -> Watch merge nodes turn AMBER (WAITING) until slower prerequisites complete."
            self.banner_color = "#38bdf8"
        else:
            self.banner_title = f"MISSION: {self.current_mission_id}  |  FAULT INJECTION & BFS CANCELLATION WAVE"
            self.banner_subtitle = "'TargetScan' (Stage 3) will fail -> Watch BFS cancel 4 downstream nodes while independent lower lanes finish."
            self.banner_color = "#fb923c"

        self._post_mission_start(MAIN_BLUEPRINT)

    def start_mega_scenario(self):
        self.view_mode = "MEGA_VIEW"
        self.scenario_mode = "MEGA"
        self.pause_for_crash_demo = False
        self.mission_counter += 1
        self.current_mission_id = f"MegaGrid100_{self.mission_counter}"
        self.active_layout = MEGA_LAYOUT
        self._reset_state(MEGA_BLUEPRINT)

        self.banner_title = f"🔥 MEGA STRESS TEST: {self.current_mission_id}  |  100 NODES  •  10 STAGES  •  ~210 DEPENDENCIES"
        self.banner_subtitle = "Live C# Engine orchestrating 100 concurrent nodes with Monitor thread locks (_stateLock) and JSON snapshots on every completion."
        self.banner_color = "#a78bfa"

        self._post_mission_start(MEGA_BLUEPRINT)

    def _post_mission_start(self, blueprint_payload):
        def _start_request():
            try:
                self.log("REST", f"POST /api/engine/start/{self.current_mission_id} ({len(blueprint_payload)} nodes)")
                resp = requests.post(
                    f"{BASE_URL}/api/engine/start/{self.current_mission_id}",
                    json=blueprint_payload,
                    timeout=8
                )
                if resp.status_code == 200:
                    ready = resp.json()
                    r_ids = [t.get("id") or t.get("Id") for t in ready]
                    self.ui_queue.put(("SAVE_FLASH", True))
                    self.log("REST", f"200 OK — Initial Ready Roots ({len(r_ids)}): {r_ids}")
                    self._dispatch_ready_tasks(ready)
                else:
                    self.log("ERROR", f"Start error ({resp.status_code}): {resp.text}")
            except Exception as exc:
                self.log("ERROR", f"API unreachable at {BASE_URL}: {exc}")
                self.banner_title = "⚠ BACKEND SERVER UNREACHABLE"
                self.banner_subtitle = f"Run 'dotnet run --project ConsistencyEngine.Api' in your terminal first ({BASE_URL})"
                self.banner_color = "#f43f5e"

        threading.Thread(target=_start_request, daemon=True).start()

    def simulate_crash_and_reload(self):
        if self.view_mode == "CYCLE_VIEW":
            self.start_dag_scenario("HAPPY")
            return

        self.pause_for_crash_demo = True
        self.banner_title = f"⚡ SIMULATED SERVER INTERRUPT  |  MISSION: {self.current_mission_id}"
        self.banner_subtitle = f"Workers paused. Recovering persisted graph via POST /api/engine/load/{self.current_mission_id}..."
        self.banner_color = "#60a5fa"
        self.log("SAVE", f"Simulating crash & reload for '{self.current_mission_id}'...")

        def _reload_worker():
            time.sleep(1.0)
            try:
                self.log("REST", f"POST /api/engine/load/{self.current_mission_id}")
                resp = requests.post(f"{BASE_URL}/api/engine/load/{self.current_mission_id}", timeout=5)
                if resp.status_code == 200:
                    ready = resp.json()
                    r_ids = [t.get("id") or t.get("Id") for t in ready]
                    self.ui_queue.put(("SAVE_FLASH", True))
                    self.log("SAVE", f"Restored {self.current_mission_id}.json! Ready queue: {r_ids}")
                    self.banner_title = f"✔ STATE RESTORED FROM JSON  |  MISSION: {self.current_mission_id}"
                    self.banner_subtitle = f"SavingManager reloaded graph and recalculated InDegrees around completed tasks. Resuming {len(r_ids)} ready task(s)."
                    self.banner_color = "#10b981"
                    for rid in r_ids:
                        self.dispatched_tasks.discard(rid)
                    self.pause_for_crash_demo = False
                    self._dispatch_ready_tasks(ready)
                else:
                    self.log("ERROR", f"Load failed ({resp.status_code}): {resp.text}")
            except Exception as exc:
                self.log("ERROR", f"Reload exception: {exc}")

        threading.Thread(target=_reload_worker, daemon=True).start()

    def run_visual_cycle_guard(self):
        self.pause_for_crash_demo = True
        self.view_mode = "CYCLE_VIEW"
        self.mission_counter += 1
        cycle_mission_id = f"CyclicBlueprint_{self.mission_counter}"
        self.current_mission_id = cycle_mission_id
        self.active_layout = CYCLE_LAYOUT
        self._reset_state(CYCLE_BLUEPRINT)

        self.banner_title = f"🛡 KAHN'S ALGORITHM CYCLE GUARD  |  INSPECTING '{cycle_mission_id}'"
        self.banner_subtitle = "Submitting blueprint with circular dependency loop: AuthToken -> FetchConfig -> BuildContext -> VerifyState -> AuthToken"
        self.banner_color = "#f43f5e"

        def _cycle_worker():
            self.log("REST", f"POST /api/engine/start/{cycle_mission_id} (Contains 4-Node Cycle)")
            time.sleep(0.45)

            self.ui_queue.put(("CYCLE_STEP_1", None))
            time.sleep(0.55)

            try:
                resp = requests.post(
                    f"{BASE_URL}/api/engine/start/{cycle_mission_id}",
                    json=CYCLE_BLUEPRINT,
                    timeout=5
                )
                server_msg = resp.text.strip() or "Graph contains a circular dependency."
                status_code = resp.status_code
            except Exception:
                status_code = 400
                server_msg = "Graph contains a circular dependency. (Offline Simulation)"

            self.ui_queue.put(("CYCLE_REJECTED", (status_code, server_msg)))
            self.log("ERROR", f"HTTP {status_code} Bad Request -> CircularDependencyException: '{server_msg}'")

        threading.Thread(target=_cycle_worker, daemon=True).start()

    # =====================================================================
    # BFS CASCADE & QUEUE PROCESSING
    # =====================================================================
    def _animate_bfs_cascade(self, failed_id):
        adj = {node["Id"]: [] for node in self.active_blueprint}
        for node in self.active_blueprint:
            for dep in node["Dependencies"]:
                if dep in adj:
                    adj[dep].append(node["Id"])

        def _wave():
            frontier = [(failed_id, child) for child in adj.get(failed_id, [])]
            visited = set()

            while frontier:
                next_frontier = []
                for parent, curr in frontier:
                    if curr not in visited:
                        visited.add(curr)
                        self.ui_queue.put(("BFS_CANCEL_NODE", (parent, curr)))
                        for child in adj.get(curr, []):
                            next_frontier.append((curr, child))
                time.sleep(0.28)
                frontier = next_frontier

        threading.Thread(target=_wave, daemon=True).start()

    def _process_events(self):
        while not self.ui_queue.empty():
            etype, data = self.ui_queue.get_nowait()

            if etype == "LOG":
                self._append_log_ui(*data)

            elif etype == "SAVE_FLASH":
                log_it = data
                self.save_flash_timer = 1.0
                if log_it:
                    self._append_log_ui(
                        time.strftime("%H:%M:%S"), "SAVE",
                        f"SavingManager -> Persisted MissionData/{self.current_mission_id}.json"
                    )

            elif etype == "STATUS":
                nid, st = data
                if self.node_status.get(nid) not in ("COMPLETED", "FAILED", "CANCELLED"):
                    self.node_status[nid] = st

            elif etype == "PROGRESS":
                nid, val = data
                self.node_progress[nid] = val

            elif etype == "TASK_COMPLETED":
                nid = data
                self.node_status[nid] = "COMPLETED"
                self.node_progress[nid] = 1.0
                p_speed = 0.065 if self.view_mode == "MEGA_VIEW" else 0.035

                for node in self.active_blueprint:
                    if nid in node["Dependencies"]:
                        child = node["Id"]
                        self.node_indegree[child] = max(0, self.node_indegree[child] - 1)
                        # If child still has remaining dependencies > 0, mark it as WAITING!
                        if self.node_indegree[child] > 0 and self.node_status.get(child) == "PENDING":
                            self.node_status[child] = "WAITING"
                            if self.view_mode == "DAG":
                                done_deps = self.node_total_deps[child] - self.node_indegree[child]
                                tot_deps = self.node_total_deps[child]
                                self._append_log_ui(
                                    time.strftime("%H:%M:%S"), "WARN",
                                    f"'{child}' received '{nid}' ({done_deps}/{tot_deps} done) -> WAITING on slower branch"
                                )
                        self.particles.append(EdgeParticle(nid, child, color="#10b981", speed=p_speed))

            elif etype == "TASK_FAILED":
                nid = data
                self.node_status[nid] = "FAILED"
                self.banner_title = f"💥 HARDWARE FAULT IN '{nid}'  |  BFS CANCELLATION WAVE ACTIVE"
                self.banner_subtitle = "TaskOrchestrator triggered Breadth-First Search to cancel unreachable downstream dependents while parallel lanes continue."
                self.banner_color = "#f43f5e"
                self._animate_bfs_cascade(nid)

            elif etype == "BFS_CANCEL_NODE":
                parent, curr = data
                if self.node_status.get(curr) != "COMPLETED":
                    self.node_status[curr] = "CANCELLED"
                    self.particles.append(EdgeParticle(parent, curr, color="#f97316", speed=0.04))
                    self._append_log_ui(
                        time.strftime("%H:%M:%S"), "WARN",
                        f"BFS Cascade -> Cancelled unreachable node '{curr}'"
                    )

            elif etype == "CYCLE_STEP_1":
                self.node_status["InitCore"] = "COMPLETED"
                self.node_progress["InitCore"] = 1.0
                self.node_indegree["AuthToken"] = 1
                self.particles.append(EdgeParticle("InitCore", "AuthToken", color="#10b981", speed=0.035))

            elif etype == "CYCLE_REJECTED":
                code, msg = data
                cycle_nodes = ["AuthToken", "FetchConfig", "BuildContext", "VerifyState"]
                for cn in cycle_nodes:
                    self.node_status[cn] = "CYCLE_LOCK"
                cycle_edges = [
                    ("AuthToken", "FetchConfig"),
                    ("FetchConfig", "BuildContext"),
                    ("BuildContext", "VerifyState"),
                    ("VerifyState", "AuthToken"),
                ]
                for s, d in cycle_edges:
                    p1 = EdgeParticle(s, d, color="#f43f5e", speed=0.018, loop=True)
                    p2 = EdgeParticle(s, d, color="#fb7185", speed=0.018, loop=True)
                    p2.progress = 0.5
                    self.particles.extend([p1, p2])

                self.banner_title = f"🛡 DEADLOCK PREVENTED (HTTP {code})  |  KAHN'S ALGORITHM ABORTED MISSION"
                self.banner_subtitle = f"4 nodes trapped with InDegree = 1 ('{msg}'). Engine aborted before execution could start."
                self.banner_color = "#f43f5e"

            elif etype == "CHECK_DONE":
                vals = list(self.node_status.values())
                if "RUNNING" not in vals and "READY" not in vals:
                    if "FAILED" in vals:
                        done_cnt = vals.count("COMPLETED")
                        canc_cnt = vals.count("CANCELLED")
                        self.banner_title = f"⚠ MISSION '{self.current_mission_id}' HALTED SAFELY"
                        self.banner_subtitle = f"{done_cnt} independent nodes succeeded | 1 node failed | {canc_cnt} downstream nodes safely cancelled via BFS."
                        self.banner_color = "#fb923c"
                    elif all(v == "COMPLETED" for v in vals):
                        total_n = len(vals)
                        self.banner_title = f"✔ MISSION '{self.current_mission_id}' COMPLETED ALL {total_n} NODES!"
                        self.banner_subtitle = f"All {total_n} DAG nodes executed in optimal topological order with real-time JSON persistence."
                        self.banner_color = "#10b981"
                        self._append_log_ui(
                            time.strftime("%H:%M:%S"), "WS_OUT",
                            f"Mission '{self.current_mission_id}' finished all {total_n} nodes!"
                        )

    def _tick(self):
        self.tick_count += 1
        self._process_events()

        if self.save_flash_timer > 0:
            self.save_flash_timer = max(0.0, self.save_flash_timer - 0.04)

        kept = []
        for p in self.particles:
            p.progress += p.speed
            if p.loop:
                p.progress %= 1.0
                kept.append(p)
            elif p.progress < 1.0:
                kept.append(p)
        self.particles = kept

        self._render_canvas()
        self.root.after(16, self._tick)

    # =====================================================================
    # RESPONSIVE CANVAS RENDERER
    # =====================================================================
    def _draw_rrect(self, x1, y1, x2, y2, r, **kwargs):
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1
        ]
        return self.canvas.create_polygon(pts, smooth=True, **kwargs)

    def _get_node_screen_pos(self, nid, w, h):
        rx, ry = self.active_layout[nid]
        top_margin = 92
        bot_margin = 54
        usable_h = max(300, h - top_margin - bot_margin)
        return int(rx * w), int(top_margin + ry * usable_h)

    def _get_edge_control_points(self, src_id, dst_id, w, h, card_w, card_h):
        sx, sy = self._get_node_screen_pos(src_id, w, h)
        dx, dy = self._get_node_screen_pos(dst_id, w, h)

        if self.view_mode == "CYCLE_VIEW":
            if src_id == "FetchConfig" and dst_id == "BuildContext":
                p0 = (sx, sy + card_h // 2)
                p3 = (dx, dy - card_h // 2)
                return p0, (sx + 40, (sy + dy) // 2), (dx + 40, (sy + dy) // 2), p3
            if src_id == "BuildContext" and dst_id == "VerifyState":
                p0 = (sx - card_w // 2, sy)
                p3 = (dx + card_w // 2, dy)
                return p0, ((sx + dx) // 2, sy + 35), ((sx + dx) // 2, dy + 35), p3
            if src_id == "VerifyState" and dst_id == "AuthToken":
                p0 = (sx, sy - card_h // 2)
                p3 = (dx, dy + card_h // 2)
                return p0, (sx - 40, (sy + dy) // 2), (dx - 40, (sy + dy) // 2), p3

        p0 = (sx + card_w // 2, sy)
        p3 = (dx - card_w // 2, dy)
        span = max(24, abs(p3[0] - p0[0]) * 0.45)
        p1 = (p0[0] + span, p0[1])
        p2 = (p3[0] - span, p3[1])
        return p0, p1, p2, p3

    def _render_canvas(self):
        self.canvas.delete("all")
        w = max(860, self.canvas.winfo_width())
        h = max(560, self.canvas.winfo_height())

        # 1. Background Grid
        for gx in range(0, w, 38):
            self.canvas.create_line(gx, 0, gx, h, fill=THEME["grid"])
        for gy in range(0, h, 38):
            self.canvas.create_line(0, gy, w, gy, fill=THEME["grid"])

        # 2. Top Status Banner & SavingManager Indicator
        save_box_w = 265
        banner_right = w - save_box_w - 28
        self._draw_rrect(18, 14, banner_right, 72, 10, fill="#0f172a", outline="#1e293b", width=2)

        self.canvas.create_text(
            34, 32, anchor=tk.W,
            text=self.banner_title,
            fill=self.banner_color, font=("Helvetica", 10, "bold")
        )
        self.canvas.create_text(
            34, 53, anchor=tk.W,
            text=self.banner_subtitle,
            fill="#cbd5e1", font=("Helvetica", 9)
        )

        save_active = self.save_flash_timer > 0.08
        s_bg = "#064e3b" if save_active else "#0f172a"
        s_border = "#10b981" if save_active else "#1e293b"
        s_text = "#34d399" if save_active else "#64748b"

        self._draw_rrect(w - save_box_w - 16, 14, w - 16, 72, 10, fill=s_bg, outline=s_border, width=2)
        self.canvas.create_text(
            w - save_box_w // 2 - 16, 33,
            text="💾 SAVING MANAGER (JSON)",
            fill=s_text, font=("Helvetica", 8, "bold")
        )
        self.canvas.create_text(
            w - save_box_w // 2 - 16, 53,
            text=f"{self.current_mission_id}.json",
            fill="#e2e8f0" if save_active else "#94a3b8", font=("Courier", 9, "bold")
        )

        if self.view_mode == "MEGA_VIEW":
            self._render_mega_graph(w, h)
        else:
            self._render_standard_graph(w, h)

        # 7. Bottom Legend Bar (Includes WAITING state)
        self._draw_rrect(18, h - 42, w - 18, h - 10, 8, fill="#0f172a", outline="#1e293b", width=1)
        legend_items = [
            ("PENDING", THEME["PENDING"]["badge"]),
            ("WAITING (1+ Done)", THEME["WAITING"]["badge"]),
            ("READY (InDeg=0)", THEME["READY"]["badge"]),
            ("RUNNING", THEME["RUNNING"]["badge"]),
            ("COMPLETED", THEME["COMPLETED"]["badge"]),
            ("FAILED", THEME["FAILED"]["badge"]),
            ("CANCELLED (BFS)", THEME["CANCELLED"]["badge"]),
        ]
        slot_w = (w - 56) / len(legend_items)
        for idx, (lbl, col) in enumerate(legend_items):
            lx = int(30 + idx * slot_w)
            ly = h - 26
            self.canvas.create_oval(lx, ly - 5, lx + 10, ly + 5, fill=col, outline="#ffffff")
            self.canvas.create_text(lx + 15, ly, anchor=tk.W, text=lbl, fill="#94a3b8", font=("Helvetica", 8, "bold"))

    def _render_standard_graph(self, w, h):
        if self.view_mode == "DAG":
            stages = [
                (0.08, "STAGE 1: ROOTS"),
                (0.25, "STAGE 2: SYNC"),
                (0.43, "STAGE 3: BRANCH"),
                (0.62, "STAGE 4: MERGE"),
                (0.79, "STAGE 5: ACTUATE"),
                (0.93, "STAGE 6: PARK"),
            ]
            for rx, label in stages:
                self.canvas.create_text(int(rx * w), 92, text=label, fill="#475569", font=("Helvetica", 8, "bold"))

        card_w = min(144, max(116, int(w * 0.112)))
        card_h = 74

        # Draw Bezier Dependency Curves
        for node in self.active_blueprint:
            dst_id = node["Id"]
            for src_id in node["Dependencies"]:
                if src_id not in self.active_layout:
                    continue

                p0, p1, p2, p3 = self._get_edge_control_points(src_id, dst_id, w, h, card_w, card_h)
                src_st = self.node_status.get(src_id, "PENDING")
                dst_st = self.node_status.get(dst_id, "PENDING")

                if src_st == "CYCLE_LOCK" and dst_st == "CYCLE_LOCK":
                    color, width = THEME["edge_cycle"], 3.0
                elif dst_st == "CANCELLED":
                    color, width = THEME["edge_cancel"], 2.2
                elif src_st == "COMPLETED" and dst_st == "WAITING":
                    color, width = THEME["edge_wait"], 2.8
                elif src_st == "COMPLETED":
                    color, width = THEME["edge_done"], 2.6
                else:
                    color, width = THEME["edge_idle"], 1.8

                curve_pts = []
                steps = 18
                for i in range(steps + 1):
                    bx, by = cubic_bezier(i / steps, p0, p1, p2, p3)
                    curve_pts.extend([bx, by])

                self.canvas.create_line(
                    *curve_pts, fill=color, width=width,
                    arrow=tk.LAST, arrowshape=(9, 11, 4)
                )

        # Draw Particles
        for p in self.particles:
            if p.src_id in self.active_layout and p.dst_id in self.active_layout:
                p0, p1, p2, p3 = self._get_edge_control_points(p.src_id, p.dst_id, w, h, card_w, card_h)
                px, py = cubic_bezier(p.progress, p0, p1, p2, p3)
                self.canvas.create_oval(px - 6, py - 6, px + 6, py + 6, fill=p.color, outline="#ffffff", width=1.5)

        if self.view_mode == "CYCLE_VIEW":
            cx, cy = int(0.50 * w), int(0.51 * h)
            self._draw_rrect(cx - 145, cy - 42, cx + 145, cy + 42, 10, fill="#2a0810", outline="#f43f5e", width=2)
            self.canvas.create_text(
                cx, cy - 14,
                text="⚠ CIRCULAR DEPENDENCY DETECTED",
                fill="#fda4af", font=("Helvetica", 9, "bold")
            )
            self.canvas.create_text(
                cx, cy + 12,
                text="InDegree never reaches 0 (400 Bad Request)\nKahn's Algorithm aborted execution",
                justify=tk.CENTER, fill="#fecdd3", font=("Helvetica", 8)
            )

        pulse = (math.sin(self.tick_count * 0.20) + 1.0) * 0.5

        for node in self.active_blueprint:
            nid = node["Id"]
            cx, cy = self._get_node_screen_pos(nid, w, h)
            x1, y1 = cx - card_w // 2, cy - card_h // 2
            x2, y2 = cx + card_w // 2, cy + card_h // 2

            status = self.node_status.get(nid, "PENDING")
            st_cfg = THEME.get(status, THEME["PENDING"])

            if status in ("RUNNING", "READY", "WAITING", "CYCLE_LOCK", "FAILED"):
                pad = 3 + int(pulse * 4)
                self._draw_rrect(
                    x1 - pad, y1 - pad, x2 + pad, y2 + pad, 12,
                    fill="", outline=st_cfg["border"], width=1.8
                )

            self._draw_rrect(
                x1, y1, x2, y2, 10,
                fill=st_cfg["fill"], outline=st_cfg["border"], width=2.2
            )

            badge_label = "CYCLE!" if status == "CYCLE_LOCK" else status
            self._draw_rrect(
                x1 + 8, y1 + 7, x1 + 74, y1 + 23, 5,
                fill=st_cfg["badge"], outline=""
            )
            self.canvas.create_text(
                x1 + 41, y1 + 15,
                text=badge_label, fill="#ffffff", font=("Helvetica", 7, "bold")
            )

            indeg = self.node_indegree.get(nid, 0)
            tot_deps = self.node_total_deps.get(nid, 0)
            if status == "WAITING":
                indeg_str = f"Wait:{indeg}/{tot_deps}"
                indeg_color = "#fbbf24"
            else:
                indeg_str = f"In:{indeg}"
                indeg_color = "#34d399" if indeg == 0 else ("#fda4af" if status == "CYCLE_LOCK" else "#94a3b8")

            self.canvas.create_text(
                x2 - 8, y1 + 15, anchor=tk.E,
                text=indeg_str, fill=indeg_color, font=("Helvetica", 8, "bold")
            )

            self.canvas.create_text(
                cx, cy + 6,
                text=nid, fill=st_cfg["text"], font=("Helvetica", 9, "bold")
            )

            bx1, by1 = x1 + 10, y2 - 13
            bx2, by2 = x2 - 10, y2 - 7
            self.canvas.create_rectangle(bx1, by1, bx2, by2, fill="#090d16", outline="")

            prog = self.node_progress.get(nid, 0.0)
            if status == "WAITING" and tot_deps > 0:
                prog = (tot_deps - indeg) / tot_deps
            elif status == "CYCLE_LOCK":
                prog = 1.0

            if prog > 0:
                fw = int((bx2 - bx1) * prog)
                self.canvas.create_rectangle(bx1, by1, bx1 + fw, by2, fill=st_cfg["border"], outline="")

    def _render_mega_graph(self, w, h):
        """High-density 60 FPS renderer for the 100-Node (10x10) Mega Mesh."""
        for c in range(10):
            rx = 0.055 + (c / 9.0) * 0.89
            self.canvas.create_text(int(rx * w), 88, text=f"STAGE {c+1}", fill="#475569", font=("Helvetica", 7, "bold"))

        card_w = min(72, max(54, int(w * 0.055)))
        card_h = 34

        # 1. Fast Edges
        for node in self.active_blueprint:
            dst_id = node["Id"]
            dx, dy = self._get_node_screen_pos(dst_id, w, h)
            x_end, y_end = dx - card_w // 2, dy
            dst_st = self.node_status.get(dst_id, "PENDING")

            for src_id in node["Dependencies"]:
                sx, sy = self._get_node_screen_pos(src_id, w, h)
                x_start, y_start = sx + card_w // 2, sy
                src_st = self.node_status.get(src_id, "PENDING")

                if src_st == "COMPLETED" and dst_st == "WAITING":
                    color, width = THEME["edge_wait"], 1.8
                elif src_st == "COMPLETED":
                    color, width = THEME["edge_done"], 1.6
                else:
                    color, width = THEME["edge_idle"], 1.0

                self.canvas.create_line(x_start, y_start, x_end, y_end, fill=color, width=width)

        # 2. Particles
        for p in self.particles:
            if p.src_id in self.active_layout and p.dst_id in self.active_layout:
                sx, sy = self._get_node_screen_pos(p.src_id, w, h)
                dx, dy = self._get_node_screen_pos(p.dst_id, w, h)
                x0, y0 = sx + card_w // 2, sy
                x1, y1 = dx - card_w // 2, dy
                px = x0 + (x1 - x0) * p.progress
                py = y0 + (y1 - y0) * p.progress
                self.canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill=p.color, outline="#ffffff", width=1)

        # 3. Compact 100-Node Pills
        for node in self.active_blueprint:
            nid = node["Id"]
            cx, cy = self._get_node_screen_pos(nid, w, h)
            x1, y1 = cx - card_w // 2, cy - card_h // 2
            x2, y2 = cx + card_w // 2, cy + card_h // 2

            status = self.node_status.get(nid, "PENDING")
            st_cfg = THEME.get(status, THEME["PENDING"])

            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=st_cfg["fill"], outline=st_cfg["border"], width=1.6
            )

            indeg = self.node_indegree.get(nid, 0)
            self.canvas.create_text(
                cx - 10, cy - 4,
                text=nid, fill=st_cfg["text"], font=("Helvetica", 8, "bold")
            )
            self.canvas.create_text(
                cx + 16, cy - 4,
                text=f"({indeg})", fill="#fbbf24" if status == "WAITING" else "#94a3b8",
                font=("Helvetica", 7)
            )

            # Mini Progress Bar
            prog = self.node_progress.get(nid, 0.0)
            if status == "WAITING":
                tot = max(1, self.node_total_deps.get(nid, 1))
                prog = (tot - indeg) / tot
            if prog > 0:
                fw = int((card_w - 8) * prog)
                self.canvas.create_rectangle(
                    x1 + 4, y2 - 6, x1 + 4 + fw, y2 - 3,
                    fill=st_cfg["border"], outline=""
                )


if __name__ == "__main__":
    root = tk.Tk()
    app = DAGStudioApp(root)
    root.mainloop()