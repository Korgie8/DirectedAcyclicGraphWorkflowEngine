using System.Collections.Generic;
using System.Collections.Concurrent;

namespace DirectedAcyclicGraphWorkflowEngine.Core
{
    public class MissionManager
    {
        public ConcurrentDictionary<string, TaskOrchestrator> TaskOrchestrators { get; set; } = new ConcurrentDictionary<string, TaskOrchestrator>();

        public void StartNewMission(string id, ConsistencyGraph graph)
        {
            var orchestrator = new TaskOrchestrator(graph, id);
            TaskOrchestrators.TryAdd(id, orchestrator);
        }

        public void LoadMission(string id)
        {
            SavingManager savingManager = new SavingManager();
            ConsistencyGraph graph = savingManager.LoadGraph(id);
            var orchestrator = new TaskOrchestrator(graph, id);
            TaskOrchestrators.TryAdd(id, orchestrator);
        }

        public TaskOrchestrator? GetMissionOrchestrator(string id)
        {
            return TaskOrchestrators.TryGetValue(id, out TaskOrchestrator? orchestrator) ? orchestrator : null;
        }
    }
}