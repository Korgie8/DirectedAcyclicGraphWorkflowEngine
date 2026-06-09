using System.Collections.Generic;

namespace ConsistencyEngine.Core
{
    public class TaskOrchestrator
    {
        public ConsistencyGraph graph { get; private set; }
        public Dictionary<string, List<string>> AdjacencyList = new Dictionary<string, List<string>>();
        public Dictionary<string, int> InDegree = new Dictionary<string, int>();
        public List<string> ReadyNodes = new List<string>();

        public TaskOrchestrator(ConsistencyGraph consistencyGraph)
        {
            graph = consistencyGraph;

            InitializeGraph();
        }

        public void LoadNewMission(ConsistencyGraph newGraph)
        {
            graph = newGraph;
            AdjacencyList.Clear();
            InDegree.Clear();
            ReadyNodes.Clear();

            InitializeGraph();
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

                    if (!InDegree.ContainsKey(node.Id))
                        InDegree[node.Id] = 0;

                    InDegree[node.Id]++;
                }
            }

            foreach (var kvp in InDegree)
            {
                if (kvp.Value == 0)
                {
                    ReadyNodes.Add(kvp.Key);
                    TaskNode task = graph.GetNode(kvp.Key);
                    task.Status = NodeStatus.Ready;
                }
            }
        }

        public void MarkTaskAsCompleted(string taskId)
        {
            TaskNode task = graph.GetNode(taskId);

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
                    TaskNode neighborTask = graph.GetNode(neighborId);
                    neighborTask.Status = NodeStatus.Ready;
                }
            }
        }

        public void MarkTaskAsFailed(string failedTaskId)
        {
            TaskNode originTask = graph.GetNode(failedTaskId);
            originTask.Status = NodeStatus.Failed;
            ReadyNodes.Remove(failedTaskId);

            Queue<string> cancelQueue = new Queue<string>();

            foreach (var neighborId in AdjacencyList[failedTaskId])
            {
                cancelQueue.Enqueue(neighborId);
            }

            while (cancelQueue.Count > 0)
            {
                string currentId = cancelQueue.Dequeue();
                TaskNode nodeToCancel = graph.GetNode(currentId);

                if (nodeToCancel.Status != NodeStatus.Cancelled)
                {
                    nodeToCancel.Status = NodeStatus.Cancelled;
                    ReadyNodes.Remove(currentId);

                    foreach (var childId in AdjacencyList[currentId])
                    {
                        cancelQueue.Enqueue(childId);
                    }
                }
            }
        }

        public List<TaskNode> GetReadyTasks()
        {
            return ReadyNodes.ConvertAll(id => graph.GetNode(id));
        }

        public TaskNode GetReadyTask()
        {
            return graph.GetNode(ReadyNodes[0]);
        }
    }
}