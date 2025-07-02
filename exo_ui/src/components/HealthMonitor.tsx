import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, Heart, Thermometer, Cpu, AlertTriangle, TrendingUp } from 'lucide-react';

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

interface HealthMonitorProps {
  apiUrl: string;
  nodeId: string;
}

const HealthMonitor: React.FC<HealthMonitorProps> = ({ apiUrl, nodeId }) => {
  const [health, setHealth] = useState<NodeHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      setError(null);
      const response = await axios.get(`${apiUrl}/nodes/${nodeId}/health`);
      setHealth(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 3000); // Update every 3 seconds
    return () => clearInterval(interval);
  }, [nodeId]);

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    if (score >= 40) return 'text-orange-500';
    return 'text-red-500';
  };

  const getHealthBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-100 border-green-200';
    if (score >= 60) return 'bg-yellow-100 border-yellow-200';
    if (score >= 40) return 'bg-orange-100 border-orange-200';
    return 'bg-red-100 border-red-200';
  };

  const getLoadColor = (load: number) => {
    if (load < 0.5) return 'text-green-500';
    if (load < 0.8) return 'text-yellow-500';
    return 'text-red-500';
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 animate-spin" />
          <span className="text-sm text-gray-600">Loading health data...</span>
        </div>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-500" />
          <span className="text-sm text-red-700">{error || 'Health data unavailable'}</span>
        </div>
      </div>
    );
  }

  const failureRate = health.tasks_completed + health.tasks_failed > 0 
    ? (health.tasks_failed / (health.tasks_completed + health.tasks_failed)) * 100 
    : 0;

  return (
    <div className={`rounded-lg border-2 p-4 ${getHealthBgColor(health.health_score)}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <Heart className="w-5 h-5 mr-2" />
          Node Health
        </h3>
        <div className="flex items-center space-x-2">
          <span className={`text-2xl font-bold ${getHealthColor(health.health_score)}`}>
            {Math.round(health.health_score)}
          </span>
          <span className="text-sm text-gray-600">/100</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Health Score Progress */}
        <div className="col-span-2">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Health Score</span>
            <span>{Math.round(health.health_score)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${
                health.health_score >= 80 ? 'bg-green-500' :
                health.health_score >= 60 ? 'bg-yellow-500' :
                health.health_score >= 40 ? 'bg-orange-500' : 'bg-red-500'
              }`}
              style={{ width: `${Math.max(0, Math.min(100, health.health_score))}%` }}
            ></div>
          </div>
        </div>

        {/* Current Load */}
        <div className="flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-gray-400" />
          <div>
            <p className="text-xs text-gray-500">CPU Load</p>
            <p className={`text-sm font-semibold ${getLoadColor(health.current_load)}`}>
              {Math.round(health.current_load * 100)}%
            </p>
          </div>
        </div>

        {/* Active Tasks */}
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-gray-400" />
          <div>
            <p className="text-xs text-gray-500">Active Tasks</p>
            <p className="text-sm font-semibold text-gray-900">{health.active_tasks}</p>
          </div>
        </div>

        {/* Tasks Completed */}
        <div className="flex items-center space-x-2">
          <TrendingUp className="w-4 h-4 text-green-500" />
          <div>
            <p className="text-xs text-gray-500">Completed</p>
            <p className="text-sm font-semibold text-green-600">{health.tasks_completed}</p>
          </div>
        </div>

        {/* Tasks Failed */}
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-500" />
          <div>
            <p className="text-xs text-gray-500">Failed</p>
            <p className="text-sm font-semibold text-red-600">
              {health.tasks_failed} ({failureRate.toFixed(1)}%)
            </p>
          </div>
        </div>

        {/* Last Heartbeat */}
        <div className="col-span-2 pt-2 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Thermometer className="w-4 h-4 text-gray-400" />
              <span className="text-xs text-gray-500">Last Heartbeat</span>
            </div>
            <span className={`text-xs font-medium ${
              health.seconds_since_heartbeat < 10 ? 'text-green-600' :
              health.seconds_since_heartbeat < 30 ? 'text-yellow-600' : 'text-red-600'
            }`}>
              {health.seconds_since_heartbeat}s ago
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HealthMonitor;
