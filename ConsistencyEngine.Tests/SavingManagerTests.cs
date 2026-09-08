using Xunit;
using FluentAssertions;
using ConsistencyEngine.Core;

namespace ConsistencyEngine.Tests
{
    public class SavingManagerTests
    {
        [Fact]
        public void SavingManager_Save_Load()
        {
            string expectedId = "Test";

            ConsistencyGraph graph = new ConsistencyGraph();
            TaskNode nodeA = new TaskNode("Motor1");
            TaskNode nodeB = new TaskNode("Motor2");
            TaskNode nodeC = new TaskNode("CloseClaw");

            nodeC.AddDependency("Motor1");
            nodeC.AddDependency("Motor2");

            graph.AddNode(nodeA);
            graph.AddNode(nodeB);
            graph.AddNode(nodeC);

            SavingManager savingManager = new SavingManager("test_data");

            savingManager.SaveGraph(expectedId, graph);

            ConsistencyGraph recoveredGraph = savingManager.LoadGraph(expectedId);

            recoveredGraph.Should().BeEquivalentTo(graph);
        }
    }
}