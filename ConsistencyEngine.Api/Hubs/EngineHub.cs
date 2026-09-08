using Microsoft.AspNetCore.SignalR;
using ConsistencyEngine.Core;
using System.Threading.Tasks;

namespace ConsistencyEngine.Api.Hubs
{
    public class EngineHub : Hub
    {
        private readonly MissionManager _manager;

        public EngineHub(MissionManager manager)
        {
            _manager = manager;
        }

        public async Task ReportTaskDone(string missionId, string taskId)
        {
            var orchestrator = _manager.GetMissionOrchestrator(missionId);
            if (orchestrator == null) return;
            
            orchestrator.MarkTaskAsCompleted(taskId);
            await Clients.Caller.SendAsync("ExecuteNext", orchestrator.GetReadyTasks());
        }

        public async Task ReportTaskFailed(string missionId, string taskId)
        {
            var orchestrator = _manager.GetMissionOrchestrator(missionId);
            if (orchestrator == null) return;

            orchestrator.MarkTaskAsFailed(taskId);
            await Clients.Caller.SendAsync("ExecuteNext", orchestrator.GetReadyTasks());
        }
    }
}