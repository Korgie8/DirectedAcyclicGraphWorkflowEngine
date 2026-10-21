using System;

namespace DirectedAcyclicGraphWorkflowEngine.Core
{
    public class CircularDependencyException : Exception
    {
        public CircularDependencyException(string message) : base(message)
        {
        }
    }
}