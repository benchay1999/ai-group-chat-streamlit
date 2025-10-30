/**
 * EarningsChart Component
 * Mini earnings trend chart showing recent session earnings
 */

import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';

const EarningsChart = ({ data }) => {
  // Transform data for chart - ONLY show actual payments, not calculated suggestions
  const chartData = data.map((session, index) => ({
    index,
    amount: session.amount || 0, // Only admin-set payment amounts
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-600 rounded px-3 py-2 shadow-lg">
          <p className="text-green-400 font-semibold">
            ${payload[0].value.toFixed(2)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height={80}>
      <LineChart data={chartData}>
        <defs>
          <linearGradient id="earningsGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <Tooltip content={<CustomTooltip />} />
        <Line 
          type="monotone" 
          dataKey="amount" 
          stroke="#22c55e" 
          strokeWidth={2}
          dot={{ fill: '#22c55e', r: 3 }}
          activeDot={{ r: 5, fill: '#22c55e', stroke: '#fff', strokeWidth: 2 }}
          fill="url(#earningsGradient)"
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default EarningsChart;

