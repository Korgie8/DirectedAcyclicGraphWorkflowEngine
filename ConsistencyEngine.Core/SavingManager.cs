using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using ConsistencyEngine.Core;

namespace ConsistencyEngine.Core
{
    public class SavingManager
    {
        private readonly string _folderPath = "MissionData";
        
        public SavingManager(string path = null)
        {
            if (!string.IsNullOrEmpty(path))
            {
                _folderPath = path;
            }

            EnsureFolderExists();
        }
        private void EnsureFolderExists()
        {
            if (!Directory.Exists(_folderPath))
            {
                Directory.CreateDirectory(_folderPath);
            }
        }

        public void SaveGraph(string id, ConsistencyGraph graph)
        {
            string filePath = Path.Combine(_folderPath, $"{id}.json");
            string json = JsonSerializer.Serialize(graph);
            File.WriteAllText(filePath, json);
        }

        public ConsistencyGraph LoadGraph(string id)
        {
            string filePath = Path.Combine(_folderPath, $"{id}.json");
            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException($"Graph with ID '{id}' not found.");
            }

            string json = File.ReadAllText(filePath);
            return JsonSerializer.Deserialize<ConsistencyGraph>(json);
        }
    }
}