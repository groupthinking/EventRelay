import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  useTheme,
  alpha,
  Stack,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ScatterChart,
  Scatter,
  ComposedChart,
  Legend,
} from 'recharts';
import {
  Analytics,
  Speed,
  VideoLibrary,
  Timeline,
  Security,
} from '@mui/icons-material';

// Sample data for different chart types
const videoProcessingData = [
  { time: '00:00', processed: 12, queued: 8, errors: 1 },
  { time: '02:00', processed: 18, queued: 5, errors: 0 },
  { time: '04:00', processed: 24, queued: 12, errors: 2 },
  { time: '06:00', processed: 35, queued: 6, errors: 1 },
  { time: '08:00', processed: 42, queued: 15, errors: 0 },
  { time: '10:00', processed: 38, queued: 9, errors: 3 },
  { time: '12:00', processed: 28, queued: 7, errors: 1 },
  { time: '14:00', processed: 45, queued: 11, errors: 2 },
  { time: '16:00', processed: 52, queued: 8, errors: 1 },
  { time: '18:00', processed: 31, queued: 14, errors: 0 },
  { time: '20:00', processed: 22, queued: 6, errors: 1 },
  { time: '22:00', processed: 16, queued: 4, errors: 0 },
];

const performanceMetrics = [
  { category: 'Processing Speed', current: 92, target: 95 },
  { category: 'Accuracy', current: 96, target: 98 },
  { category: 'Uptime', current: 99.5, target: 99.9 },
  { category: 'Response Time', current: 85, target: 90 },
  { category: 'Throughput', current: 88, target: 95 },
  { category: 'Error Rate', current: 95, target: 98 },
];

const technologyUsage = [
  { name: 'Video Analysis', value: 42, color: '#2196f3' },
  { name: 'AI Processing', value: 28, color: '#4caf50' },
  { name: 'Data Pipeline', value: 18, color: '#ff9800' },
  { name: 'API Integration', value: 12, color: '#9c27b0' },
];

const systemHealth = [
  { component: 'Frontend', health: 98, load: 65 },
  { component: 'Backend API', health: 95, load: 78 },
  { component: 'Database', health: 92, load: 45 },
  { component: 'AI Models', health: 88, load: 82 },
  { component: 'File Storage', health: 96, load: 35 },
  { component: 'Queue System', health: 94, load: 58 },
];

const userEngagement = [
  { hour: 0, users: 24, sessions: 18 },
  { hour: 3, users: 12, sessions: 8 },
  { hour: 6, users: 45, sessions: 32 },
  { hour: 9, users: 78, sessions: 65 },
  { hour: 12, users: 95, sessions: 85 },
  { hour: 15, users: 88, sessions: 76 },
  { hour: 18, users: 65, sessions: 48 },
  { hour: 21, users: 42, sessions: 35 },
];

interface ChartCardProps {
  title: string;
  icon: React.ReactElement;
  children: React.ReactNode;
  height?: number;
}

