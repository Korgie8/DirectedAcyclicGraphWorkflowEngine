using Xunit;
using FluentAssertions;
using System.Collections.Generic;
using ConsistencyEngine.Core;

namespace ConsistencyEngine.Tests
{
    public class TaskOrchestratorTests
    {
        [Fact]
        public void Orchestrator_GetReadyTasks_WhenStarted_ShouldReturnZeroDependencyTasks()
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

            TaskOrchestrator orchestrator = new TaskOrchestrator(graph, expectedId);
            List<TaskNode> readyTasks = orchestrator.GetReadyTasks();

            readyTasks.Should().HaveCount(2);
            readyTasks.Should().Contain(nodeA);
            readyTasks.Should().Contain(nodeB);
            readyTasks.Should().NotContain(nodeC);

            nodeA.Status.Should().Be(NodeStatus.Ready);
            nodeB.Status.Should().Be(NodeStatus.Ready);
            nodeC.Status.Should().Be(NodeStatus.Pending);

            orchestrator.MarkTaskAsCompleted(nodeA.Id);
            readyTasks = orchestrator.GetReadyTasks();

            readyTasks.Should().HaveCount(1);
            readyTasks.Should().NotContain(nodeA);
            readyTasks.Should().Contain(nodeB);
            readyTasks.Should().NotContain(nodeC);

            nodeA.Status.Should().Be(NodeStatus.Completed);
            nodeB.Status.Should().Be(NodeStatus.Ready);
            nodeC.Status.Should().Be(NodeStatus.Pending);

            orchestrator.MarkTaskAsCompleted(nodeB.Id);
            readyTasks = orchestrator.GetReadyTasks();

            readyTasks.Should().HaveCount(1);
            readyTasks.Should().NotContain(nodeA);
            readyTasks.Should().NotContain(nodeB);
            readyTasks.Should().Contain(nodeC);

            nodeA.Status.Should().Be(NodeStatus.Completed);
            nodeB.Status.Should().Be(NodeStatus.Completed);
            nodeC.Status.Should().Be(NodeStatus.Ready);
        }

        [Fact]
        public void Orchestrator_NodeFailed_ShouldCascadeCancelDownstreamTasks()
        {
            string expectedId = "Test";

            ConsistencyGraph graph = new ConsistencyGraph();
            TaskNode nodeA = new TaskNode("Motor1");
            TaskNode nodeB = new TaskNode("Motor2");
            TaskNode nodeC = new TaskNode("ExtendClaw");
            TaskNode nodeD = new TaskNode("CloseClaw");
            TaskNode nodeE = new TaskNode("RetractClaw");

            nodeC.AddDependency("Motor1");
            nodeC.AddDependency("Motor2");
            nodeD.AddDependency("ExtendClaw");
            nodeD.AddDependency("Motor1");
            nodeE.AddDependency("CloseClaw");
            nodeE.AddDependency("Motor2");

            graph.AddNode(nodeA);
            graph.AddNode(nodeB);
            graph.AddNode(nodeC);
            graph.AddNode(nodeD);
            graph.AddNode(nodeE);

            TaskOrchestrator orchestrator = new TaskOrchestrator(graph, expectedId);

            orchestrator.MarkTaskAsCompleted(nodeA.Id);
            orchestrator.MarkTaskAsCompleted(nodeB.Id);

            nodeC.Status.Should().Be(NodeStatus.Ready);

            orchestrator.MarkTaskAsFailed(nodeC.Id);

            nodeC.Status.Should().Be(NodeStatus.Failed);

            nodeD.Status.Should().Be(NodeStatus.Cancelled);
            nodeE.Status.Should().Be(NodeStatus.Cancelled);

            nodeA.Status.Should().Be(NodeStatus.Completed);
            nodeB.Status.Should().Be(NodeStatus.Completed);

            List<TaskNode> readyTasks = orchestrator.GetReadyTasks();
            readyTasks.Should().BeEmpty("because the only remaining tasks were dependent on a failed hardware component");
        }
    }
}