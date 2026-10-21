using Xunit;
using FluentAssertions;
using DirectedAcyclicGraphWorkflowEngine.Core;

namespace DirectedAcyclicGraphWorkflowEngine.Tests
{
    public class TaskNodeTests
    {
        [Fact]
        public void TaskNode_WhenCreated_ShouldDefaultToPendingStatus()
        {
            string expectedId = "BirthOfTheDragon";

            TaskNode node = new TaskNode(expectedId);

            node.Id.Should().Be(expectedId);
            node.Status.Should().Be(NodeStatus.Pending);
            node.Dependencies.Should().NotBeNull();
            node.Dependencies.Should().BeEmpty();
        }

        [Fact]
        public void TaskNode_AddDependency_ShouldStoreDependencyId()
        {
            string expectedId = "BirthOfTheDragon";

            TaskNode node = new TaskNode(expectedId);
            string requiredEventId = "TheBreakingOfTheWorld";

            node.AddDependency(requiredEventId);

            node.Dependencies.Should().Contain(requiredEventId);
            node.Dependencies.Should().HaveCount(1);
        }
    }
}