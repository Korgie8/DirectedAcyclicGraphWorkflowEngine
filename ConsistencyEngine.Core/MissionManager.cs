using System.Collections.Generic;

namespace ConsistencyEngine.Core
{
    public class MissionManager
    {
        public Dictionary<string, TaskOrchestrator> TaskOrchestrators { get; set; } = new Dictionary<string, TaskOrchestrator>();

        public void StartNewMission(string id, ConsistencyGraph graph)
        {
            var orchestrator = new TaskOrchestrator(graph);
            TaskOrchestrators[id] = orchestrator;
        }

        public TaskOrchestrator GetMissionOrchestrator(string id)
        {
            return TaskOrchestrators.TryGetValue(id, out TaskOrchestrator orchestrator) ? orchestrator : null;
        }
    }
}