import React, { useState } from 'react';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  AppBar,
  Toolbar,
  Card,
  CardContent,
  Chip,
  Button,
  LinearProgress,
  IconButton,
  CircularProgress,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  useTheme as useMUITheme,
  alpha,
  Fab,
  Badge,
  Avatar,
  Stack,
  Skeleton,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  VideoLibrary,
  SmartToy,
  Analytics,
  Timeline,
  CloudSync,
  Settings,
  Brightness4,
  Brightness7,
  Notifications,
  Add,
  Code,
  AutoAwesome,
  CheckCircle,
  ErrorOutline,
  HourglassEmpty,
  Refresh,
  FileUpload,
  Api,
  Menu as MenuIconAlt,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { useTheme } from '../../theme/ThemeProvider';
import { DashboardProps, Project } from '../../types/project';

// Enhanced mock data with more realistic metrics
const mockAnalyticsData = [
  { name: 'Jan', videos: 24, success: 22, errors: 2 },
  { name: 'Feb', videos: 35, success: 32, errors: 3 },
  { name: 'Mar', videos: 28, success: 26, errors: 2 },
  { name: 'Apr', videos: 42, success: 38, errors: 4 },
  { name: 'May', videos: 51, success: 48, errors: 3 },
  { name: 'Jun', videos: 38, success: 35, errors: 3 },
];

const performanceData = [
  { name: 'Processing Speed', value: 92 },
  { name: 'Accuracy', value: 96 },
  { name: 'Uptime', value: 99.5 },
  { name: 'User Satisfaction', value: 94 },
];

const pieData = [
  { name: 'Video Analysis', value: 45, color: '#2196f3' },
  { name: 'Code Generation', value: 30, color: '#4caf50' },
  { name: 'File Processing', value: 15, color: '#ff9800' },
  { name: 'API Integration', value: 10, color: '#9c27b0' },
];

// Enhanced project data
const mockProjects: Project[] = [
  {
    id: '1',
    name: 'YouTube AI Content Analyzer',
    status: 'analyzing',
    createdAt: '2024-01-15T10:30:00Z',
    updatedAt: '2024-01-15T11:45:00Z',
    description: 'Advanced AI-powered analysis of educational YouTube content with real-time processing',
    progress: 78,
    type: 'video-analysis'
  },
  {
    id: '2',
    name: 'Multi-Modal Document Pipeline',
    status: 'deployed',
    createdAt: '2024-01-14T14:20:00Z',
    updatedAt: '2024-01-15T09:15:00Z',
    description: 'Enterprise document processing with OCR, NLP, and automated extraction',
    progress: 100,
    type: 'file-upload'
  },
  {
    id: '3',
    name: 'MCP Protocol Integration',
    status: 'processing',
    createdAt: '2024-01-15T16:00:00Z',
    updatedAt: '2024-01-15T16:30:00Z',
    description: 'Advanced Model Context Protocol integration with hybrid AI systems',
    progress: 45,
    type: 'api-integration'
  },
  {
    id: '4',
    name: 'Legacy System Migration',
    status: 'failed',
    createdAt: '2024-01-13T08:45:00Z',
    updatedAt: '2024-01-13T12:20:00Z',
    description: 'Complex data migration with advanced error recovery mechanisms',
    type: 'file-upload'
  },
  {
    id: '5',
    name: 'Neural Network Training Hub',
    status: 'pending',
    createdAt: '2024-01-15T18:00:00Z',
    updatedAt: '2024-01-15T18:00:00Z',
    description: 'Custom ML model training for advanced video content understanding',
    type: 'video-analysis'
  }
];

// Enhanced status and type utilities
const getStatusColor = (status: string) => {
  switch (status) {
    case 'deployed': return 'success';
    case 'analyzing': case 'processing': return 'warning';
    case 'failed': return 'error';
    case 'pending': return 'default';
    default: return 'default';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'deployed': return <CheckCircle />;
    case 'analyzing': case 'processing': return <HourglassEmpty />;
    case 'failed': return <ErrorOutline />;
    case 'pending': return <Refresh />;
    default: return <HourglassEmpty />;
  }
};

const getTypeIcon = (type: string) => {
  switch (type) {
    case 'video-analysis': return <VideoLibrary />;
    case 'file-upload': return <FileUpload />;
    case 'api-integration': return <Api />;
    default: return <Code />;
  }
};

