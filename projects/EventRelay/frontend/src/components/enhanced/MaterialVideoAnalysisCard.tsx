import React, { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Card,
  CardContent,
  CardHeader,
  CardActions,
  Typography,
  Box,
  Chip,
  Button,
  IconButton,
  Avatar,
  Stack,
  Collapse,
  Divider,
  LinearProgress,
  Tooltip,
  Snackbar,
  Alert,
  Paper,
  Grid,
  useTheme,
  alpha,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel,
  Badge,
  Fade,
} from '@mui/material';
import {
  VideoLibrary,
  PlayArrow,
  Pause,
  ContentCopy,
  Bookmark,
  BookmarkBorder,
  CheckCircle,
  CheckCircleOutline,
  ExpandMore,
  ExpandLess,
  AccessTime,
  Visibility,
  Category,
  Share,
  Download,
  Analytics,
  Speed,
  TextFields,
  AutoAwesome,
  TrendingUp,
  ThumbUp,
  Comment,
  OpenInNew,
} from '@mui/icons-material';

interface VideoAnalysisCardProps {
  videoData: {
    video_id: string;
    title?: string;
    channel?: string;
    thumbnail?: string;
    duration?: string;
    view_count?: number;
    category?: string;
  };
  markdownContent: string;
}

interface Section {
  title: string;
  content: string;
  readingTime: number;
  wordCount: number;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`video-analysis-tabpanel-${index}`}
      aria-labelledby={`video-analysis-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export const MaterialVideoAnalysisCard: React.FC<VideoAnalysisCardProps> = ({ 
  videoData, 
  markdownContent 
}) => {
  const theme = useTheme();
  const [tabValue, setTabValue] = useState(0);
  const [copiedToClipboard, setCopiedToClipboard] = useState(false);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [bookmarkedSections, setBookmarkedSections] = useState<Set<string>>(new Set());
  const [completedSections, setCompletedSections] = useState<Set<string>>(new Set());
  const [isPlaying, setIsPlaying] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  // Calculate reading time (average 200 words per minute)
  const calculateReadingTime = (text: string): number => {
    const wordCount = text.trim().split(/\s+/).length;
    return Math.max(1, Math.ceil(wordCount / 200));
  };

  const getWordCount = (text: string): number => {
    return text.trim().split(/\s+/).length;
  };

  // Parse markdown content into sections
  const sections = useMemo<Section[]>(() => {
    if (!markdownContent) return [];
    
    const lines = markdownContent.split('\\n');
    const sectionList: Section[] = [];
    let currentSection: Partial<Section> | null = null;
    
    lines.forEach((line) => {
      if (line.startsWith('## ') && line.length > 3) {
        if (currentSection) {
          sectionList.push({
            title: currentSection.title!,
            content: currentSection.content!,
            readingTime: calculateReadingTime(currentSection.content!),
            wordCount: getWordCount(currentSection.content!),
          });
        }
        currentSection = {
          title: line.substring(3).trim(),
          content: '',
        };
      } else if (currentSection) {
        currentSection.content += line + '\\n';
      }
    });
    
    if (currentSection) {
      sectionList.push({
        title: currentSection.title!,
        content: currentSection.content!,
        readingTime: calculateReadingTime(currentSection.content!),
        wordCount: getWordCount(currentSection.content!),
      });
    }
    
    return sectionList;
  }, [markdownContent]);

  const totalReadingTime = sections.reduce((total, section) => total + section.readingTime, 0);
  const totalWordCount = sections.reduce((total, section) => total + section.wordCount, 0);
  const completionPercentage = (completedSections.size / sections.length) * 100;

  const copyToClipboard = async (content: string, sectionTitle?: string) => {
    try {
      await navigator.clipboard.writeText(content);
      if (sectionTitle) {
        setCopiedSection(sectionTitle);
        setTimeout(() => setCopiedSection(null), 2000);
      } else {
        setCopiedToClipboard(true);
        setTimeout(() => setCopiedToClipboard(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const toggleSection = (sectionTitle: string) => {
    const newExpandedSections = new Set(expandedSections);
    if (expandedSections.has(sectionTitle)) {
      newExpandedSections.delete(sectionTitle);
    } else {
      newExpandedSections.add(sectionTitle);
    }
    setExpandedSections(newExpandedSections);
  };

  const toggleBookmark = (sectionTitle: string) => {
    const newBookmarkedSections = new Set(bookmarkedSections);
    if (bookmarkedSections.has(sectionTitle)) {
      newBookmarkedSections.delete(sectionTitle);
    } else {
      newBookmarkedSections.add(sectionTitle);
    }
    setBookmarkedSections(newBookmarkedSections);
  };

  const toggleCompleted = (sectionTitle: string) => {
    const newCompletedSections = new Set(completedSections);
    if (completedSections.has(sectionTitle)) {
      newCompletedSections.delete(sectionTitle);
    } else {
      newCompletedSections.add(sectionTitle);
    }
    setCompletedSections(newCompletedSections);
  };

  const formatViewCount = (count: number | undefined): string => {
    if (!count) return 'N/A';
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: 2 }}>
      {/* Main Video Information Card */}
      <Card 
        sx={{ 
          mb: 3,
          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.secondary.main, 0.05)} 100%)`,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <CardHeader
          avatar={
            <Avatar 
              sx={{ 
                bgcolor: 'primary.main',
                width: 56,
                height: 56,
              }}
            >
              <VideoLibrary />
            </Avatar>
          }
          title={
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              {videoData.title || 'Video Analysis'}
            </Typography>
          }
          subheader={
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Channel: {videoData.channel || 'Unknown'}
              </Typography>
              <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                <Chip 
                  icon={<AccessTime />} 
                  label={videoData.duration || 'Unknown'} 
                  size="small" 
                  color="primary" 
                  variant="outlined"
                />
                <Chip 
                  icon={<Visibility />} 
                  label={`${formatViewCount(videoData.view_count)} views`} 
                  size="small" 
                  color="secondary" 
                  variant="outlined"
                />
                {videoData.category && (
                  <Chip 
                    icon={<Category />} 
                    label={videoData.category} 
                    size="small" 
                    color="success" 
                    variant="outlined"
                  />
                )}
              </Stack>
            </Box>
          }
          action={
            <Stack direction="row" spacing={1}>
              <Tooltip title="Share Analysis">
                <IconButton onClick={() => setShareDialogOpen(true)}>
                  <Share />
                </IconButton>
              </Tooltip>
              <Tooltip title="Download Analysis">
                <IconButton>
                  <Download />
                </IconButton>
              </Tooltip>
            </Stack>
          }
        />

        {/* Progress Bar */}
        <CardContent sx={{ pt: 0 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Box sx={{ flex: 1, mr: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Reading Progress: {completionPercentage.toFixed(0)}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={completionPercentage} 
                sx={{ 
                  height: 8, 
                  borderRadius: 4,
                  backgroundColor: alpha(theme.palette.primary.main, 0.1),
                }}
              />
            </Box>
            <Typography variant="body2" color="text.secondary">
              {completedSections.size}/{sections.length}
            </Typography>
          </Box>

          {/* Statistics */}
          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Paper sx={{ p: 2, textAlign: 'center', bgcolor: alpha(theme.palette.info.main, 0.1) }}>
                <Typography variant="h6" color="info.main" sx={{ fontWeight: 600 }}>
                  {totalReadingTime}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Min Read
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Paper sx={{ p: 2, textAlign: 'center', bgcolor: alpha(theme.palette.success.main, 0.1) }}>
                <Typography variant="h6" color="success.main" sx={{ fontWeight: 600 }}>
                  {totalWordCount}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Words
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Paper sx={{ p: 2, textAlign: 'center', bgcolor: alpha(theme.palette.warning.main, 0.1) }}>
                <Typography variant="h6" color="warning.main" sx={{ fontWeight: 600 }}>
                  {sections.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Sections
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Paper sx={{ p: 2, textAlign: 'center', bgcolor: alpha(theme.palette.secondary.main, 0.1) }}>
                <Typography variant="h6" color="secondary.main" sx={{ fontWeight: 600 }}>
                  {bookmarkedSections.size}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Bookmarks
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Tabbed Content */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab icon={<Analytics />} label="Analysis" />
            <Tab icon={<Bookmark />} label={`Bookmarks (${bookmarkedSections.size})`} />
            <Tab icon={<Speed />} label="Quick Actions" />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          {/* Main Analysis Content */}
          <Box sx={{ mb: 2 }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <FormControlLabel
                control={
                  <Switch
                    checked={autoScroll}
                    onChange={(e) => setAutoScroll(e.target.checked)}
                  />
                }
                label="Auto-scroll on complete"
              />
              <Button 
                variant="outlined" 
                onClick={() => copyToClipboard(markdownContent)}
                startIcon={<ContentCopy />}
              >
                Copy All
              </Button>
            </Stack>
          </Box>

          {sections.map((section, index) => (
            <Card 
              key={section.title}
              sx={{ 
                mb: 2, 
                border: completedSections.has(section.title) 
                  ? `2px solid ${theme.palette.success.main}` 
                  : `1px solid ${alpha(theme.palette.divider, 0.12)}`,
                position: 'relative',
              }}
            >
              <CardHeader
                avatar={
                  <Badge
                    badgeContent={index + 1}
                    color="primary"
                    sx={{
                      '& .MuiBadge-badge': {
                        fontSize: '0.75rem',
                        minWidth: 20,
                        height: 20,
                      }
                    }}
                  >
                    <Avatar 
                      sx={{ 
                        bgcolor: completedSections.has(section.title) 
                          ? 'success.main' 
                          : 'primary.main',
                        width: 40,
                        height: 40,
                      }}
                    >
                      {completedSections.has(section.title) ? <CheckCircle /> : <AutoAwesome />}
                    </Avatar>
                  </Badge>
                }
                title={
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    {section.title}
                  </Typography>
                }
                subheader={
                  <Stack direction="row" spacing={1}>
                    <Chip 
                      icon={<AccessTime />} 
                      label={`${section.readingTime} min`} 
                      size="small"
                      color="info"
                      variant="outlined"
                    />
                    <Chip 
                      icon={<TextFields />} 
                      label={`${section.wordCount} words`} 
                      size="small"
                      color="secondary"
                      variant="outlined"
                    />
                  </Stack>
                }
                action={
                  <Stack direction="row" spacing={1}>
                    <Tooltip title={completedSections.has(section.title) ? "Mark Incomplete" : "Mark Complete"}>
                      <IconButton 
                        onClick={() => toggleCompleted(section.title)}
                        color={completedSections.has(section.title) ? "success" : "default"}
                      >
                        {completedSections.has(section.title) ? <CheckCircle /> : <CheckCircleOutline />}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={bookmarkedSections.has(section.title) ? "Remove Bookmark" : "Add Bookmark"}>
                      <IconButton 
                        onClick={() => toggleBookmark(section.title)}
                        color={bookmarkedSections.has(section.title) ? "warning" : "default"}
                      >
                        {bookmarkedSections.has(section.title) ? <Bookmark /> : <BookmarkBorder />}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Copy Section">
                      <IconButton onClick={() => copyToClipboard(section.content, section.title)}>
                        <ContentCopy />
                      </IconButton>
                    </Tooltip>
                    <IconButton onClick={() => toggleSection(section.title)}>
                      {expandedSections.has(section.title) ? <ExpandLess /> : <ExpandMore />}
                    </IconButton>
                  </Stack>
                }
              />

              <Collapse in={expandedSections.has(section.title)}>
                <CardContent>
                  <Paper 
                    sx={{ 
                      p: 3, 
                      bgcolor: alpha(theme.palette.background.default, 0.5),
                      maxHeight: 400,
                      overflow: 'auto',
                    }}
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {section.content}
                    </ReactMarkdown>
                  </Paper>
                </CardContent>
              </Collapse>
            </Card>
          ))}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {/* Bookmarks Tab */}
          {bookmarkedSections.size === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <BookmarkBorder sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                No bookmarks yet
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Bookmark sections to access them quickly here
              </Typography>
            </Box>
          ) : (
            <Stack spacing={2}>
              {Array.from(bookmarkedSections).map((sectionTitle) => {
                const section = sections.find(s => s.title === sectionTitle);
                if (!section) return null;
                
                return (
                  <Card key={sectionTitle} variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        {section.title}
                      </Typography>
                      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                        <Chip 
                          icon={<AccessTime />} 
                          label={`${section.readingTime} min`} 
                          size="small"
                        />
                        <Chip 
                          icon={<TextFields />} 
                          label={`${section.wordCount} words`} 
                          size="small"
                        />
                      </Stack>
                      <Button 
                        variant="outlined" 
                        size="small"
                        onClick={() => {
                          setTabValue(0);
                          toggleSection(section.title);
                        }}
                      >
                        View Section
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
            </Stack>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          {/* Quick Actions Tab */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card sx={{ textAlign: 'center', p: 3 }}>
                <TrendingUp sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Progress Report
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Generate a progress report of your reading
                </Typography>
                <Button variant="contained" fullWidth>
                  Generate Report
                </Button>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Card sx={{ textAlign: 'center', p: 3 }}>
                <Comment sx={{ fontSize: 48, color: 'secondary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Add Notes
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Add personal notes to sections
                </Typography>
                <Button variant="contained" color="secondary" fullWidth>
                  Add Notes
                </Button>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Card sx={{ textAlign: 'center', p: 3 }}>
                <OpenInNew sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Export Analysis
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Export to PDF, Word, or other formats
                </Typography>
                <Button variant="contained" color="success" fullWidth>
                  Export
                </Button>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Share Dialog */}
      <Dialog open={shareDialogOpen} onClose={() => setShareDialogOpen(false)}>
        <DialogTitle>Share Analysis</DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Share this video analysis with others:
          </Typography>
          <Stack spacing={2}>
            <Button variant="outlined" startIcon={<ContentCopy />}>
              Copy Link
            </Button>
            <Button variant="outlined" startIcon={<Download />}>
              Download PDF
            </Button>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShareDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbars */}
      <Snackbar
        open={copiedToClipboard}
        autoHideDuration={2000}
        onClose={() => setCopiedToClipboard(false)}
      >
        <Alert severity="success">
          Content copied to clipboard!
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!copiedSection}
        autoHideDuration={2000}
        onClose={() => setCopiedSection(null)}
      >
        <Alert severity="success">
          "{copiedSection}" section copied to clipboard!
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default MaterialVideoAnalysisCard;