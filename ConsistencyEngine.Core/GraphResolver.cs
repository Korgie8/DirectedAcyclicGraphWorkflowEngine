using System.Collections.Generic;

namespace ConsistencyEngine.Core
{
    public class GraphResolver
    {
        public List<TaskNode> Resolve(ConsistencyGraph graph)
        {
            Dictionary<string, List<string>> AdjacencyList = new Dictionary<string, List<string>>();
            Dictionary<string, int> InDegree = new Dictionary<string, int>();
            Queue<string> ZeroInDegreeQueue = new Queue<string>();

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
                    ZeroInDegreeQueue.Enqueue(kvp.Key);
                }
            }

            List<TaskNode> sortedNodes = new List<TaskNode>();

            while (ZeroInDegreeQueue.Count > 0)
            {
                string currentId = ZeroInDegreeQueue.Dequeue();
                sortedNodes.Add(graph.GetNode(currentId));

                foreach (var neighborId in AdjacencyList[currentId])
                {
                    InDegree[neighborId]--;

                    if (InDegree[neighborId] == 0)
                    {
                        ZeroInDegreeQueue.Enqueue(neighborId);
                    }
                }
            }

            foreach (var kvp in InDegree)
            {
                if (kvp.Value > 0)
                {
                    throw new CircularDependencyException("Graph contains a circular dependency.");
                }
            }

            return sortedNodes;
        }
    }
}