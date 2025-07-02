import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, Server, Cpu, AlertCircle, CheckCircle } from 'lucide-react';

interface Node {
  id: string;
  status: 'online' | 'offline';
  last_heartbeat: string;
  tasks_completed?: number;
  tasks_failed?: number;
  current_load?: number;
  active_tasks?: number;
  health_score?: number;
  host?: string;
  port?: number;
}

interface Task {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  node_id?: string;
  created_at: string;
  model?: string;
  result?: {
    output?: string;
    processing_time?: number;
    tokens_generated?: number;
    error?: string;
  };
}

interface SystemStats {
  nodes: {
    total: number;
    online: number;
    offline: number;
  };
  tasks: {
    pending: number;
    running: number;
    completed: number;
    failed: number;
    total: number;
  };
}

interface NodeHealth {
  node_id: string;
  status: string;
  health_score: number;
  current_load: number;
  active_tasks: number;
  tasks_completed: number;
  tasks_failed: number;
  seconds_since_heartbeat: number;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [nodesResponse, tasksResponse] = await Promise.all([
        axios.get(`${API_BASE_URL}/nodes/status`),
        axios.get(`${API_BASE_URL}/tasks/status`)
      ]);
      
      setNodes(nodesResponse.data);
      setTasks(tasksResponse.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
      case 'completed':
        return 'text-green-500';
      case 'running':
        return 'text-blue-500';
      case 'pending':
        return 'text-yellow-500';
      case 'offline':
      case 'failed':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
      case 'completed':
        return <CheckCircle className="w-4 h-4" />;
      case 'running':
        return <Activity className="w-4 h-4" />;
      case 'offline':
      case 'failed':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return <Server className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <Activity className="w-6 h-6 animate-spin" />
          <span>Loading ExoStack Dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <Cpu className="w-8 h-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">ExoStack Dashboard</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">
                Last updated: {new Date().toLocaleTimeString()}
              </span>
              <button
                onClick={fetchData}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex items-center">
              <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
              <span className="text-red-800">Error: {error}</span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Nodes Section */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                <Server className="w-5 h-5 mr-2" />
                Nodes ({nodes.length})
              </h2>
            </div>
            <div className="p-6">
              {nodes.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No nodes registered</p>
              ) : (
                <div className="space-y-4">
                  {nodes.map((node) => (
                    <div key={node.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <span className={getStatusColor(node.status)}>
                            {getStatusIcon(node.status)}
                          </span>
                          <div>
                            <h3 className="font-medium text-gray-900">{node.id}</h3>
                            <p className="text-sm text-gray-500">
                              Last heartbeat: {new Date(node.last_heartbeat).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            node.status === 'online' 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {node.status}
                          </span>
                          {node.tasks_completed !== undefined && (
                            <p className="text-sm text-gray-500 mt-1">
                              Tasks: {node.tasks_completed}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Tasks Section */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                <Activity className="w-5 h-5 mr-2" />
                Recent Tasks ({tasks.length})
              </h2>
            </div>
            <div className="p-6">
              {tasks.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No tasks found</p>
              ) : (
                <div className="space-y-4">
                  {tasks.slice(0, 10).map((task) => (
                    <div key={task.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <span className={getStatusColor(task.status)}>
                            {getStatusIcon(task.status)}
                          </span>
                          <div>
                            <h3 className="font-medium text-gray-900">{task.id}</h3>
                            <p className="text-sm text-gray-500">
                              Created: {new Date(task.created_at).toLocaleString()}
                            </p>
                            {task.node_id && (
                              <p className="text-sm text-gray-500">Node: {task.node_id}</p>
                            )}
                            {task.model && (
                              <p className="text-sm text-gray-500">Model: {task.model}</p>
                            )}
                          </div>
                        </div>
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          task.status === 'completed' ? 'bg-green-100 text-green-800' :
                          task.status === 'running' ? 'bg-blue-100 text-blue-800' :
                          task.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {task.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Server className="w-8 h-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Total Nodes</p>
                <p className="text-2xl font-semibold text-gray-900">{nodes.length}</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <CheckCircle className="w-8 h-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Online Nodes</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {nodes.filter(n => n.status === 'online').length}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Activity className="w-8 h-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Running Tasks</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {tasks.filter(t => t.status === 'running').length}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <CheckCircle className="w-8 h-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Completed Tasks</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {tasks.filter(t => t.status === 'completed').length}
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
