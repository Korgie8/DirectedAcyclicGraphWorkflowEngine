using Xunit;
using FluentAssertions;
using ConsistencyEngine.Core;

namespace ConsistencyEngine.Tests
{
    public class GraphResolverTests
    {
        [Fact]
        public void GraphResolver_Validation_CircularLoop()
        {
            ConsistencyGraph graph = new ConsistencyGraph();
            string nodeAId = "NodeA";
            string nodeBId = "NodeB";
            string nodeCId = "NodeC";
            TaskNode nodeA = new TaskNode(nodeAId);
            TaskNode nodeB = new TaskNode(nodeBId);
            TaskNode nodeC = new TaskNode(nodeCId);

            nodeA.AddDependency(nodeBId);
            nodeB.AddDependency(nodeCId);
            nodeC.AddDependency(nodeAId);

            graph.AddNode(nodeA);
            graph.AddNode(nodeB);
            graph.AddNode(nodeC);

            GraphResolver resolver = new GraphResolver();

            Action act = () => resolver.Resolve(graph);

            act.Should().Throw<CircularDependencyException>();
        }

        [Fact]
        public void GraphResolver_VShape_ShouldOrderDependenciesCorrectly()
        {
            ConsistencyGraph graph = new ConsistencyGraph();
            string nodeAId = "NodeA";
            string nodeBId = "NodeB";
            string nodeCId = "NodeC";
            TaskNode nodeA = new TaskNode(nodeAId);
            TaskNode nodeB = new TaskNode(nodeBId);
            TaskNode nodeC = new TaskNode(nodeCId);

            nodeC.AddDependency(nodeAId);
            nodeC.AddDependency(nodeBId);

            graph.AddNode(nodeC);
            graph.AddNode(nodeA);
            graph.AddNode(nodeB);

            GraphResolver resolver = new GraphResolver();

            List<TaskNode> executionOrder = resolver.Resolve(graph);

            executionOrder.Should().HaveCount(3);
            int indexOfA = executionOrder.IndexOf(nodeA);
            int indexOfB = executionOrder.IndexOf(nodeB);
            int indexOfC = executionOrder.IndexOf(nodeC);

            indexOfC.Should().BeGreaterThan(indexOfA, "because the claw cannot close before Motor 1 is done");
            indexOfC.Should().BeGreaterThan(indexOfB, "because the claw cannot close before Motor 2 is done");
        }

        [Fact]
        public void GraphResolver_LinearChain_ShouldOrderDependenciesCorrectly()
        {
            ConsistencyGraph graph = new ConsistencyGraph();
            string nodeAId = "NodeA";
            string nodeBId = "NodeB";
            string nodeCId = "NodeC";
            TaskNode nodeA = new TaskNode(nodeAId);
            TaskNode nodeB = new TaskNode(nodeBId);
            TaskNode nodeC = new TaskNode(nodeCId);

            nodeB.AddDependency(nodeAId);
            nodeC.AddDependency(nodeBId);

            graph.AddNode(nodeC);
            graph.AddNode(nodeA);
            graph.AddNode(nodeB);

            GraphResolver resolver = new GraphResolver();

            List<TaskNode> executionOrder = resolver.Resolve(graph);

            executionOrder.Should().HaveCount(3);
            int indexOfA = executionOrder.IndexOf(nodeA);
            int indexOfB = executionOrder.IndexOf(nodeB);
            int indexOfC = executionOrder.IndexOf(nodeC);

            indexOfB.Should().BeGreaterThan(indexOfA, "because the claw cannot close before Motor 2 is done");
            indexOfC.Should().BeGreaterThan(indexOfA, "because the claw cannot close before Motor 1 is done");
            indexOfC.Should().BeGreaterThan(indexOfB, "because the claw cannot close before Motor 2 is done");
        }
    }
}