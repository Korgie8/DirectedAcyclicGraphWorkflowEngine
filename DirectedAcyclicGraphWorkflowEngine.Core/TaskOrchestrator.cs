using System;
using System.Collections.Generic;

namespace DirectedAcyclicGraphWorkflowEngine.Core
{
    public class TaskOrchestrator
    {
        public string Id { get; private set; }
        public ConsistencyGraph graph { get; private set; }
        public Dictionary<string, List<string>> AdjacencyList = new Dictionary<string, List<string>>();
        public Dictionary<string, int> InDegree = new Dictionary<string, int>();
        public List<string> ReadyNodes = new List<string>();

        private readonly object _stateLock = new object();
        SavingManager savingManager = new SavingManager();

        public TaskOrchestrator(ConsistencyGraph consistencyGraph, string id)
        {
            Id = id;
            graph = consistencyGraph;

            InitializeGraph();

            savingManager.SaveGraph(Id, graph);
        }

        private void InitializeGraph()
        {
            foreach (var node in graph.GetAllNodes())
            {
                if (!AdjacencyList.ContainsKey(node.Id))
                    AdjacencyList[node.Id] = new List<string>();

                if (!InDegree.ContainsKey(node.Id))
                    InDegree[node.Id] = 0;

                foreach (var depId in node.Dependencies)
                {
                    if (!AdjacencyList.ContainsKey(depId))
                        AdjacencyList[depId] = new List<string>();

                    AdjacencyList[depId].Add(node.Id);

                    TaskNode? dependencyNode = graph.GetNode(depId);
                    if (dependencyNode != null && dependencyNode.Status != NodeStatus.Completed)
                    {
                        if (!InDegree.ContainsKey(node.Id))
                            InDegree[node.Id] = 0;

                        InDegree[node.Id]++;
                    }
                }
            }

            foreach (var kvp in InDegree)
            {
                TaskNode? task = graph.GetNode(kvp.Key);

                if (task != null && kvp.Value == 0 && task.Status != NodeStatus.Completed)
                {
                    ReadyNodes.Add(kvp.Key);
                    task.Status = NodeStatus.Ready;
                }
            }
        }

        public void MarkTaskAsCompleted(string taskId)
        {
            lock (_stateLock)
            {
                TaskNode? task = graph.GetNode(taskId);

                if (task != null && task.Status == NodeStatus.Completed) 
                    return;

                if (task == null || task.Status != NodeStatus.Ready)
                {
                    throw new InvalidOperationException($"Task {taskId} is not ready to be marked as completed.");
                }
                
                task.Status = NodeStatus.Completed;
                ReadyNodes.Remove(taskId);

                foreach (var neighborId in AdjacencyList[taskId])
                {
                    InDegree[neighborId]--;

                    if (InDegree[neighborId] == 0)
                    {
                        ReadyNodes.Add(neighborId);
                        TaskNode? neighborTask = graph.GetNode(neighborId);
                        if (neighborTask != null)
                        {
                            neighborTask.Status = NodeStatus.Ready;
                        }
                    }
                }

                savingManager.SaveGraph(Id, graph);
            }
        }

        public void MarkTaskAsFailed(string failedTaskId)
        {
            lock (_stateLock)
            {
                TaskNode? originTask = graph.GetNode(failedTaskId);

                if (originTask != null && originTask.Status == NodeStatus.Failed) 
                    return;

                if (originTask != null)
                {
                    originTask.Status = NodeStatus.Failed;
                }
                
                ReadyNodes.Remove(failedTaskId);

                Queue<string> cancelQueue = new Queue<string>();

                if (AdjacencyList.TryGetValue(failedTaskId, out var adjacentList))
                {
                    foreach (var neighborId in adjacentList)
                    {
                        cancelQueue.Enqueue(neighborId);
                    }
                }

                while (cancelQueue.Count > 0)
                {
                    string currentId = cancelQueue.Dequeue();
                    TaskNode? nodeToCancel = graph.GetNode(currentId);

                    if (nodeToCancel != null && nodeToCancel.Status != NodeStatus.Cancelled)
                    {
                        nodeToCancel.Status = NodeStatus.Cancelled;
                        ReadyNodes.Remove(currentId);

                        if (AdjacencyList.TryGetValue(currentId, out var childList))
                        {
                            foreach (var childId in childList)
                            {
                                cancelQueue.Enqueue(childId);
                            }
                        }
                    }
                }

                savingManager.SaveGraph(Id, graph);
            }
        }

        public List<TaskNode> GetReadyTasks()
        {
            lock (_stateLock)
            {
                var tasks = new List<TaskNode>();
                foreach (var id in ReadyNodes)
                {
                    var node = graph.GetNode(id);
                    if (node != null)
                    {
                        tasks.Add(node);
                    }
                }
                return tasks;
            }
        }

        public TaskNode? GetReadyTask()
        {
            lock (_stateLock)
            {
                if (ReadyNodes.Count == 0) return null;
                return graph.GetNode(ReadyNodes[0]);
            }
        }
    }
}