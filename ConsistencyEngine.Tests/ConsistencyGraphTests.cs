using Xunit;
using FluentAssertions;
using ConsistencyEngine.Core;

namespace ConsistencyEngine.Tests
{
    public class ConsistencyGraphTests
    {
        [Fact]
        public void ConsistencyGraph_AddNode_ShouldStoreAndRetrieveNode()
        {
            ConsistencyGraph graph = new ConsistencyGraph();
            string expectedId = "BirthOfTheDragon";
            TaskNode node = new TaskNode(expectedId);
            string requiredEventId = "TheBreakingOfTheWorld";

            node.AddDependency(requiredEventId);

            graph.AddNode(node);

            TaskNode retrievedNode = graph.GetNode(expectedId);
            retrievedNode.Should().NotBeNull();
            retrievedNode.Id.Should().Be(expectedId);
            retrievedNode.Dependencies.Should().Contain(requiredEventId);
            retrievedNode.Dependencies.Should().HaveCount(1);
        }
    }
}