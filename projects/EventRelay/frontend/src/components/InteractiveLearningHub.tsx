import React, { useState, useEffect, useRef, useCallback } from 'react';
import YouTube, { YouTubeProps } from 'react-youtube';
import RealLearningAgent from './RealLearningAgent';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import './InteractiveLearningHub.css';

interface Chapter {
  id: string;
  title: string;
  time: string;
  timeSeconds: number;
  duration?: string;
  topics?: string[];
}

interface TranscriptLine {
  id: string;
  text: string;
  start: number;
  end: number;
  speaker?: string;
}

interface Keyframe {
  time: number;
  image: string;
  description: string;
}

interface Resource {
  id: string;
  type: 'code' | 'document' | 'link' | 'exercise';
  title: string;
  url: string;
  chapters?: string[];
}

interface Note {
  id: string;
  text: string;
  timestamp: number;
  createdAt: Date;
}

interface InteractiveLearningHubProps {
  videoId: string;
  videoData: {
    title: string;
    channel: string;
    duration: string;
  };
  chapters: Chapter[];
  transcript: TranscriptLine[];
  keyframes?: Keyframe[];
  resources?: Resource[];
}

export const InteractiveLearningHub: React.FC<InteractiveLearningHubProps> = ({
  videoId,
  videoData,
  chapters,
  transcript,
  keyframes = [],
  resources = []
}) => {
  const [player, setPlayer] = useState<any>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [activeChapter, setActiveChapter] = useState<string>('');
  const [activeTranscriptLine, setActiveTranscriptLine] = useState<string>('');
  const [notes, setNotes] = useState<Note[]>([]);
  const [newNote, setNewNote] = useState('');
  const [showNotes, setShowNotes] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const transcriptRef = useRef<HTMLDivElement>(null);

  // YouTube player options
  const opts: YouTubeProps['opts'] = {
    height: '100%',
    width: '100%',
    playerVars: {
      autoplay: 0,
      modestbranding: 1,
      rel: 0
    }
  };

  // Handle player ready
  const onPlayerReady = (event: any) => {
    setPlayer(event.target);
  };

  // Update time and sync UI
  useEffect(() => {
    if (!player) return;

    const interval = setInterval(() => {
      const time = player.getCurrentTime();
      setCurrentTime(time);

      // Update active chapter
      const chapter = chapters.find((ch, index) => {
        const nextChapter = chapters[index + 1];
        return time >= ch.timeSeconds && (!nextChapter || time < nextChapter.timeSeconds);
      });
      if (chapter) setActiveChapter(chapter.id);

      // Update active transcript line
      const line = transcript.find(t => time >= t.start && time <= t.end);
      if (line) {
        setActiveTranscriptLine(line.id);
        // Auto-scroll transcript
        const element = document.getElementById(`transcript-${line.id}`);
        if (element && transcriptRef.current) {
          const container = transcriptRef.current;
          const elementTop = element.offsetTop;
          const containerHeight = container.clientHeight;
          const scrollTop = elementTop - containerHeight / 2;
          container.scrollTo({ top: scrollTop, behavior: 'smooth' });
        }
      }
    }, 100);

    return () => clearInterval(interval);
  }, [player, chapters, transcript]);

  // Seek to timestamp
  const seekToTime = useCallback((seconds: number) => {
    if (player) {
      player.seekTo(seconds, true);
      player.playVideo();
    }
  }, [player]);

  // Convert time string to seconds
  const timeToSeconds = (time: string): number => {
    const parts = time.split(':').map(Number);
    if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    }
    return parts[0];
  };

  // Add note
  const addNote = () => {
    if (!newNote.trim()) return;
    
    const note: Note = {
      id: Date.now().toString(),
      text: newNote,
      timestamp: currentTime,
      createdAt: new Date()
    };
    
    setNotes([...notes, note]);
    setNewNote('');
  };

  // Format time for display
  const formatTime = (seconds: number): string => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    
    if (h > 0) {
      return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // Filter transcript based on search
  const filteredTranscript = transcript.filter(line =>
    line.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter resources for current chapter
  const currentResources = resources.filter(resource =>
    !resource.chapters || resource.chapters.includes(activeChapter)
  );

  return (
    <div className="interactive-learning-hub">
      <div className="hub-header">
        <h1>{videoData.title}</h1>
        <p className="channel-info">by {videoData.channel} • {videoData.duration}</p>
      </div>

      <div className="hub-container">
        <div className="main-content">
          {/* Video Player */}
          <div className="video-container">
            <YouTube
              videoId={videoId}
              opts={opts}
              onReady={onPlayerReady}
              className="youtube-player"
            />
          </div>

          {/* Video Controls */}
          <div className="video-controls">
            <div className="current-time">
              {formatTime(currentTime)} / {videoData.duration}
            </div>
            <button 
              className="notes-toggle"
              onClick={() => setShowNotes(!showNotes)}
            >
              📝 Notes ({notes.length})
            </button>
          </div>

          {/* Notes Section */}
          {showNotes && (
            <div className="notes-section">
              <div className="add-note">
                <input
                  type="text"
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addNote()}
                  placeholder="Add a note at current timestamp..."
                />
                <button onClick={addNote}>Add Note</button>
              </div>
              <div className="notes-list">
                {notes.map(note => (
                  <div key={note.id} className="note-item">
                    <span 
                      className="note-timestamp"
                      onClick={() => seekToTime(note.timestamp)}
                    >
                      {formatTime(note.timestamp)}
                    </span>
                    <span className="note-text">{note.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Keyframes Gallery */}
          {keyframes.length > 0 && (
            <div className="keyframes-section">
              <h3>Key Moments</h3>
              <div className="keyframes-grid">
                {keyframes.map((kf, index) => (
                  <div 
                    key={index} 
                    className="keyframe-item"
                    onClick={() => seekToTime(kf.time)}
                  >
                    <img src={kf.image} alt={kf.description} />
                    <div className="keyframe-info">
                      <span className="keyframe-time">{formatTime(kf.time)}</span>
                      <span className="keyframe-desc">{kf.description}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="sidebar">
          {/* Chapters Navigation */}
          <div className="chapters-section">
            <h3>Chapters</h3>
            <div className="chapters-list">
              {chapters.map(chapter => (
                <div
                  key={chapter.id}
                  className={`chapter-item ${activeChapter === chapter.id ? 'active' : ''}`}
                  onClick={() => seekToTime(chapter.timeSeconds)}
                >
                  <span className="chapter-time">{chapter.time}</span>
                  <span className="chapter-title">{chapter.title}</span>
                  {chapter.duration && (
                    <span className="chapter-duration">{chapter.duration}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Resources */}
          {currentResources.length > 0 && (
            <div className="resources-section">
              <h3>Resources</h3>
              <div className="resources-list">
                {currentResources.map(resource => (
                  <a
                    key={resource.id}
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`resource-item resource-${resource.type}`}
                  >
                    <span className="resource-icon">
                      {resource.type === 'code' && '💻'}
                      {resource.type === 'document' && '📄'}
                      {resource.type === 'link' && '🔗'}
                      {resource.type === 'exercise' && '✏️'}
                    </span>
                    <span className="resource-title">{resource.title}</span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Transcript Panel */}
      <div className="transcript-panel">
        <div className="transcript-header">
          <h3>Transcript</h3>
          <input
            type="text"
            placeholder="Search transcript..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="transcript-search"
          />
        </div>
        <div className="transcript-content" ref={transcriptRef}>
          {filteredTranscript.map(line => (
            <div
              key={line.id}
              id={`transcript-${line.id}`}
              className={`transcript-line ${activeTranscriptLine === line.id ? 'active' : ''}`}
              onClick={() => seekToTime(line.start)}
            >
              <span className="transcript-time">{formatTime(line.start)}</span>
              <span className="transcript-text">
                {line.speaker && <strong>{line.speaker}: </strong>}
                {line.text}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Default export wrapper with sample data
const InteractiveLearningHubDefault: React.FC = () => {
  const defaultVideoId = 'sample-video-123';
  const defaultVideoData = {
    title: 'Sample Interactive Learning Video',
    channel: 'Sample Channel',
    thumbnail: 'https://via.placeholder.com/320x180',
    duration: '15:30'
  };
  
  const defaultChapters = [
    { id: '1', title: 'Introduction', time: '0:00', timeSeconds: 0, duration: '2:30' },
    { id: '2', title: 'Main Content', time: '2:30', timeSeconds: 150, duration: '10:00' },
    { id: '3', title: 'Summary', time: '12:30', timeSeconds: 750, duration: '3:00' }
  ];
  
  const defaultTranscript = [
    { id: '1', start: 0, end: 5, text: 'Welcome to this interactive learning session.', speaker: 'Instructor' },
    { id: '2', start: 5, end: 10, text: 'Today we will explore advanced concepts.', speaker: 'Instructor' },
    { id: '3', start: 10, end: 15, text: 'Let\'s dive into the main content.', speaker: 'Instructor' }
  ];

  return (
    <InteractiveLearningHub
      videoId={defaultVideoId}
      videoData={defaultVideoData}
      chapters={defaultChapters}
      transcript={defaultTranscript}
    />
  );
};

export default InteractiveLearningHubDefault;
