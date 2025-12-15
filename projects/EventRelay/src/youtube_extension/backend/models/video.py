#!/usr/bin/env python3
"""
Video Processing Models
======================

Models for video metadata, processing jobs, analysis results, and caching.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, Float, Index, BigInteger
from sqlalchemy.dialects.postgresql import JSONB, URL
from sqlalchemy.orm import relationship, Mapped, mapped_column
from enum import Enum as PyEnum
from sqlalchemy import Enum

from .base import BaseModel, SearchableMixin

class VideoStatus(PyEnum):
    """Video processing status"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProcessingType(PyEnum):
    """Type of video processing"""
    TRANSCRIPT = "transcript"
    ANALYSIS = "analysis"
    SUMMARY = "summary"
    LEARNING_EXTRACTION = "learning_extraction"
    CODE_GENERATION = "code_generation"
    FULL_PIPELINE = "full_pipeline"

class VideoQuality(PyEnum):
    """Video quality levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HD = "hd"
    UHD = "uhd"

class Video(BaseModel, SearchableMixin):
    """
    Core video model with metadata and processing tracking
    """
    __tablename__ = "videos"
    
    # YouTube video information
    youtube_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        doc="YouTube video ID"
    )
    
    youtube_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Full YouTube URL"
    )
    
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Video title"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Video description"
    )
    
    # Channel information
    channel_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="YouTube channel ID"
    )
    
    channel_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="YouTube channel name"
    )
    
    uploader: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Video uploader name"
    )
    
    # Video metrics
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Video duration in seconds"
    )
    
    view_count: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger,
        nullable=True,
        doc="YouTube view count"
    )
    
    like_count: Mapped[Optional[Integer]] = mapped_column(
        Integer,
        nullable=True,
        doc="YouTube like count"
    )
    
    comment_count: Mapped[Optional[Integer]] = mapped_column(
        Integer,
        nullable=True,
        doc="YouTube comment count"
    )
    
    # Video details
    published_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Video publication date"
    )
    
    language: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="Video language code"
    )
    
    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Video category"
    )
    
    tags: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Video tags"
    )
    
    # Quality and availability
    quality: Mapped[VideoQuality] = mapped_column(
        Enum(VideoQuality),
        default=VideoQuality.MEDIUM,
        nullable=False,
        doc="Video quality level"
    )
    
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether video is still available on YouTube"
    )
    
    age_restricted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether video is age restricted"
    )
    
    # Thumbnails
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Video thumbnail URL"
    )
    
    # Processing status
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus),
        default=VideoStatus.PENDING,
        nullable=False,
        index=True,
        doc="Overall processing status"
    )
    
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Last processing timestamp"
    )
    
    processing_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of processing attempts"
    )
    
    # Raw metadata from yt-dlp
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Raw metadata from video extractor"
    )
    
    # User who added video
    added_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        doc="User who added this video"
    )
    
    # Relationships
    metadata_entries = relationship("VideoMetadata", back_populates="video", lazy="dynamic")
    analyses = relationship("VideoAnalysis", back_populates="video", lazy="dynamic")
    processing_jobs = relationship("VideoProcessingJob", back_populates="video", lazy="dynamic")
    
    def get_formatted_duration(self) -> str:
        """Get human-readable duration"""
        if not self.duration_seconds:
            return "Unknown"
        
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def is_long_form(self) -> bool:
        """Check if video is long-form content (>10 minutes)"""
        return self.duration_seconds and self.duration_seconds > 600
    
    def get_engagement_rate(self) -> float:
        """Calculate engagement rate based on likes and views"""
        if not self.view_count or self.view_count == 0:
            return 0.0
        
        likes = self.like_count or 0
        return (likes / self.view_count) * 100
    
    def __repr__(self) -> str:
        return f"<Video(youtube_id='{self.youtube_id}', title='{self.title[:50]}...')>"

class VideoMetadata(BaseModel):
    """
    Extended video metadata and extracted information
    """
    __tablename__ = "video_metadata"
    
    # Foreign key to video
    video_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("videos.id"),
        nullable=False,
        index=True
    )
    
    # Metadata type and source
    metadata_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of metadata (transcript, captions, chapters, etc.)"
    )
    
    source: Mapped[str] = mapped_column(
        String(50),
        default="youtube",
        nullable=False,
        doc="Source of metadata (youtube, auto-generated, manual)"
    )
    
    # Content
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Metadata content (transcript, captions, etc.)"
    )
    
    structured_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Structured metadata (timestamps, chapters, etc.)"
    )
    
    # Quality and confidence
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score for auto-generated content"
    )
    
    language: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="Language of metadata content"
    )
    
    # Processing information
    extracted_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        doc="When metadata was extracted"
    )
    
    extraction_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Method used to extract metadata"
    )
    
    # Relationships
    video = relationship("Video", back_populates="metadata_entries")
    
    def get_word_count(self) -> int:
        """Get word count of content"""
        if not self.content:
            return 0
        return len(self.content.split())
    
    def get_transcript_segments(self) -> List[Dict[str, Any]]:
        """Get transcript segments with timestamps"""
        if self.metadata_type != "transcript" or not self.structured_data:
            return []
        
        return self.structured_data.get("segments", [])
    
    def __repr__(self) -> str:
        return f"<VideoMetadata(video_id='{self.video_id}', type='{self.metadata_type}')>"

class VideoAnalysis(BaseModel):
    """
    Video analysis results and AI-generated insights
    """
    __tablename__ = "video_analyses"
    
    # Foreign key to video
    video_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("videos.id"),
        nullable=False,
        index=True
    )
    
    # Analysis information
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of analysis (summary, learning_extraction, etc.)"
    )
    
    analyzer_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Name of the analyzer/model used"
    )
    
    analyzer_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Version of the analyzer"
    )
    
    # Analysis results
    title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Analysis title/summary"
    )
    
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Text summary of analysis"
    )
    
    key_points: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Key points extracted from video"
    )
    
    topics: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Topics covered in video"
    )
    
    # Structured analysis data
    analysis_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Detailed analysis results"
    )
    
    # Quality metrics
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence in analysis quality"
    )
    
    completeness_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="How complete the analysis is"
    )
    
    # Processing metrics
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Time taken for analysis"
    )
    
    tokens_processed: Mapped[Optional[Integer]] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of tokens processed"
    )
    
    cost_estimate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Estimated processing cost"
    )
    
    # Relationships
    video = relationship("Video", back_populates="analyses")
    
    def get_topic_frequency(self) -> Dict[str, int]:
        """Get frequency count of topics"""
        # This could be enhanced with actual frequency analysis
        return {topic: 1 for topic in (self.topics or [])}
    
    def get_readability_score(self) -> Optional[float]:
        """Calculate readability score of summary"""
        if not self.summary:
            return None
        
        # Simple readability estimation based on sentence and word count
        sentences = len(self.summary.split('.'))
        words = len(self.summary.split())
        
        if sentences == 0:
            return None
        
        avg_words_per_sentence = words / sentences
        # Simple score: prefer 15-20 words per sentence
        optimal_length = 17.5
        score = max(0, 100 - abs(avg_words_per_sentence - optimal_length) * 2)
        return min(100, score)
    
    def __repr__(self) -> str:
        return f"<VideoAnalysis(video_id='{self.video_id}', type='{self.analysis_type}')>"

class VideoProcessingJob(BaseModel):
    """
    Video processing job tracking and status
    """
    __tablename__ = "video_processing_jobs"
    
    # Foreign key to video
    video_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("videos.id"),
        nullable=False,
        index=True
    )
    
    # Job information
    job_type: Mapped[ProcessingType] = mapped_column(
        Enum(ProcessingType),
        nullable=False,
        index=True,
        doc="Type of processing job"
    )
    
    processor_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Name of processor handling the job"
    )
    
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        index=True,
        doc="Job priority (1=highest, 10=lowest)"
    )
    
    # Job status
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus),
        default=VideoStatus.PENDING,
        nullable=False,
        index=True,
        doc="Job processing status"
    )
    
    progress_percentage: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Job completion percentage"
    )
    
    current_step: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Current processing step"
    )
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Job start time"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Job completion time"
    )
    
    estimated_completion_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Estimated completion time"
    )
    
    # Error handling
    error_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of errors encountered"
    )
    
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Last error message"
    )
    
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retry attempts"
    )
    
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        doc="Maximum retry attempts"
    )
    
    # Configuration
    job_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Job configuration parameters"
    )
    
    # Results
    result_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Job execution results"
    )
    
    # Relationships
    video = relationship("Video", back_populates="processing_jobs")
    
    def get_duration_seconds(self) -> Optional[int]:
        """Get job duration in seconds"""
        if not self.started_at or not self.completed_at:
            return None
        
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds())
    
    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return (self.status == VideoStatus.FAILED and 
                self.retry_count < self.max_retries)
    
    def is_stuck(self, timeout_hours: int = 2) -> bool:
        """Check if job appears stuck"""
        if not self.started_at or self.status != VideoStatus.PROCESSING:
            return False
        
        from datetime import timedelta
        timeout_delta = timedelta(hours=timeout_hours)
        return datetime.utcnow() - self.started_at > timeout_delta
    
    def __repr__(self) -> str:
        return f"<VideoProcessingJob(video_id='{self.video_id}', type='{self.job_type}', status='{self.status}')>"

# Create performance indexes
Index("ix_videos_youtube_id_tenant", Video.youtube_id, Video.tenant_id, unique=True)
Index("ix_videos_status_created", Video.status, Video.created_at)
Index("ix_video_metadata_video_type", VideoMetadata.video_id, VideoMetadata.metadata_type)
Index("ix_video_analyses_video_type", VideoAnalysis.video_id, VideoAnalysis.analysis_type)
Index("ix_video_processing_jobs_status_priority", VideoProcessingJob.status, VideoProcessingJob.priority)
Index("ix_video_processing_jobs_video_type_status", VideoProcessingJob.video_id, VideoProcessingJob.job_type, VideoProcessingJob.status)