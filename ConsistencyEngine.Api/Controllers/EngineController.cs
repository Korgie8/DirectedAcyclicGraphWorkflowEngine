using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic;
using ConsistencyEngine.Core;
using ConsistencyEngine.Api.Models;

namespace ConsistencyEngine.Api.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class EngineController : ControllerBase
    {
        private readonly MissionManager _manager;

        public EngineController(MissionManager manager)
        {
            _manager = manager;
        }

        [HttpPost("start/{missionId}")]
        public IActionResult StartMission(string missionId, [FromBody] List<BlueprintNode> payload)
        {
            ConsistencyGraph newGraph = new ConsistencyGraph();
            foreach (var node in payload)
            {
                newGraph.AddNode(new TaskNode(node.Id) { Dependencies = node.Dependencies });
            }

            GraphResolver resolver = new GraphResolver();
            try { resolver.Resolve(newGraph); }
            catch (CircularDependencyException ex) { return BadRequest(ex.Message); }

            _manager.StartNewMission(missionId, newGraph);

            var orchestrator = _manager.GetMissionOrchestrator(missionId);
            return Ok(orchestrator.GetReadyTasks());
        }

        [HttpPost("load/{missionId}")]
        public IActionResult LoadMission(string missionId)
        {
            _manager.LoadMission(missionId);

            var orchestrator = _manager.GetMissionOrchestrator(missionId);
            return Ok(orchestrator.GetReadyTasks());
        }
    }
}