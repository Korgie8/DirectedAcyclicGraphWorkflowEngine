using System;

namespace ConsistencyEngine.Core
{
    public class CircularDependencyException : Exception
    {
        public CircularDependencyException(string message) : base(message)
        {
        }
    }
}