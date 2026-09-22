using System.Collections.Generic;

namespace ConsistencyEngine.Core
{
    public class ConsistencyGraph
    {
        public Dictionary<string, TaskNode> Nodes { get; set; } = new Dictionary<string, TaskNode>();

        public ConsistencyGraph()
        {
            Nodes = new Dictionary<string, TaskNode>();
        }

        public void AddNode(TaskNode node)
        {
            if (!Nodes.ContainsKey(node.Id))
            {
                Nodes[node.Id] = node;
            }
        }

        public TaskNode? GetNode(string id)
        {
            Nodes.TryGetValue(id, out TaskNode? node);
            return node;
        }

        public List<TaskNode> GetAllNodes()
        {
            return new List<TaskNode>(Nodes.Values);
        }
    }
}