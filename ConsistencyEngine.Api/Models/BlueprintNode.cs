using System.ComponentModel.DataAnnotations;
using System.Collections.Generic;

namespace ConsistencyEngine.Api.Models
{
    public class BlueprintNode
    {
        // [Required] means if the JSON is missing "Id", 
        // the server automatically rejects it with a 400 Bad Request.
        [Required(ErrorMessage = "Every node must have an Id.")]
        public string Id { get; set; }

        // If they don't provide dependencies, it defaults to an empty list
        public List<string> Dependencies { get; set; } = new List<string>();
    }
}