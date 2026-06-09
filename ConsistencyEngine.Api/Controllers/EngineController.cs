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
        private readonly TaskOrchestrator _orchestrator;

        public EngineController(TaskOrchestrator orchestrator)
        {
            _orchestrator = orchestrator;
        }

        [HttpPost("start")]
        public IActionResult StartMission([FromBody] List<BlueprintNode> payload)
        {
            ConsistencyGraph newGraph = new ConsistencyGraph();
            foreach (var node in payload)
            {
                TaskNode taskNode = new TaskNode(node.Id)
                {
                    Dependencies = node.Dependencies
                };
                newGraph.AddNode(taskNode);
            }

            GraphResolver resolver = new GraphResolver();
            try
            {
                resolver.Resolve(newGraph);
            }
            catch (CircularDependencyException ex)
            {
                return BadRequest(ex.Message);
            }

            _orchestrator.LoadNewMission(newGraph);

            var readyTasks = _orchestrator.GetReadyTasks();
            return Ok(readyTasks);
        }
    }
}