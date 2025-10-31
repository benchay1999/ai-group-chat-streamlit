import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import { TrendingUp, DollarSign, Activity, Database } from 'lucide-react';
import api from '../services/api';

const AdminAnalyticsPage = () => {
  const [timeRange, setTimeRange] = useState('7d');
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get(`/api/admin/analytics?time_range=${timeRange}`);
      setAnalytics(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load analytics');
      console.error('Analytics error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading analytics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center">
        <div className="text-red-400 text-xl">Error: {error}</div>
      </div>
    );
  }

  const { summary, by_model, time_series, high_cost_sessions } = analytics;

  const StatCard = ({ title, value, subtitle, icon: Icon, color }) => (
    <div className={`bg-gray-800 rounded-lg p-6 border-l-4 ${color}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold text-white mt-2">{value}</p>
          {subtitle && <p className="text-gray-500 text-sm mt-1">{subtitle}</p>}
        </div>
        <Icon className="text-gray-600" size={40} />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Token Usage Analytics</h1>
            <p className="text-gray-400">Monitor API costs and token consumption</p>
          </div>
          
          {/* Time Range Selector */}
          <div className="flex gap-2">
            {['24h', '7d', '30d', 'all'].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  timeRange === range
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                {range === '24h' ? '24 Hours' : range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : 'All Time'}
              </button>
            ))}
          </div>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Cost"
            value={summary.total_cost_formatted}
            subtitle={`Avg: $${summary.avg_cost_per_session.toFixed(4)}/session`}
            icon={DollarSign}
            color="border-green-500"
          />
          <StatCard
            title="Total Tokens"
            value={summary.total_tokens_formatted}
            subtitle={`${summary.total_input_tokens.toLocaleString()} in / ${summary.total_output_tokens.toLocaleString()} out`}
            icon={Activity}
            color="border-blue-500"
          />
          <StatCard
            title="Total Sessions"
            value={summary.total_sessions.toLocaleString()}
            subtitle={`${(summary.total_tokens / summary.total_sessions).toFixed(0)} tokens/session`}
            icon={Database}
            color="border-purple-500"
          />
          <StatCard
            title="Cost Range"
            value={`$${summary.min_cost.toFixed(4)} - $${summary.max_cost.toFixed(4)}`}
            subtitle={`Median: $${summary.median_cost_per_session.toFixed(4)}`}
            icon={TrendingUp}
            color="border-yellow-500"
          />
        </div>

        {/* Cost Over Time Chart */}
        <div className="bg-gray-800 rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-white mb-4">Cost Over Time</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={time_series}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="timestamp" 
                stroke="#9CA3AF"
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return timeRange === '24h' 
                    ? format(date, 'HH:mm')
                    : format(date, 'MM/dd');
                }}
              />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                labelStyle={{ color: '#F3F4F6' }}
                itemStyle={{ color: '#A78BFA' }}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="cost" 
                stroke="#8B5CF6" 
                strokeWidth={2}
                name="Cost ($)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Token Usage by Model */}
        <div className="bg-gray-800 rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-white mb-4">Token Usage by Model</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={Object.entries(by_model).map(([model, stats]) => ({
              model,
              input: stats.input_tokens,
              output: stats.output_tokens
            }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="model" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                labelStyle={{ color: '#F3F4F6' }}
              />
              <Legend />
              <Bar dataKey="input" fill="#3B82F6" name="Input Tokens" />
              <Bar dataKey="output" fill="#8B5CF6" name="Output Tokens" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Model Stats Table */}
        <div className="bg-gray-800 rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-white mb-4">Model Statistics</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Model</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Sessions</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Total Tokens</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Cost</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Avg Cost/Session</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(by_model).map(([model, stats]) => (
                  <tr key={model} className="border-b border-gray-700 hover:bg-gray-750">
                    <td className="py-3 px-4 text-white font-medium">{model}</td>
                    <td className="py-3 px-4 text-right text-gray-300">{stats.sessions}</td>
                    <td className="py-3 px-4 text-right text-gray-300">
                      {(stats.total_tokens).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right text-green-400">{stats.cost_formatted}</td>
                    <td className="py-3 px-4 text-right text-gray-300">
                      ${(stats.cost / stats.sessions).toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* High Cost Sessions */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-2xl font-bold text-white mb-4">Highest Cost Sessions</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Room Code</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Cost</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Tokens</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Model</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Completed</th>
                </tr>
              </thead>
              <tbody>
                {high_cost_sessions.map((session) => (
                  <tr key={session.session_id} className="border-b border-gray-700 hover:bg-gray-750">
                    <td className="py-3 px-4 text-white font-mono text-sm">{session.room_code}</td>
                    <td className="py-3 px-4 text-right text-red-400 font-bold">
                      ${session.cost.toFixed(4)}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-300">
                      {(session.input_tokens + session.output_tokens).toLocaleString()}
                      <span className="text-gray-500 text-xs ml-1">
                        ({session.input_tokens} + {session.output_tokens})
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-300">{session.model}</td>
                    <td className="py-3 px-4 text-gray-400 text-sm">
                      {format(new Date(session.completed_at), 'MMM dd, HH:mm')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminAnalyticsPage;