const ChartCard: React.FC<ChartCardProps> = ({ title, icon, children, height = 300 }) => {
  const theme = useTheme();
  
  return (
    <Card 
      sx={{ 
        height: '100%',
        transition: 'all 0.3s ease',
        '&:hover': {
          boxShadow: theme.shadows[8],
          transform: 'translateY(-2px)',
        }
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box 
            sx={{ 
              p: 1, 
              borderRadius: 2, 
              bgcolor: alpha(theme.palette.primary.main, 0.1),
              mr: 2,
              color: 'primary.main'
            }}
          >
            {icon}
          </Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
        </Box>
        <Box sx={{ height }}>
          {children}
        </Box>
      </CardContent>
    </Card>
  );
};

// Custom tooltip component
const CustomTooltip = ({ active, payload, label }: any) => {
  const theme = useTheme();
  
  if (active && payload && payload.length) {
    return (
      <Box
        sx={{
          bgcolor: alpha(theme.palette.background.paper, 0.95),
          backdropFilter: 'blur(10px)',
          p: 2,
          border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
          borderRadius: 2,
          boxShadow: theme.shadows[8],
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
          {label}
        </Typography>
        {payload.map((entry: any, index: number) => (
          <Typography
            key={index}
            variant="body2"
            sx={{ color: entry.color }}
          >
            {entry.name}: {entry.value}
          </Typography>
        ))}
      </Box>
    );
  }
  return null;
};

export const VideoProcessingChart: React.FC = () => {
  const theme = useTheme();
  
  return (
    <ChartCard title="Real-time Video Processing" icon={<VideoLibrary />}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={videoProcessingData}>
          <defs>
            <linearGradient id="processedGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.8}/>
              <stop offset="95%" stopColor={theme.palette.primary.main} stopOpacity={0.1}/>
            </linearGradient>
            <linearGradient id="queuedGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={theme.palette.warning.main} stopOpacity={0.8}/>
              <stop offset="95%" stopColor={theme.palette.warning.main} stopOpacity={0.1}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.2)} />
          <XAxis dataKey="time" stroke={theme.palette.text.secondary} />
          <YAxis stroke={theme.palette.text.secondary} />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="processed"
            stackId="1"
            stroke={theme.palette.primary.main}
            fill="url(#processedGradient)"
            strokeWidth={2}
            name="Processed"
          />
          <Area
            type="monotone"
            dataKey="queued"
            stackId="1"
            stroke={theme.palette.warning.main}
            fill="url(#queuedGradient)"
            strokeWidth={2}
            name="Queued"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
};

export const PerformanceRadarChart: React.FC = () => {
  const theme = useTheme();
  
  return (
    <ChartCard title="System Performance Metrics" icon={<Speed />}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={performanceMetrics}>
          <PolarGrid stroke={alpha(theme.palette.divider, 0.3)} />
          <PolarAngleAxis 
            dataKey="category" 
            tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          />
          <PolarRadiusAxis 
            angle={90} 
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: theme.palette.text.secondary }}
          />
          <Radar
            name="Current"
            dataKey="current"
            stroke={theme.palette.primary.main}
            fill={alpha(theme.palette.primary.main, 0.3)}
            strokeWidth={2}
          />
          <Radar
            name="Target"
            dataKey="target"
            stroke={theme.palette.success.main}
            fill={alpha(theme.palette.success.main, 0.1)}
            strokeWidth={2}
          />
          <Legend />
        </RadarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
};

export const TechnologyUsagePieChart: React.FC = () => {
  const theme = useTheme();
  
  return (
    <ChartCard title="Technology Usage Distribution" icon={<Analytics />} height={350}>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie
            data={technologyUsage}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            dataKey="value"
            label={({ name, value }) => `${name}: ${value}%`}
          >
            {technologyUsage.map((entry, index) => (
              <Cell key={index} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      
      {/* Legend */}
      <Stack direction="row" spacing={2} sx={{ mt: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
        {technologyUsage.map((item, index) => (
          <Stack key={index} direction="row" alignItems="center" spacing={1}>
            <Box 
              sx={{ 
                width: 12, 
                height: 12, 
                bgcolor: item.color, 
                borderRadius: '50%' 
              }} 
            />
            <Typography variant="body2">
              {item.name}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </ChartCard>
  );
};

export const SystemHealthScatterChart: React.FC = () => {
  const theme = useTheme();
  
  return (
    <ChartCard title="System Health vs Load" icon={<Security />}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart data={systemHealth}>
          <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.2)} />
          <XAxis 
            dataKey="load" 
            name="Load %" 
            stroke={theme.palette.text.secondary}
            label={{ value: 'System Load (%)', position: 'insideBottom', offset: -10 }}
          />
          <YAxis 
            dataKey="health" 
            name="Health %" 
            stroke={theme.palette.text.secondary}
            label={{ value: 'System Health (%)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <Box
                    sx={{
                      bgcolor: alpha(theme.palette.background.paper, 0.95),
                      backdropFilter: 'blur(10px)',
                      p: 2,
                      border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
                      borderRadius: 2,
                      boxShadow: theme.shadows[8],
                    }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {data.component}
                    </Typography>
                    <Typography variant="body2">
                      Health: {data.health}%
                    </Typography>
                    <Typography variant="body2">
                      Load: {data.load}%
                    </Typography>
                  </Box>
                );
              }
              return null;
            }}
          />
          <Scatter 
            name="Components" 
            fill={theme.palette.primary.main}
            stroke={theme.palette.primary.dark}
            strokeWidth={2}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </ChartCard>
  );
};

export const UserEngagementComposedChart: React.FC = () => {
  const theme = useTheme();
  
  return (
    <ChartCard title="User Engagement Analytics" icon={<Timeline />}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={userEngagement}>
          <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.2)} />
          <XAxis 
            dataKey="hour" 
            stroke={theme.palette.text.secondary}
            label={{ value: 'Hour of Day', position: 'insideBottom', offset: -10 }}
          />
          <YAxis stroke={theme.palette.text.secondary} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar 
            dataKey="users" 
            fill={alpha(theme.palette.primary.main, 0.6)} 
            name="Active Users"
          />
          <Line
            type="monotone"
            dataKey="sessions"
            stroke={theme.palette.success.main}
            strokeWidth={3}
            name="Sessions"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  );
};

// Main dashboard component that combines all charts
export const AdvancedAnalyticsDashboard: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 4, textAlign: 'center' }}>
        Advanced Analytics Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <VideoProcessingChart />
        </Grid>
        
        <Grid item xs={12} lg={4}>
          <TechnologyUsagePieChart />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <PerformanceRadarChart />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <SystemHealthScatterChart />
        </Grid>
        
        <Grid item xs={12}>
          <UserEngagementComposedChart />
        </Grid>
      </Grid>
    </Box>
  );
};

// Backwards-compatible export for existing panels that still import { AdvancedCharts }
export const AdvancedCharts = AdvancedAnalyticsDashboard;

export default AdvancedAnalyticsDashboard;