// Enhanced Project Card Component
const EnhancedProjectCard: React.FC<{ project: Project; onClick: (project: Project) => void }> = ({ 
  project, 
  onClick 
}) => {
  const muiTheme = useMUITheme();

  return (
    <Card 
      sx={{ 
        cursor: 'pointer',
        transition: 'all 0.3s ease',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: muiTheme.shadows[8],
        }
      }}
      onClick={() => onClick(project)}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar sx={{ bgcolor: alpha(muiTheme.palette.primary.main, 0.1) }}>
              {getTypeIcon(project.type)}
            </Avatar>
            <Box>
              <Typography variant="h6" component="h3" sx={{ fontWeight: 600 }}>
                {project.name}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {project.description}
              </Typography>
            </Box>
          </Box>
          <Chip
            icon={getStatusIcon(project.status)}
            label={project.status.charAt(0).toUpperCase() + project.status.slice(1)}
            color={getStatusColor(project.status)}
            variant="outlined"
            size="small"
          />
        </Box>

        {project.progress !== undefined && (
          <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">Progress</Typography>
              <Typography variant="body2" color="text.secondary">{project.progress}%</Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={project.progress} 
              sx={{ 
                height: 8, 
                borderRadius: 4,
                backgroundColor: alpha(muiTheme.palette.primary.main, 0.1),
                '& .MuiLinearProgress-bar': {
                  borderRadius: 4,
                }
              }} 
            />
          </Box>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Updated {new Date(project.updatedAt).toLocaleDateString()}
          </Typography>
          <Button size="small" variant="text">
            View Details
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

// Analytics Overview Component
const AnalyticsOverview: React.FC = () => {
  const muiTheme = useMUITheme();

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Analytics sx={{ mr: 1 }} />
        Analytics Overview
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <Card sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Processing Performance</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockAnalyticsData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <RechartsTooltip />
                <Line 
                  type="monotone" 
                  dataKey="videos" 
                  stroke={muiTheme.palette.primary.main} 
                  strokeWidth={2}
                  name="Total Videos"
                />
                <Line 
                  type="monotone" 
                  dataKey="success" 
                  stroke={muiTheme.palette.success.main} 
                  strokeWidth={2}
                  name="Successful"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Grid>

        <Grid item xs={12} lg={4}>
          <Card sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>Task Distribution</Typography>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={80}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
            <Box sx={{ mt: 2 }}>
              {pieData.map((item, index) => (
                <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Box 
                    sx={{ 
                      width: 12, 
                      height: 12, 
                      bgcolor: item.color, 
                      borderRadius: '50%', 
                      mr: 1 
                    }} 
                  />
                  <Typography variant="body2">
                    {item.name}: {item.value}%
                  </Typography>
                </Box>
              ))}
            </Box>
          </Card>
        </Grid>
      </Grid>
    </Paper>
  );
};

// Performance Metrics Component
const PerformanceMetrics: React.FC = () => {
  return (
    <Grid container spacing={3}>
      {performanceData.map((metric, index) => (
        <Grid item xs={12} sm={6} md={3} key={index}>
          <Card sx={{ p: 3, textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
            <Box sx={{ position: 'relative', display: 'inline-flex' }}>
              <CircularProgress
                variant="determinate"
                value={metric.value}
                size={80}
                thickness={4}
                sx={{
                  color: metric.value >= 95 ? 'success.main' : metric.value >= 85 ? 'warning.main' : 'error.main',
                }}
              />
              <Box
                sx={{
                  top: 0,
                  left: 0,
                  bottom: 0,
                  right: 0,
                  position: 'absolute',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Typography variant="h6" component="div" color="text.secondary">
                  {metric.value}%
                </Typography>
              </Box>
            </Box>
            <Typography variant="h6" sx={{ mt: 2, fontWeight: 600 }}>
              {metric.name}
            </Typography>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

// Main Dashboard Component
export const MaterialDashboard: React.FC<DashboardProps> = ({ 
  projects = mockProjects, 
  isLoading = false 
}) => {
  const { mode, toggleTheme } = useTheme();
  const muiTheme = useMUITheme();
  const [activeTab, setActiveTab] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleProjectClick = (project: Project) => {
    console.log('Project clicked:', project);
  };

  const getStatusCounts = () => {
    return projects.reduce((acc, project) => {
      acc[project.status] = (acc[project.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
  };

  const statusCounts = getStatusCounts();

  const sidebarItems = [
    { icon: <DashboardIcon />, label: 'Dashboard', value: 0 },
    { icon: <VideoLibrary />, label: 'Video Processing', value: 1 },
    { icon: <SmartToy />, label: 'AI Agents', value: 2 },
    { icon: <Analytics />, label: 'Analytics', value: 3 },
    { icon: <Timeline />, label: 'Performance', value: 4 },
  ];

  if (isLoading) {
    return (
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Skeleton variant="text" width={200} height={40} />
            <Box sx={{ flexGrow: 1 }} />
            <Skeleton variant="circular" width={40} height={40} />
          </Toolbar>
        </AppBar>
        <Container maxWidth="xl" sx={{ mt: 3 }}>
          <Grid container spacing={3}>
            {[...Array(6)].map((_, i) => (
              <Grid item xs={12} md={6} lg={4} key={i}>
                <Skeleton variant="rectangular" height={200} sx={{ borderRadius: 2 }} />
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, display: 'flex' }}>
      {/* Navigation Drawer */}
      <Drawer
        variant="persistent"
        anchor="left"
        open={drawerOpen}
        sx={{
          width: 240,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: 240,
            boxSizing: 'border-box',
            borderRight: `1px solid ${alpha(muiTheme.palette.divider, 0.12)}`,
          },
        }}
      >
        <Toolbar>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            UVAI Platform
          </Typography>
        </Toolbar>
        <Divider />
        <List>
          {sidebarItems.map((item) => (
            <ListItem 
              button 
              key={item.value}
              selected={activeTab === item.value}
              onClick={() => setActiveTab(item.value)}
              sx={{
                '&.Mui-selected': {
                  bgcolor: alpha(muiTheme.palette.primary.main, 0.1),
                  '&:hover': {
                    bgcolor: alpha(muiTheme.palette.primary.main, 0.15),
                  },
                },
              }}
            >
              <ListItemIcon sx={{ color: activeTab === item.value ? 'primary.main' : 'text.secondary' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItem>
          ))}
        </List>
      </Drawer>

      {/* Main Content */}
      <Box sx={{ flexGrow: 1 }}>
        {/* App Bar */}
        <AppBar position="static" elevation={0}>
          <Toolbar>
            <IconButton
              color="inherit"
              edge="start"
              onClick={() => setDrawerOpen(!drawerOpen)}
              sx={{ mr: 2 }}
            >
              <MenuIconAlt />
            </IconButton>
            
            <AutoAwesome sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
              Universal Video-to-Action Intelligence Platform
            </Typography>
            
            <Stack direction="row" spacing={1} alignItems="center">
              <Button 
                color="inherit" 
                startIcon={<CloudSync />}
                variant="outlined"
                sx={{ 
                  borderColor: alpha('#fff', 0.3),
                  '&:hover': {
                    borderColor: alpha('#fff', 0.5),
                    bgcolor: alpha('#fff', 0.1),
                  }
                }}
              >
                Online
              </Button>
              
              <IconButton color="inherit">
                <Badge badgeContent={3} color="error">
                  <Notifications />
                </Badge>
              </IconButton>
              
              <IconButton color="inherit" onClick={toggleTheme}>
                {mode === 'dark' ? <Brightness7 /> : <Brightness4 />}
              </IconButton>
              
              <IconButton color="inherit">
                <Settings />
              </IconButton>
            </Stack>
          </Toolbar>
        </AppBar>

        {/* Main Content Area */}
        <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
          {activeTab === 0 && (
            <Box>
              {/* Header Section */}
              <Box sx={{ mb: 4, textAlign: 'center' }}>
                <Typography variant="h3" component="h1" sx={{ fontWeight: 700, mb: 2 }}>
                  Enterprise Dashboard
                </Typography>
                <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 800, mx: 'auto' }}>
                  Advanced AI-powered platform for universal video-to-action intelligence with enterprise-grade analytics
                </Typography>
              </Box>

              {/* Performance Metrics */}
              <Box sx={{ mb: 4 }}>
                <Typography variant="h5" sx={{ mb: 3, fontWeight: 600 }}>
                  System Performance
                </Typography>
                <PerformanceMetrics />
              </Box>

              {/* Status Overview Cards */}
              <Box sx={{ mb: 4 }}>
                <Typography variant="h5" sx={{ mb: 3, fontWeight: 600 }}>
                  Project Status Overview
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ p: 3 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                          <DashboardIcon />
                        </Avatar>
                        <Box>
                          <Typography variant="h4" sx={{ fontWeight: 700 }}>
                            {projects.length}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Total Projects
                          </Typography>
                        </Box>
                      </Box>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ p: 3 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ bgcolor: 'success.main', mr: 2 }}>
                          <CheckCircle />
                        </Avatar>
                        <Box>
                          <Typography variant="h4" sx={{ fontWeight: 700 }}>
                            {statusCounts.deployed || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Deployed
                          </Typography>
                        </Box>
                      </Box>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ p: 3 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ bgcolor: 'warning.main', mr: 2 }}>
                          <HourglassEmpty />
                        </Avatar>
                        <Box>
                          <Typography variant="h4" sx={{ fontWeight: 700 }}>
                            {(statusCounts.analyzing || 0) + (statusCounts.processing || 0)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            In Progress
                          </Typography>
                        </Box>
                      </Box>
                    </Card>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={3}>
                    <Card sx={{ p: 3 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar sx={{ bgcolor: 'error.main', mr: 2 }}>
                          <ErrorOutline />
                        </Avatar>
                        <Box>
                          <Typography variant="h4" sx={{ fontWeight: 700 }}>
                            {statusCounts.failed || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Failed
                          </Typography>
                        </Box>
                      </Box>
                    </Card>
                  </Grid>
                </Grid>
              </Box>

              {/* Recent Projects */}
              <Box sx={{ mb: 4 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                  <Typography variant="h5" sx={{ fontWeight: 600 }}>
                    Recent Projects
                  </Typography>
                  <Button 
                    variant="contained" 
                    startIcon={<Add />}
                    sx={{ borderRadius: 2 }}
                  >
                    New Project
                  </Button>
                </Box>
                <Grid container spacing={3}>
                  {projects.map((project) => (
                    <Grid item xs={12} md={6} lg={4} key={project.id}>
                      <EnhancedProjectCard
                        project={project}
                        onClick={handleProjectClick}
                      />
                    </Grid>
                  ))}
                </Grid>
              </Box>

              {/* Platform Status Banner */}
              <Card 
                sx={{ 
                  background: `linear-gradient(135deg, ${muiTheme.palette.primary.main} 0%, ${muiTheme.palette.secondary.main} 100%)`,
                  color: 'white',
                  p: 4,
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <Box sx={{ position: 'relative', zIndex: 2 }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, mb: 2 }}>
                    🚀 Enterprise Platform Status
                  </Typography>
                  <Typography variant="h6" sx={{ mb: 3, opacity: 0.9 }}>
                    Your Universal Video-to-Action Intelligence platform is fully operational with enterprise-grade security and performance
                  </Typography>
                  <Grid container spacing={4}>
                    <Grid item xs={12} md={4}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h3" sx={{ fontWeight: 700 }}>
                          99.9%
                        </Typography>
                        <Typography variant="body1" sx={{ opacity: 0.8 }}>
                          Uptime
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h3" sx={{ fontWeight: 700 }}>
                          10M+
                        </Typography>
                        <Typography variant="body1" sx={{ opacity: 0.8 }}>
                          Videos Processed
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h3" sx={{ fontWeight: 700 }}>
                          $2B+
                        </Typography>
                        <Typography variant="body1" sx={{ opacity: 0.8 }}>
                          Market Value
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Box>
                <Box
                  sx={{
                    position: 'absolute',
                    top: -50,
                    right: -50,
                    width: 200,
                    height: 200,
                    background: 'radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%)',
                    borderRadius: '50%',
                  }}
                />
              </Card>
            </Box>
          )}

          {activeTab === 3 && <AnalyticsOverview />}
          
          {activeTab !== 0 && activeTab !== 3 && (
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="h5" gutterBottom>
                {sidebarItems.find(item => item.value === activeTab)?.label}
              </Typography>
              <Typography variant="body1" color="text.secondary">
                This section is under development. Advanced features coming soon.
              </Typography>
            </Paper>
          )}
        </Container>
      </Box>

      {/* Floating Action Button */}
      <Fab
        color="primary"
        aria-label="add"
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
        }}
      >
        <Add />
      </Fab>
    </Box>
  );
};