/**
 * EarningsChart Component
 * Mini earnings trend chart showing recent session earnings (in gems)
 * Supports positive (green) and negative (red) values
 */

import { LineChart, Line, ResponsiveContainer, Tooltip, YAxis, ReferenceLine, CartesianGrid } from 'recharts';

const EarningsChart = ({ data }) => {
  // Transform data for chart - shows gem earnings per session
  const chartData = data.map((session, index) => ({
    index,
    amount: session.amount || 0, // Gem amounts (can be negative)
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const value = payload[0].value;
      const isPositive = value >= 0;
      return (
        <div className="bg-gray-800 border border-gray-600 rounded px-3 py-2 shadow-lg">
          <p className={`font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {isPositive ? '+' : ''}{value.toLocaleString()} gems
          </p>
        </div>
      );
    }
    return null;
  };

  // Custom dot color based on value
  const CustomDot = (props) => {
    const { cx, cy, payload } = props;
    const isPositive = payload.amount >= 0;
    const fill = isPositive ? '#22c55e' : '#ef4444';
    return (
      <circle cx={cx} cy={cy} r={3} fill={fill} />
    );
  };

  return (
    <ResponsiveContainer width="100%" height={150}>
      <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="positiveGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="negativeGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
        <YAxis 
          stroke="#9ca3af"
          tick={{ fill: '#9ca3af', fontSize: 12 }}
          tickFormatter={(value) => value >= 0 ? `+${value}` : value}
          width={50}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="3 3" />
        <Line 
          type="monotone" 
          dataKey="amount" 
          stroke="#22c55e" 
          strokeWidth={2}
          dot={<CustomDot />}
          activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default EarningsChart;

