using Xunit;
using FluentAssertions;
using ConsistencyEngine.Core;

namespace ConsistencyEngine.Tests
{
    public class MissionManagerTests
    {
        [Fact]
        public void MissionManagerTests_FunctionalityOfOneMission_ShouldReturnZeroDependencyTasks()
        {
            ConsistencyGraph graph = new ConsistencyGraph();
            TaskNode nodeA = new TaskNode("Motor1");
            TaskNode nodeB = new TaskNode("Motor2");
            TaskNode nodeC = new TaskNode("CloseClaw");

            nodeC.AddDependency("Motor1");
            nodeC.AddDependency("Motor2");

            graph.AddNode(nodeA);
            graph.AddNode(nodeB);
            graph.AddNode(nodeC);

            MissionManager missionManager = new MissionManager();
            missionManager.StartNewMission("Test", graph);
            TaskOrchestrator orchestrator = missionManager.GetMissionOrchestrator("Test");
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
        public void MissionManager_ConcurrentMissions_ShouldNotInterfere()
        {
            ConsistencyGraph graphA = new ConsistencyGraph();
            TaskNode motor1 = new TaskNode("Motor1");
            TaskNode motor2 = new TaskNode("Motor2");
            motor2.AddDependency("Motor1");
            graphA.AddNode(motor1);
            graphA.AddNode(motor2);

            ConsistencyGraph graphB = new ConsistencyGraph();
            TaskNode laser1 = new TaskNode("Laser1");
            TaskNode laser2 = new TaskNode("Laser2");
            laser2.AddDependency("Laser1");
            graphB.AddNode(laser1);
            graphB.AddNode(laser2);

            MissionManager manager = new MissionManager();
            manager.StartNewMission("Mission-Drive", graphA);
            manager.StartNewMission("Mission-Laser", graphB);

            TaskOrchestrator orchestratorA = manager.GetMissionOrchestrator("Mission-Drive");
            TaskOrchestrator orchestratorB = manager.GetMissionOrchestrator("Mission-Laser");

            orchestratorA.GetReadyTasks().Should().ContainSingle(n => n.Id == "Motor1");
            orchestratorB.GetReadyTasks().Should().ContainSingle(n => n.Id == "Laser1");

            orchestratorA.MarkTaskAsCompleted("Motor1");

            orchestratorA.GetReadyTasks().Should().ContainSingle(n => n.Id == "Motor2");

            orchestratorB.GetReadyTasks().Should().ContainSingle(n => n.Id == "Laser1",
                "because Mission B runs on a completely separate memory state than Mission A");
        }
    }
}