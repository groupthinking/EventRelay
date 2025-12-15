#!/usr/bin/env python3
"""
Learning Management Models
=========================

Models for learning outcomes, paths, progress tracking, and knowledge management.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, Float, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from enum import Enum as PyEnum
from sqlalchemy import Enum

from .base import BaseModel, SearchableMixin

class LearningType(PyEnum):
    """Types of learning content"""
    CONCEPT = "concept"
    SKILL = "skill"
    PROCESS = "process"
    TOOL = "tool"
    FRAMEWORK = "framework"
    BEST_PRACTICE = "best_practice"

class DifficultyLevel(PyEnum):
    """Learning difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ProgressStatus(PyEnum):
    """Learning progress status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"

class LearningOutcome(BaseModel, SearchableMixin):
    """
    Learning outcomes extracted from videos
    """
    __tablename__ = "learning_outcomes"
    
    # Source video
    video_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("videos.id"),
        nullable=False,
        index=True,
        doc="Source video ID"
    )
    
    # Learning content
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Learning outcome title"
    )
    
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed description of what can be learned"
    )
    
    learning_type: Mapped[LearningType] = mapped_column(
        Enum(LearningType),
        nullable=False,
        index=True,
        doc="Type of learning content"
    )
    
    difficulty_level: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel),
        default=DifficultyLevel.INTERMEDIATE,
        nullable=False,
        index=True,
        doc="Difficulty level"
    )
    
    # Learning structure
    prerequisites: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Required knowledge before learning this"
    )
    
    learning_objectives: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Specific learning objectives"
    )
    
    key_concepts: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Key concepts covered"
    )
    
    skills_gained: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Skills that will be gained"
    )
    
    # Timing and structure
    estimated_time_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Estimated time to learn this outcome"
    )
    
    video_timestamps: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Relevant timestamps in the source video"
    )
    
    # Quality metrics
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        nullable=False,
        doc="Confidence in learning outcome extraction"
    )
    
    relevance_score: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        nullable=False,
        doc="Relevance score for learning content"
    )
    
    # Categorization
    domain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Learning domain (programming, design, business, etc.)"
    )
    
    subdomain: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Specific subdomain or technology"
    )
    
    tags: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Learning outcome tags"
    )
    
    # Implementation details
    actionable_steps: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Concrete steps to implement this learning"
    )
    
    resources: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Additional learning resources"
    )
    
    examples: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Code examples or practical examples"
    )
    
    # Relationships
    video = relationship("Video")
    progress_entries = relationship("LearningProgress", back_populates="learning_outcome", lazy="dynamic")
    
    def get_completion_rate(self) -> float:
        """Get completion rate across all users"""
        total_progress = self.progress_entries.count()
        if total_progress == 0:
            return 0.0
        
        completed = self.progress_entries.filter_by(status=ProgressStatus.COMPLETED).count()
        mastered = self.progress_entries.filter_by(status=ProgressStatus.MASTERED).count()
        
        return ((completed + mastered) / total_progress) * 100
    
    def get_average_rating(self) -> Optional[float]:
        """Get average user rating for this learning outcome"""
        ratings = [p.rating for p in self.progress_entries if p.rating is not None]
        return sum(ratings) / len(ratings) if ratings else None
    
    def is_practical(self) -> bool:
        """Check if learning outcome has practical implementation steps"""
        return len(self.actionable_steps) > 0 or len(self.examples) > 0
    
    def __repr__(self) -> str:
        return f"<LearningOutcome(title='{self.title[:50]}...', type='{self.learning_type}')>"

class LearningPath(BaseModel):
    """
    Structured learning paths combining multiple outcomes
    """
    __tablename__ = "learning_paths"
    
    # Path information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Learning path name"
    )
    
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Learning path description"
    )
    
    # Path structure
    difficulty_level: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel),
        default=DifficultyLevel.INTERMEDIATE,
        nullable=False,
        index=True,
        doc="Overall difficulty level"
    )
    
    estimated_hours: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Estimated completion time in hours"
    )
    
    # Categorization
    domain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Primary learning domain"
    )
    
    topics: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Topics covered in this path"
    )
    
    tags: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Path tags and keywords"
    )
    
    # Path structure
    learning_outcomes: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Ordered list of learning outcome IDs"
    )
    
    prerequisites: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Prerequisites for starting this path"
    )
    
    # Path metadata
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether path is publicly visible"
    )
    
    is_curated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether path is professionally curated"
    )
    
    creator_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=True,
        doc="User who created this path"
    )
    
    # Quality metrics
    rating: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Average user rating"
    )
    
    completion_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Completion rate percentage"
    )
    
    # Additional resources
    resources: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Additional learning resources"
    )
    
    # Relationships
    progress_entries = relationship("LearningProgress", back_populates="learning_path", lazy="dynamic")
    creator = relationship("User")
    
    def get_completion_stats(self) -> Dict[str, int]:
        """Get completion statistics"""
        total = self.progress_entries.count()
        if total == 0:
            return {"total": 0, "completed": 0, "in_progress": 0, "not_started": 0}
        
        stats = {
            "total": total,
            "completed": self.progress_entries.filter_by(status=ProgressStatus.COMPLETED).count(),
            "in_progress": self.progress_entries.filter_by(status=ProgressStatus.IN_PROGRESS).count(),
            "not_started": self.progress_entries.filter_by(status=ProgressStatus.NOT_STARTED).count()
        }
        stats["mastered"] = self.progress_entries.filter_by(status=ProgressStatus.MASTERED).count()
        
        return stats
    
    def get_outcome_count(self) -> int:
        """Get number of learning outcomes in this path"""
        return len(self.learning_outcomes or [])
    
    def __repr__(self) -> str:
        return f"<LearningPath(name='{self.name}', domain='{self.domain}')>"

class LearningProgress(BaseModel):
    """
    Individual user progress on learning outcomes and paths
    """
    __tablename__ = "learning_progress"
    
    # User and content
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="User ID"
    )
    
    learning_outcome_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("learning_outcomes.id"),
        nullable=True,
        index=True,
        doc="Learning outcome ID (if tracking individual outcome)"
    )
    
    learning_path_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("learning_paths.id"),
        nullable=True,
        index=True,
        doc="Learning path ID (if tracking path progress)"
    )
    
    # Progress tracking
    status: Mapped[ProgressStatus] = mapped_column(
        Enum(ProgressStatus),
        default=ProgressStatus.NOT_STARTED,
        nullable=False,
        index=True,
        doc="Current progress status"
    )
    
    progress_percentage: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Progress completion percentage"
    )
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="When user started learning"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="When user completed learning"
    )
    
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Last access timestamp"
    )
    
    time_spent_minutes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Total time spent learning (minutes)"
    )
    
    # User feedback
    rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="User rating (1-5)"
    )
    
    feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User feedback text"
    )
    
    difficulty_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="User-perceived difficulty (1-5)"
    )
    
    # Learning data
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User notes and thoughts"
    )
    
    bookmarks: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Bookmarked sections or timestamps"
    )
    
    achievements: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Learning achievements unlocked"
    )
    
    # Progress metadata
    learning_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Additional learning progress data"
    )
    
    # Assessment results
    quiz_scores: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Quiz and assessment scores"
    )
    
    skill_assessments: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Skill-based assessments"
    )
    
    # Relationships
    user = relationship("User")
    learning_outcome = relationship("LearningOutcome", back_populates="progress_entries")
    learning_path = relationship("LearningPath", back_populates="progress_entries")
    
    def get_learning_streak(self) -> int:
        """Calculate current learning streak in days"""
        # This would need to be implemented with daily activity tracking
        return 0
    
    def add_time_spent(self, minutes: int) -> None:
        """Add time spent learning"""
        self.time_spent_minutes += minutes
        self.last_accessed_at = datetime.utcnow()
    
    def mark_completed(self) -> None:
        """Mark learning as completed"""
        self.status = ProgressStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100.0
    
    def add_bookmark(self, timestamp: int, title: str, notes: Optional[str] = None) -> None:
        """Add a bookmark"""
        if self.bookmarks is None:
            self.bookmarks = []
        
        bookmark = {
            "timestamp": timestamp,
            "title": title,
            "notes": notes,
            "created_at": datetime.utcnow().isoformat()
        }
        self.bookmarks.append(bookmark)
    
    def __repr__(self) -> str:
        return f"<LearningProgress(user_id='{self.user_id}', status='{self.status}')>"

# Create performance indexes
Index("ix_learning_outcomes_domain_difficulty", LearningOutcome.domain, LearningOutcome.difficulty_level)
Index("ix_learning_outcomes_confidence_relevance", LearningOutcome.confidence_score, LearningOutcome.relevance_score)
Index("ix_learning_paths_domain_public", LearningPath.domain, LearningPath.is_public)
Index("ix_learning_progress_user_status", LearningProgress.user_id, LearningProgress.status)
Index("ix_learning_progress_outcome_status", LearningProgress.learning_outcome_id, LearningProgress.status)
Index("ix_learning_progress_path_status", LearningProgress.learning_path_id, LearningProgress.status)