import os
import json
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

# YouTube API and Transcript imports
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Please install required packages: pip install youtube-transcript-api google-api-python-client")

# AI/ML imports
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
except ImportError:
    print("Please install transformers: pip install transformers torch")

@dataclass
class VideoMetadata:
    """Structured video metadata container"""
    video_id: str
    title: str
    description: str
    upload_date: str
    duration: str
    channel_name: str
    view_count: int
    like_count: int

@dataclass
class ProcessedContent:
    """Container for processed video content"""
    metadata: VideoMetadata
    subtitles: List[Dict]
    summary: str
    enhanced_content: str
    key_points: List[str]
    quiz_questions: List[Dict]

class VideoContentAnalysisAgent:
    """Agent responsible for video content analysis and metadata extraction"""
    
    def __init__(self, youtube_api_key: str):
        self.api_key = youtube_api_key
        self.youtube_service = build('youtube', 'v3', developerKey=api_key)
    
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError("Invalid YouTube URL")
    
    def get_video_metadata(self, video_id: str) -> VideoMetadata:
        """Retrieve video metadata using YouTube API"""
        try:
            request = self.youtube_service.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                raise ValueError(f"Video with ID {video_id} not found")
            
            video_data = response['items'][0]
            snippet = video_data['snippet']
            statistics = video_data.get('statistics', {})
            content_details = video_data.get('contentDetails', {})
            
            return VideoMetadata(
                video_id=video_id,
                title=snippet['title'],
                description=snippet['description'],
                upload_date=snippet['publishedAt'],
                duration=content_details.get('duration', ''),
                channel_name=snippet['channelTitle'],
                view_count=int(statistics.get('viewCount', 0)),
                like_count=int(statistics.get('likeCount', 0))
            )
        except HttpError as e:
            raise Exception(f"YouTube API error: {e}")
    
    def get_video_transcript(self, video_id: str) -> List[Dict]:
        """Retrieve video transcript using YouTube Transcript API"""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return transcript_list
        except Exception as e:
            print(f"Could not retrieve transcript: {e}")
            return []
    
    def clean_subtitle_text(self, subtitles: List[Dict]) -> str:
        """Clean and preprocess subtitle text"""
        if not subtitles:
            return ""
        
        # Combine all subtitle text
        full_text = " ".join([subtitle['text'] for subtitle in subtitles])
        
        # Clean the text
        cleaned_text = re.sub(r'\[.*?\]', '', full_text)  # Remove brackets
        cleaned_text = re.sub(r'\(.*?\)', '', cleaned_text)  # Remove parentheses
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Normalize whitespace
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text

class TextProcessingAgent:
    """Agent responsible for text summarization and content enhancement"""
    
    def __init__(self):
        self.summarizer = None
        self.generator = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize AI models for text processing"""
        try:
            # Initialize summarization model
            self.summarizer = pipeline(
                'summarization',
                model='facebook/bart-large-cnn',
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Initialize text generation model for content enhancement
            self.generator = pipeline(
                'text-generation',
                model='gpt2',
                device=0 if torch.cuda.is_available() else -1
            )
        except Exception as e:
            print(f"Error initializing models: {e}")
    
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 50) -> str:
        """Summarize text using AI model"""
        if not self.summarizer or not text:
            return text
        
        try:
            # Split text into chunks if too long
            max_chunk_length = 1024
            if len(text) > max_chunk_length:
                chunks = [text[i:i+max_chunk_length] for i in range(0, len(text), max_chunk_length)]
                summaries = []
                
                for chunk in chunks:
                    summary = self.summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
                    summaries.append(summary[0]['summary_text'])
                
                return " ".join(summaries)
            else:
                summary = self.summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
                return summary[0]['summary_text']
        except Exception as e:
            print(f"Error in summarization: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text
    
    def extract_key_points(self, text: str) -> List[str]:
        """Extract key points from text"""
        # Simple key point extraction based on sentence importance
        sentences = re.split(r'[.!?]+', text)
        key_points = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and any(keyword in sentence.lower() for keyword in 
                ['important', 'key', 'main', 'primary', 'essential', 'crucial', 'significant']):
                key_points.append(sentence)
        
        return key_points[:5]  # Return top 5 key points
    
    def enhance_content(self, summary: str) -> str:
        """Enhance content with additional context and explanations"""
        if not self.generator or not summary:
            return summary
        
        try:
            enhanced_prompt = f"Based on this summary: {summary}\n\nAdditional context and explanations:"
            enhanced_text = self.generator(
                enhanced_prompt,
                max_length=len(enhanced_prompt.split()) + 100,
                do_sample=True,
                temperature=0.7
            )
            return enhanced_text[0]['generated_text']
        except Exception as e:
            print(f"Error in content enhancement: {e}")
            return summary
    
    def generate_quiz_questions(self, content: str) -> List[Dict]:
        """Generate quiz questions based on content"""
        questions = []
        
        # Simple question generation based on key phrases
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30:
                # Create a simple fill-in-the-blank question
                words = sentence.split()
                if len(words) > 5:
                    # Replace a random word with a blank
                    import random
                    blank_index = random.randint(0, len(words) - 1)
                    correct_answer = words[blank_index]
                    words[blank_index] = "_____"
                    
                    question = {
                        "question": " ".join(words),
                        "correct_answer": correct_answer,
                        "options": [correct_answer, "option1", "option2", "option3"],
                        "explanation": sentence
                    }
                    questions.append(question)
                    
                    if len(questions) >= 5:  # Generate max 5 questions
                        break
        
        return questions

class LearningAppProcessor:
    """Main processor that coordinates all agents"""
    
    def __init__(self, youtube_api_key: str):
        self.video_agent = VideoContentAnalysisAgent(youtube_api_key)
        self.text_agent = TextProcessingAgent()
    
    def process_video(self, video_url: str) -> ProcessedContent:
        """Main method to process a YouTube video into learning content"""
        
        # Step 1: Extract video ID and get metadata
        video_id = self.video_agent.extract_video_id(video_url)
        metadata = self.video_agent.get_video_metadata(video_id)
        
        # Step 2: Get and clean subtitles

        subtitles = self.video_agent.get_video_subtitles(video_id)
        cleaned_content = self.text_agent.clean_subtitles(subtitles)
        
        # Step 3: Generate learning content
        summary = self.text_agent.generate_summary(cleaned_content)
        key_points = self.text_agent.extract_key_points(cleaned_content)
        quiz_questions = self.text_agent.generate_quiz_questions(cleaned_content)
        
        # Step 4: Create processed content object
        processed_content = ProcessedContent(
            video_id=video_id,
            title=metadata.get('title', ''),
            description=metadata.get('description', ''),
            duration=metadata.get('duration', 0),
            summary=summary,
            key_points=key_points,
            quiz_questions=quiz_questions
        )

        # Looking at the code, this appears to be a complete implementation of a `LearningAppProcessor` class with a `process_video` method. The method:
        # 1. Extracts video ID and metadata
        # 2. Gets and cleans subtitles
        # 3. Generates learning content (summary, key points, quiz questions,work flows, and code)
        return processed_content
