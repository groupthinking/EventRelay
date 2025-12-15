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
  Button,
  IconButton,
  Chip,
  LinearProgress,
  Collapse,
  Paper,
  Divider,
  Avatar,
  Stack,
  Tooltip,
  Badge,
  Grid,
  useTheme,
  alpha,
  Fade,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  PlayArrow,
  Bookmark,
  BookmarkBorder,
  CheckCircle,
  CheckCircleOutline,
  ContentCopy,
  ExpandMore,
  ExpandLess,
  UnfoldMore,
  UnfoldLess,
  Print,
  Visibility,
  Schedule,
  Category,
  VideoLibrary,
  Article,
  Timeline,
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

export const VideoAnalysisCard: React.FC<VideoAnalysisCardProps> = ({ videoData, markdownContent }) => {
  const theme = useTheme();
  const [copiedToClipboard, setCopiedToClipboard] = useState(false);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [bookmarkedSections, setBookmarkedSections] = useState<Set<string>>(new Set());
  const [completedSections, setCompletedSections] = useState<Set<string>>(new Set());
  const [showCopyAlert, setShowCopyAlert] = useState(false);

  // Calculate reading time (average 200 words per minute)
  const calculateReadingTime = (text: string): number => {
    const wordCount = text.trim().split(/\s+/).length;
    return Math.max(1, Math.ceil(wordCount / 200));
  };

  const getWordCount = (text: string): number => {
    return text.trim().split(/\s+/).length;
  };

  const copyToClipboard = async (content: string, sectionTitle?: string) => {
    try {
      await navigator.clipboard.writeText(content);
      if (sectionTitle) {
        setCopiedSection(sectionTitle);
        setTimeout(() => setCopiedSection(null), 2000);
      } else {
        setCopiedToClipboard(true);
        setShowCopyAlert(true);
        setTimeout(() => setCopiedToClipboard(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const downloadPDF = () => {
    window.print();
  };

  const toggleSection = (sectionTitle: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionTitle)) {
      newExpanded.delete(sectionTitle);
    } else {
      newExpanded.add(sectionTitle);
    }
    setExpandedSections(newExpanded);
  };

  const toggleBookmark = (sectionTitle: string) => {
    const newBookmarked = new Set(bookmarkedSections);
    if (newBookmarked.has(sectionTitle)) {
      newBookmarked.delete(sectionTitle);
    } else {
      newBookmarked.add(sectionTitle);
    }
    setBookmarkedSections(newBookmarked);
  };

  const toggleCompleted = (sectionTitle: string) => {
    const newCompleted = new Set(completedSections);
    if (newCompleted.has(sectionTitle)) {
      newCompleted.delete(sectionTitle);
    } else {
      newCompleted.add(sectionTitle);
    }
    setCompletedSections(newCompleted);
  };

  const expandAllSections = () => {
    setExpandedSections(new Set(sections.map(s => s.title)));
  };

  const collapseAllSections = () => {
    setExpandedSections(new Set());
  };

  // Parse markdown sections with enhanced metadata
  const sections = useMemo(() => {
    const sectionRegex = /^## (.+)$/gm;
    const matches: RegExpMatchArray[] = [];
    let match;
    while ((match = sectionRegex.exec(markdownContent)) !== null) {
      matches.push(match);
    }
    const sectionsList: Section[] = [];
    
    for (let i = 0; i < matches.length; i++) {
      const title = matches[i][1];
      const startIndex = matches[i].index! + matches[i][0].length;
      const endIndex = matches[i + 1]?.index || markdownContent.length;
      const content = markdownContent.slice(startIndex, endIndex).trim();
      const readingTime = calculateReadingTime(content);
      const wordCount = getWordCount(content);
      sectionsList.push({ title, content, readingTime, wordCount });
    }
    
    return sectionsList;
  }, [markdownContent]);

  const totalReadingTime = sections.reduce((total, section) => total + section.readingTime, 0);
  const completionPercentage = Math.round((completedSections.size / sections.length) * 100);

  return (
    <Paper elevation={2} sx={{ borderRadius: 3, overflow: 'hidden' }}>
      <Card sx={{ minHeight: '600px' }}>
        {/* Enhanced Header with video thumbnail and info */}
        <CardHeader
          avatar={
            videoData.thumbnail ? (
              <Box
                sx={{
                  position: 'relative',
                  width: 120,
                  height: 68,
                  borderRadius: 2,
                  overflow: 'hidden',
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                  '&:hover': { transform: 'scale(1.05)' },
                }}
                onClick={() => window.open(`https://www.youtube.com/watch?v=${videoData.video_id}`, '_blank')}
              >
                <img
                  src={videoData.thumbnail}
                  alt={videoData.title || 'Video thumbnail'}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
                <Box
                  sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'rgba(0,0,0,0.4)',
                    opacity: 0,
                    transition: 'opacity 0.2s',
                    '&:hover': { opacity: 1 },
                  }}
                >
                  <IconButton
                    sx={{
                      color: 'white',
                      backgroundColor: 'rgba(255,255,255,0.2)',
                      '&:hover': { backgroundColor: 'rgba(255,255,255,0.3)' },
                    }}
                  >
                    <PlayArrow />
                  </IconButton>
                </Box>
              </Box>
            ) : (
              <Avatar sx={{ bgcolor: theme.palette.primary.main }}>
                <VideoLibrary />
              </Avatar>
            )
          }
          title={
            <Typography variant="h5" component="h1" sx={{ fontWeight: 600, mb: 1 }}>
              {videoData.title || 'Video Analysis'}
            </Typography>
          }
          subheader={
            <Box>
              {videoData.channel && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  <strong>Channel:</strong> {videoData.channel}
                </Typography>
              )}
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {videoData.category && (
                  <Chip
                    icon={<Category />}
                    label={videoData.category}
                    size="small"
                    variant="outlined"
                    color="primary"
                  />
                )}
                {videoData.duration && (
                  <Chip
                    icon={<Schedule />}
                    label={videoData.duration}
                    size="small"
                    variant="outlined"
                  />
                )}
                {videoData.view_count && (
                  <Chip
                    icon={<Visibility />}
                    label={`${videoData.view_count.toLocaleString()} views`}
                    size="small"
                    variant="outlined"
                  />
                )}
                <Chip
                  icon={<Article />}
                  label={`${totalReadingTime} min read`}
                  size="small"
                  variant="outlined"
                  color="secondary"
                />
              </Stack>
            </Box>
          }
          sx={{ pb: 1 }}
        />

        <CardContent sx={{ pt: 0 }}>
          {/* Progress Section */}
          <Paper
            elevation={1}
            sx={{
              p: 2,
              mb: 3,
              background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)}, ${alpha(theme.palette.secondary.main, 0.1)})`,
              borderRadius: 2,
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Timeline color="primary" />
                Learning Progress
              </Typography>
              <Typography variant="h6" color="primary" sx={{ fontWeight: 600 }}>
                {completionPercentage}%
              </Typography>
            </Box>
            
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {completedSections.size} of {sections.length} sections completed
            </Typography>
            
            <LinearProgress
              variant="determinate"
              value={completionPercentage}
              sx={{
                height: 8,
                borderRadius: 4,
                backgroundColor: alpha(theme.palette.primary.main, 0.1),
                '& .MuiLinearProgress-bar': {
                  borderRadius: 4,
                  background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                },
              }}
            />
          </Paper>

          {/* Control Buttons */}
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 3 }}>
            <Button
              variant="outlined"
              startIcon={<UnfoldMore />}
              onClick={expandAllSections}
              size="small"
            >
              Expand All
            </Button>
            <Button
              variant="outlined"
              startIcon={<UnfoldLess />}
              onClick={collapseAllSections}
              size="small"
            >
              Collapse All
            </Button>
            <Button
              variant={copiedToClipboard ? "contained" : "outlined"}
              startIcon={<ContentCopy />}
              onClick={() => copyToClipboard(markdownContent)}
              size="small"
              color={copiedToClipboard ? "success" : "primary"}
            >
              {copiedToClipboard ? 'Copied!' : 'Copy All'}
            </Button>
            <Button
              variant="outlined"
              startIcon={<Print />}
              onClick={downloadPDF}
              size="small"
            >
              Print
            </Button>
          </Stack>

          {/* Enhanced Markdown sections */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {sections.map((section, index) => (
              <Paper
                key={index}
                elevation={1}
                sx={{
                  overflow: 'hidden',
                  border: completedSections.has(section.title) 
                    ? `2px solid ${theme.palette.success.main}` 
                    : bookmarkedSections.has(section.title)
                    ? `2px solid ${theme.palette.warning.main}`
                    : `1px solid ${theme.palette.divider}`,
                  borderRadius: 2,
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    boxShadow: theme.shadows[4],
                  },
                }}
              >
                {/* Section Header */}
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    p: 2,
                    backgroundColor: completedSections.has(section.title)
                      ? alpha(theme.palette.success.main, 0.1)
                      : bookmarkedSections.has(section.title)
                      ? alpha(theme.palette.warning.main, 0.1)
                      : alpha(theme.palette.primary.main, 0.05),
                    cursor: 'pointer',
                  }}
                  onClick={() => toggleSection(section.title)}
                >
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                      {section.title}
                    </Typography>
                    <Stack direction="row" spacing={2}>
                      <Typography variant="caption" color="text.secondary">
                        {section.readingTime} min read
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {section.wordCount} words
                      </Typography>
                    </Stack>
                  </Box>
                  
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <Tooltip title="Bookmark section">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleBookmark(section.title);
                        }}
                        color={bookmarkedSections.has(section.title) ? "warning" : "default"}
                      >
                        {bookmarkedSections.has(section.title) ? <Bookmark /> : <BookmarkBorder />}
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title="Mark as completed">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleCompleted(section.title);
                        }}
                        color={completedSections.has(section.title) ? "success" : "default"}
                      >
                        {completedSections.has(section.title) ? <CheckCircle /> : <CheckCircleOutline />}
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title="Copy section">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          copyToClipboard(section.content, section.title);
                        }}
                        color={copiedSection === section.title ? "success" : "default"}
                      >
                        <ContentCopy />
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title={expandedSections.has(section.title) ? 'Collapse section' : 'Expand section'}>
                      <IconButton size="small">
                        {expandedSections.has(section.title) ? <ExpandLess /> : <ExpandMore />}
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </Box>
                {/* Section Content */}
                <Collapse in={expandedSections.has(section.title)} timeout="auto">
                  <Box sx={{ p: 3, pt: 0 }}>
                    <Divider sx={{ mb: 2 }} />
                    <Box
                      sx={{
                        '& h3': {
                          ...theme.typography.h6,
                          fontWeight: 600,
                          color: theme.palette.text.primary,
                          mt: 2,
                          mb: 1,
                        },
                        '& h4': {
                          ...theme.typography.subtitle1,
                          fontWeight: 600,
                          color: theme.palette.text.primary,
                          mt: 2,
                          mb: 1,
                        },
                        '& p': {
                          ...theme.typography.body1,
                          lineHeight: 1.7,
                          mb: 2,
                        },
                        '& ul, & ol': {
                          pl: 2,
                          mb: 2,
                        },
                        '& li': {
                          ...theme.typography.body1,
                          mb: 0.5,
                        },
                        '& blockquote': {
                          borderLeft: `4px solid ${theme.palette.primary.main}`,
                          pl: 2,
                          ml: 0,
                          fontStyle: 'italic',
                          backgroundColor: alpha(theme.palette.primary.main, 0.05),
                          py: 1,
                          px: 2,
                          borderRadius: 1,
                          mb: 2,
                        },
                        '& code': {
                          backgroundColor: alpha(theme.palette.text.primary, 0.1),
                          padding: '2px 6px',
                          borderRadius: 1,
                          fontFamily: 'monospace',
                          fontSize: '0.875em',
                        },
                        '& pre': {
                          backgroundColor: alpha(theme.palette.text.primary, 0.05),
                          padding: 2,
                          borderRadius: 1,
                          overflow: 'auto',
                          mb: 2,
                        },
                        '& table': {
                          width: '100%',
                          borderCollapse: 'collapse',
                          mb: 2,
                          '& th, & td': {
                            border: `1px solid ${theme.palette.divider}`,
                            padding: 1,
                            textAlign: 'left',
                          },
                          '& th': {
                            backgroundColor: alpha(theme.palette.primary.main, 0.1),
                            fontWeight: 600,
                          },
                        },
                        '& a': {
                          color: theme.palette.primary.main,
                          textDecoration: 'none',
                          '&:hover': {
                            textDecoration: 'underline',
                          },
                        },
                      }}
                    >
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {section.content}
                      </ReactMarkdown>
                    </Box>
                  </Box>
                </Collapse>
              </Paper>
            ))}
          </Box>

        </CardContent>

        {/* Footer with completion summary */}
        <CardActions sx={{ flexDirection: 'column', alignItems: 'stretch', p: 3, pt: 0 }}>
          <Paper 
            elevation={1} 
            sx={{ 
              p: 3, 
              background: `linear-gradient(135deg, ${alpha(theme.palette.success.main, 0.1)}, ${alpha(theme.palette.info.main, 0.1)})`,
              borderRadius: 2,
            }}
          >
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
              📊 Learning Summary
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={6} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: theme.palette.success.main }}>
                    {completedSections.size}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Completed
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: theme.palette.warning.main }}>
                    {bookmarkedSections.size}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Bookmarked
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: theme.palette.primary.main }}>
                    {totalReadingTime}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Min Read
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: theme.palette.secondary.main }}>
                    {sections.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Sections
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </CardActions>
      </Card>

      {/* Copy Success Notification */}
      <Snackbar
        open={showCopyAlert}
        autoHideDuration={3000}
        onClose={() => setShowCopyAlert(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={() => setShowCopyAlert(false)} 
          severity="success" 
          variant="filled"
          sx={{ width: '100%' }}
        >
          Content copied to clipboard!
        </Alert>
      </Snackbar>
    </Paper>
  );
};

// Default export wrapper with sample data
const VideoAnalysisCardDefault: React.FC = () => {
  const defaultVideoData = {
    video_id: 'sample-video-123',
    title: 'Sample Video Analysis',
    channel: 'Sample Channel',
    thumbnail: 'https://via.placeholder.com/320x180',
    duration: '10:30',
    view_count: 15000,
    category: 'Education'
  };

  const defaultMarkdownContent = `# Sample Video Analysis

## Overview
This is a sample video analysis demonstrating the capabilities of the UVAI platform.

## Key Points
- **Point 1**: Important insight about the video content
- **Point 2**: Another key observation
- **Point 3**: Final takeaway

## Summary
This sample demonstrates how the VideoAnalysisCard component works with default data.`;

  return (
    <VideoAnalysisCard 
      videoData={defaultVideoData} 
      markdownContent={defaultMarkdownContent} 
    />
  );
};

export default VideoAnalysisCardDefault;
