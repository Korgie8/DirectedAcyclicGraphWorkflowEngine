using System.Collections.Generic;

namespace ConsistencyEngine.Core
{
    public enum NodeStatus
    {
        Pending,
        Ready,
        Running,
        Completed,
        Failed,
        Cancelled
    }

    public class TaskNode
    {
        public string Id { get; set; }
        public List<string> Dependencies { get; set; }
        public NodeStatus Status { get; set; }

        public TaskNode()
        {
            Dependencies = new List<string>();
            Status = NodeStatus.Pending;
        }

        public TaskNode(string id)
        {
            Id = id;
            Status = NodeStatus.Pending;
            Dependencies = new List<string>();
        }

        public void AddDependency(string dependencyId)
        {
            if (!Dependencies.Contains(dependencyId))
            {
                Dependencies.Add(dependencyId);
            }
        }
    }
}