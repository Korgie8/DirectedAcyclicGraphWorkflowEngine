# Directed Acyclic Graph Workflow Engine
A lightweight Directed Acyclic Graph (DAG) Workflow Engine built in C# and .NET.

## The Goal

To safely orchestrate complex sequences of tasks by guaranteeing absolute execution order. The engine ensures that no step in a process runs until all of its prerequisites are successfully completed, while automatically halting downstream actions if a critical upstream failure occurs.

## How It Works

Instead of relying on hardcoded scripts, this engine reads dynamic graph blueprints and manages the state machine for the entire workflow.

    Dependency Resolution: Maps out the exact topological execution order of a node-based blueprint.

    Loop Prevention: Automatically detects and rejects circular dependencies before execution begins.

    Real-Time Orchestration: Acts as the central brain, actively pushing "Ready" tasks via WebSockets to connected worker clients—whether those workers are background software threads or physical hardware controllers.

## TODO
- Fully flashed API calls.