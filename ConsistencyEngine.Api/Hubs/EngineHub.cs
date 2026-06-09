using Microsoft.AspNetCore.SignalR;
using ConsistencyEngine.Core;
using System.Threading.Tasks;

namespace ConsistencyEngine.Api.Hubs
{
    public class EngineHub : Hub
    {
        private readonly TaskOrchestrator _orchestrator;

        public EngineHub(TaskOrchestrator orchestrator)
        {
            _orchestrator = orchestrator;
        }

        public async Task ReportTaskDone(string taskId)
        {
            _orchestrator.MarkTaskAsCompleted(taskId);

            var nextTasks = _orchestrator.GetReadyTasks();

            await Clients.Caller.SendAsync("ExecuteNext", nextTasks);
        }

        public async Task ReportTaskFailed(string taskId)
        {
            _orchestrator.MarkTaskAsFailed(taskId);

            var nextTasks = _orchestrator.GetReadyTasks();

            await Clients.Caller.SendAsync("ExecuteNext", nextTasks);
        }

    }
}