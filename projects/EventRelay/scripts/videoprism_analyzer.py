#!/usr/bin/env python3
"""
VideoPrism-Style Video Content Analyzer
Advanced video analysis, categorization, and visual understanding
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import re
import hashlib
from urllib.parse import urlparse

# Import our enhanced video extractor
from video_extractor_enhanced import (
    EnhancedVideoExtractor, VideoContent, TranscriptSegment, VideoMetadata
)

# Computer vision and ML imports
try:
    import cv2
    import numpy as np
    from PIL import Image
    import torch
    import torchvision.transforms as transforms
    from transformers import (
        pipeline, AutoProcessor, AutoModel, 
        BlipProcessor, BlipForConditionalGeneration,
        CLIPProcessor, CLIPModel
    )
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_CV_DEPS = True
except ImportError:
    HAS_CV_DEPS = False
    logging.warning("Computer vision dependencies not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [VideoPrism] %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class VisualAnalysis:
    """Visual analysis results for video frames"""
    frame_timestamp: float
    scene_description: str
    objects_detected: List[str]
    activities: List[str]
    emotions: List[str]
    visual_quality: Dict[str, float]  # brightness, contrast, sharpness
    dominant_colors: List[str]
    scene_type: str  # indoor, outdoor, studio, etc.

@dataclass
class ContentCategory:
    """Content categorization with confidence scores"""
    primary_category: str
    subcategories: List[str]
    confidence_scores: Dict[str, float]
    reasoning: str
    content_tags: List[str]

@dataclass
class VideoComplexity:
    """Analysis of video complexity and production quality"""
    visual_complexity: float  # 0-1 scale
    audio_complexity: float
    content_complexity: float
    production_quality: float
    technical_quality: Dict[str, float]
    complexity_factors: List[str]

@dataclass
class AudienceAnalysis:
    """Target audience and engagement analysis"""
    target_age_group: str
    education_level: str
    expertise_level: str
    engagement_factors: List[str]
    accessibility_score: float
    content_appropriateness: Dict[str, str]

@dataclass
class VideoPrismAnalysis:
    """Complete VideoPrism-style analysis results"""
    video_metadata: VideoMetadata
    visual_analysis: List[VisualAnalysis]
    content_category: ContentCategory
    video_complexity: VideoComplexity
    audience_analysis: AudienceAnalysis
    key_moments: List[Dict[str, Any]]
    content_themes: List[str]
    similar_content_suggestions: List[str]
    analysis_metadata: Dict[str, Any]

class VideoPrismAnalyzer:
    """
    VideoPrism-style video content analyzer with advanced AI capabilities
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.sample_rate = self.config.get('frame_sample_rate', 30)  # Sample every N seconds
        self.max_frames = self.config.get('max_frames', 20)
        
        # Initialize video extractor
        self.video_extractor = EnhancedVideoExtractor(config)
        
        # Initialize computer vision components
        if HAS_CV_DEPS:
            self._initialize_cv_components()
        else:
            logger.error("Computer vision dependencies required for VideoPrism analyzer")
            self.cv_available = False
    
    def _initialize_cv_components(self):
        """Initialize computer vision models and pipelines"""
        try:
            # Image captioning model
            self.caption_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            
            # CLIP model for image-text understanding
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            
            # Object detection pipeline
            self.object_detector = pipeline(
                "object-detection",
                model="facebook/detr-resnet-50",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Emotion analysis pipeline
            self.emotion_analyzer = pipeline(
                "image-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                use_safetensors=True,
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Text classification for content categorization
            self.content_classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                use_safetensors=True,
                device=0 if torch.cuda.is_available() else -1
            )
            
            self.cv_available = True
            logger.info("Computer vision components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize CV components: {e}")
            self.cv_available = False
    
    async def analyze_video(self, video_url: str, languages: List[str] = None) -> VideoPrismAnalysis:
        """Perform comprehensive VideoPrism-style analysis"""
        if not self.cv_available:
            raise ValueError("Computer vision components not available")
        
        logger.info(f"Starting VideoPrism analysis for: {video_url}")
        start_time = datetime.now()
        
        # Extract video content
        video_content = await self.video_extractor.process_video(video_url, languages)
        
        # Download and analyze video frames
        video_path = await self._download_video(video_url)
        visual_analysis = await self._analyze_visual_content(video_path, video_content)
        
        # Perform content analysis
        content_category = await self._categorize_content(video_content)
        video_complexity = await self._analyze_complexity(video_content, visual_analysis)
        audience_analysis = await self._analyze_target_audience(video_content)
        key_moments = await self._identify_key_moments(video_content, visual_analysis)
        content_themes = await self._extract_content_themes(video_content)
        similar_suggestions = await self._generate_similar_content_suggestions(video_content)
        
        # Create comprehensive analysis
        analysis = VideoPrismAnalysis(
            video_metadata=video_content.metadata,
            visual_analysis=visual_analysis,
            content_category=content_category,
            video_complexity=video_complexity,
            audience_analysis=audience_analysis,
            key_moments=key_moments,
            content_themes=content_themes,
            similar_content_suggestions=similar_suggestions,
            analysis_metadata={
                'analyzed_at': start_time.isoformat(),
                'analysis_duration': (datetime.now() - start_time).total_seconds(),
                'frames_analyzed': len(visual_analysis),
                'models_used': ['BLIP', 'CLIP', 'DETR', 'BART'],
                'version': '1.0'
            }
        )
        
        # Cleanup
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
        
        logger.info(f"VideoPrism analysis completed in {analysis.analysis_metadata['analysis_duration']:.2f}s")
        return analysis
    
    async def _download_video(self, video_url: str) -> str:
        """Download video for frame analysis"""
        try:
            import yt_dlp
            
            # Create temporary directory
            temp_dir = Path("/tmp/videoprism_analysis")
            temp_dir.mkdir(exist_ok=True)
            
            # Generate unique filename
            url_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
            output_path = temp_dir / f"video_{url_hash}.%(ext)s"
            
            ydl_opts = {
                'format': 'best[height<=720]',  # Limit quality for faster processing
                'outtmpl': str(output_path),
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Find the downloaded file
            for file_path in temp_dir.glob(f"video_{url_hash}.*"):
                if file_path.suffix in ['.mp4', '.webm', '.mkv']:
                    return str(file_path)
            
            raise FileNotFoundError("Downloaded video file not found")
            
        except Exception as e:
            logger.warning(f"Video download failed: {e}")
            return None
    
    async def _analyze_visual_content(self, video_path: str, video_content: VideoContent) -> List[VisualAnalysis]:
        """Analyze visual content of video frames"""
        if not video_path:
            return []
        
        visual_analyses = []
        
        try:
            # Open video with OpenCV
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            # Calculate frame sampling
            if duration > 0:
                sample_interval = max(1, int(fps * self.sample_rate))
                frame_indices = range(0, total_frames, sample_interval)
                frame_indices = list(frame_indices)[:self.max_frames]
            else:
                frame_indices = []
            
            logger.info(f"Analyzing {len(frame_indices)} frames from video")
            
            for i, frame_idx in enumerate(frame_indices):
                try:
                    # Seek to frame
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    
                    if not ret:
                        continue
                    
                    # Convert frame to PIL Image
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = Image.fromarray(frame_rgb)
                    
                    # Calculate timestamp
                    timestamp = frame_idx / fps if fps > 0 else 0
                    
                    # Analyze frame
                    analysis = await self._analyze_single_frame(image, timestamp)
                    visual_analyses.append(analysis)
                    
                    if i % 5 == 0:
                        logger.info(f"Processed {i+1}/{len(frame_indices)} frames")
                
                except Exception as e:
                    logger.warning(f"Failed to analyze frame {frame_idx}: {e}")
                    continue
            
            cap.release()
            
        except Exception as e:
            logger.error(f"Visual content analysis failed: {e}")
        
        return visual_analyses
    
    async def _analyze_single_frame(self, image: Image.Image, timestamp: float) -> VisualAnalysis:
        """Analyze a single video frame"""
        try:
            # Generate scene description
            scene_description = self._generate_scene_description(image)
            
            # Detect objects
            objects_detected = self._detect_objects(image)
            
            # Analyze activities (using CLIP with activity labels)
            activities = self._analyze_activities(image)
            
            # Analyze emotions (if faces are present)
            emotions = self._analyze_emotions(image)
            
            # Calculate visual quality metrics
            visual_quality = self._calculate_visual_quality(image)
            
            # Extract dominant colors
            dominant_colors = self._extract_dominant_colors(image)
            
            # Classify scene type
            scene_type = self._classify_scene_type(image)
            
            return VisualAnalysis(
                frame_timestamp=timestamp,
                scene_description=scene_description,
                objects_detected=objects_detected,
                activities=activities,
                emotions=emotions,
                visual_quality=visual_quality,
                dominant_colors=dominant_colors,
                scene_type=scene_type
            )
        
        except Exception as e:
            logger.warning(f"Frame analysis failed: {e}")
            return VisualAnalysis(
                frame_timestamp=timestamp,
                scene_description="Analysis failed",
                objects_detected=[],
                activities=[],
                emotions=[],
                visual_quality={},
                dominant_colors=[],
                scene_type="unknown"
            )
    
    def _generate_scene_description(self, image: Image.Image) -> str:
        """Generate description of the scene using BLIP"""
        try:
            inputs = self.caption_processor(image, return_tensors="pt")
            out = self.caption_model.generate(**inputs, max_length=50)
            description = self.caption_processor.decode(out[0], skip_special_tokens=True)
            return description
        except Exception as e:
            logger.warning(f"Scene description failed: {e}")
            return "Scene description unavailable"
    
    def _detect_objects(self, image: Image.Image) -> List[str]:
        """Detect objects in the image"""
        try:
            results = self.object_detector(image)
            objects = []
            
            for result in results:
                if result['score'] > 0.5:  # Confidence threshold
                    objects.append(result['label'])
            
            return list(set(objects))  # Remove duplicates
        except Exception as e:
            logger.warning(f"Object detection failed: {e}")
            return []
    
    def _analyze_activities(self, image: Image.Image) -> List[str]:
        """Analyze activities using CLIP"""
        try:
            activity_labels = [
                "talking", "presenting", "demonstrating", "writing", "reading",
                "cooking", "exercising", "playing music", "dancing", "working",
                "teaching", "learning", "meeting", "interviewing"
            ]
            
            inputs = self.clip_processor(
                text=activity_labels, 
                images=image, 
                return_tensors="pt", 
                padding=True
            )
            
            outputs = self.clip_model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            
            activities = []
            for i, prob in enumerate(probs[0]):
                if prob > 0.1:  # Threshold for activity detection
                    activities.append(activity_labels[i])
            
            return activities
        except Exception as e:
            logger.warning(f"Activity analysis failed: {e}")
            return []
    
    def _analyze_emotions(self, image: Image.Image) -> List[str]:
        """Analyze emotions in the image"""
        try:
            # Convert PIL to numpy for face detection
            img_array = np.array(image)
            
            # Simple face detection using OpenCV
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) > 0:
                # For now, return generic emotion analysis
                # In a full implementation, you'd crop faces and analyze emotions
                return ["neutral", "engaged"]
            else:
                return []
        except Exception as e:
            logger.warning(f"Emotion analysis failed: {e}")
            return []
    
    def _calculate_visual_quality(self, image: Image.Image) -> Dict[str, float]:
        """Calculate visual quality metrics"""
        try:
            img_array = np.array(image)
            
            # Calculate brightness
            brightness = np.mean(img_array) / 255.0
            
            # Calculate contrast (standard deviation)
            contrast = np.std(img_array) / 255.0
            
            # Calculate sharpness (Laplacian variance)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var() / 10000.0  # Normalized
            
            return {
                'brightness': float(brightness),
                'contrast': float(contrast),
                'sharpness': min(float(sharpness), 1.0)  # Cap at 1.0
            }
        except Exception as e:
            logger.warning(f"Visual quality calculation failed: {e}")
            return {'brightness': 0.5, 'contrast': 0.5, 'sharpness': 0.5}
    
    def _extract_dominant_colors(self, image: Image.Image, n_colors: int = 3) -> List[str]:
        """Extract dominant colors from image"""
        try:
            # Resize image for faster processing
            image_small = image.resize((150, 150))
            img_array = np.array(image_small)
            
            # Reshape to pixel array
            pixels = img_array.reshape(-1, 3)
            
            # Use KMeans to find dominant colors
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            colors = []
            for color in kmeans.cluster_centers_:
                # Convert to hex
                hex_color = '#{:02x}{:02x}{:02x}'.format(
                    int(color[0]), int(color[1]), int(color[2])
                )
                colors.append(hex_color)
            
            return colors
        except Exception as e:
            logger.warning(f"Color extraction failed: {e}")
            return ['#808080', '#404040', '#C0C0C0']  # Default grays
    
    def _classify_scene_type(self, image: Image.Image) -> str:
        """Classify the type of scene"""
        try:
            scene_types = [
                "indoor office", "outdoor nature", "studio setup", "home interior",
                "classroom", "kitchen", "laboratory", "stage", "street", "vehicle"
            ]
            
            inputs = self.clip_processor(
                text=scene_types, 
                images=image, 
                return_tensors="pt", 
                padding=True
            )
            
            outputs = self.clip_model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            
            # Get the most likely scene type
            max_idx = torch.argmax(probs[0])
            return scene_types[max_idx]
        except Exception as e:
            logger.warning(f"Scene classification failed: {e}")
            return "unknown"
    
    async def _categorize_content(self, video_content: VideoContent) -> ContentCategory:
        """Categorize video content using AI classification"""
        try:
            # Combine title, description, and transcript for analysis
            content_text = f"{video_content.metadata.title} {video_content.metadata.description}"
            if video_content.transcript:
                transcript_text = " ".join([seg.text for seg in video_content.transcript[:10]])  # First 10 segments
                content_text += f" {transcript_text}"
            
            # Define content categories
            categories = [
                "Educational/Tutorial", "Entertainment", "News/Documentary", 
                "Technology/Science", "Business/Finance", "Health/Fitness",
                "Arts/Culture", "Gaming", "Music", "Sports", "Travel",
                "Cooking/Food", "DIY/Crafts", "Fashion/Beauty", "Automotive"
            ]
            
            # Classify content
            result = self.content_classifier(content_text[:1000], categories)
            
            primary_category = result['labels'][0]
            confidence_scores = {
                label: score for label, score in zip(result['labels'], result['scores'])
            }
            
            # Extract subcategories based on content
            subcategories = self._extract_subcategories(content_text, primary_category)
            
            # Generate reasoning
            reasoning = f"Classified as {primary_category} based on content analysis of title, description, and transcript."
            
            # Extract content tags
            content_tags = self._extract_content_tags(content_text)
            
            return ContentCategory(
                primary_category=primary_category,
                subcategories=subcategories,
                confidence_scores=confidence_scores,
                reasoning=reasoning,
                content_tags=content_tags
            )
        
        except Exception as e:
            logger.error(f"Content categorization failed: {e}")
            return ContentCategory(
                primary_category="Unknown",
                subcategories=[],
                confidence_scores={},
                reasoning="Categorization failed",
                content_tags=[]
            )
    
    def _extract_subcategories(self, content_text: str, primary_category: str) -> List[str]:
        """Extract subcategories based on content and primary category"""
        subcategory_map = {
            "Educational/Tutorial": ["beginner", "advanced", "step-by-step", "theory", "practical"],
            "Technology/Science": ["programming", "AI/ML", "hardware", "research", "innovation"],
            "Entertainment": ["comedy", "drama", "action", "documentary", "variety"],
            "Business/Finance": ["investing", "entrepreneurship", "marketing", "economics", "career"],
            "Health/Fitness": ["exercise", "nutrition", "mental health", "wellness", "medical"]
        }
        
        potential_subcategories = subcategory_map.get(primary_category, [])
        found_subcategories = []
        
        content_lower = content_text.lower()
        for subcat in potential_subcategories:
            if subcat in content_lower or any(word in content_lower for word in subcat.split()):
                found_subcategories.append(subcat)
        
        return found_subcategories[:3]  # Limit to 3 subcategories
    
    def _extract_content_tags(self, content_text: str) -> List[str]:
        """Extract relevant content tags"""
        # Use TF-IDF to find important terms
        try:
            vectorizer = TfidfVectorizer(
                max_features=20,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1
            )
            
            tfidf_matrix = vectorizer.fit_transform([content_text])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            
            # Get top scoring terms
            top_indices = np.argsort(scores)[-10:][::-1]
            tags = [feature_names[i] for i in top_indices if scores[i] > 0]
            
            return tags[:8]  # Limit to 8 tags
        except Exception as e:
            logger.warning(f"Tag extraction failed: {e}")
            return []
    
    async def _analyze_complexity(self, video_content: VideoContent, visual_analysis: List[VisualAnalysis]) -> VideoComplexity:
        """Analyze video complexity across multiple dimensions"""
        try:
            # Visual complexity based on scene changes, object diversity
            visual_complexity = self._calculate_visual_complexity(visual_analysis)
            
            # Audio complexity based on transcript analysis
            audio_complexity = self._calculate_audio_complexity(video_content)
            
            # Content complexity based on vocabulary and concepts
            content_complexity = self._calculate_content_complexity(video_content)
            
            # Production quality based on technical metrics
            production_quality = self._calculate_production_quality(video_content, visual_analysis)
            
            # Technical quality metrics
            technical_quality = self._calculate_technical_quality(visual_analysis)
            
            # Identify complexity factors
            complexity_factors = self._identify_complexity_factors(
                visual_complexity, audio_complexity, content_complexity
            )
            
            return VideoComplexity(
                visual_complexity=visual_complexity,
                audio_complexity=audio_complexity,
                content_complexity=content_complexity,
                production_quality=production_quality,
                technical_quality=technical_quality,
                complexity_factors=complexity_factors
            )
        
        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            return VideoComplexity(
                visual_complexity=0.5,
                audio_complexity=0.5,
                content_complexity=0.5,
                production_quality=0.5,
                technical_quality={},
                complexity_factors=[]
            )
    
    def _calculate_visual_complexity(self, visual_analysis: List[VisualAnalysis]) -> float:
        """Calculate visual complexity score"""
        if not visual_analysis:
            return 0.5
        
        try:
            # Count unique objects across frames
            all_objects = []
            for analysis in visual_analysis:
                all_objects.extend(analysis.objects_detected)
            unique_objects = len(set(all_objects))
            
            # Count unique scene types
            scene_types = [analysis.scene_type for analysis in visual_analysis]
            unique_scenes = len(set(scene_types))
            
            # Average activities per frame
            total_activities = sum(len(analysis.activities) for analysis in visual_analysis)
            avg_activities = total_activities / len(visual_analysis) if visual_analysis else 0
            
            # Normalize and combine metrics
            object_score = min(unique_objects / 20.0, 1.0)  # Normalize to 0-1
            scene_score = min(unique_scenes / 5.0, 1.0)
            activity_score = min(avg_activities / 3.0, 1.0)
            
            return (object_score + scene_score + activity_score) / 3.0
        
        except Exception as e:
            logger.warning(f"Visual complexity calculation failed: {e}")
            return 0.5
    
    def _calculate_audio_complexity(self, video_content: VideoContent) -> float:
        """Calculate audio complexity based on transcript"""
        if not video_content.transcript:
            return 0.3
        
        try:
            # Calculate speaking rate
            total_words = sum(len(seg.text.split()) for seg in video_content.transcript)
            total_duration = video_content.transcript[-1].end - video_content.transcript[0].start
            speaking_rate = total_words / (total_duration / 60) if total_duration > 0 else 0  # words per minute
            
            # Vocabulary diversity
            all_words = []
            for seg in video_content.transcript:
                all_words.extend(seg.text.lower().split())
            unique_words = len(set(all_words))
            vocab_diversity = unique_words / len(all_words) if all_words else 0
            
            # Normalize metrics
            rate_score = min(speaking_rate / 200.0, 1.0)  # Normalize to typical speaking rate
            vocab_score = min(vocab_diversity * 2.0, 1.0)
            
            return (rate_score + vocab_score) / 2.0
        
        except Exception as e:
            logger.warning(f"Audio complexity calculation failed: {e}")
            return 0.3
    
    def _calculate_content_complexity(self, video_content: VideoContent) -> float:
        """Calculate content complexity based on vocabulary and concepts"""
        if not video_content.transcript:
            return 0.4
        
        try:
            full_text = " ".join([seg.text for seg in video_content.transcript])
            
            # Average word length
            words = full_text.split()
            avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
            
            # Sentence complexity (average sentence length)
            sentences = re.split(r'[.!?]+', full_text)
            avg_sentence_length = sum(len(sent.split()) for sent in sentences) / len(sentences) if sentences else 0
            
            # Technical term detection (simple heuristic)
            technical_indicators = ['algorithm', 'system', 'process', 'method', 'analysis', 'data', 'model']
            technical_count = sum(1 for word in words if word.lower() in technical_indicators)
            technical_density = technical_count / len(words) if words else 0
            
            # Normalize metrics
            word_score = min(avg_word_length / 8.0, 1.0)  # Normalize to typical word length
            sentence_score = min(avg_sentence_length / 20.0, 1.0)
            technical_score = min(technical_density * 10.0, 1.0)
            
            return (word_score + sentence_score + technical_score) / 3.0
        
        except Exception as e:
            logger.warning(f"Content complexity calculation failed: {e}")
            return 0.4
    
    def _calculate_production_quality(self, video_content: VideoContent, visual_analysis: List[VisualAnalysis]) -> float:
        """Calculate production quality score"""
        try:
            if not visual_analysis:
                return 0.5
            
            # Average visual quality metrics
            avg_brightness = np.mean([va.visual_quality.get('brightness', 0.5) for va in visual_analysis])
            avg_contrast = np.mean([va.visual_quality.get('contrast', 0.5) for va in visual_analysis])
            avg_sharpness = np.mean([va.visual_quality.get('sharpness', 0.5) for va in visual_analysis])
            
            # Scene consistency (fewer scene changes might indicate better planning)
            scene_changes = len(set(va.scene_type for va in visual_analysis))
            scene_consistency = max(0, 1.0 - (scene_changes / len(visual_analysis)))
            
            # Combine metrics
            visual_quality = (avg_brightness + avg_contrast + avg_sharpness) / 3.0
            
            return (visual_quality + scene_consistency) / 2.0
        
        except Exception as e:
            logger.warning(f"Production quality calculation failed: {e}")
            return 0.5
    
    def _calculate_technical_quality(self, visual_analysis: List[VisualAnalysis]) -> Dict[str, float]:
        """Calculate technical quality metrics"""
        if not visual_analysis:
            return {}
        
        try:
            # Calculate averages across all frames
            avg_brightness = np.mean([va.visual_quality.get('brightness', 0.5) for va in visual_analysis])
            avg_contrast = np.mean([va.visual_quality.get('contrast', 0.5) for va in visual_analysis])
            avg_sharpness = np.mean([va.visual_quality.get('sharpness', 0.5) for va in visual_analysis])
            
            # Calculate stability (variance in quality metrics)
            brightness_stability = 1.0 - np.std([va.visual_quality.get('brightness', 0.5) for va in visual_analysis])
            contrast_stability = 1.0 - np.std([va.visual_quality.get('contrast', 0.5) for va in visual_analysis])
            
            return {
                'average_brightness': float(avg_brightness),
                'average_contrast': float(avg_contrast),
                'average_sharpness': float(avg_sharpness),
                'brightness_stability': max(0.0, float(brightness_stability)),
                'contrast_stability': max(0.0, float(contrast_stability))
            }
        
        except Exception as e:
            logger.warning(f"Technical quality calculation failed: {e}")
            return {}
    
    def _identify_complexity_factors(self, visual_complexity: float, audio_complexity: float, content_complexity: float) -> List[str]:
        """Identify factors contributing to complexity"""
        factors = []
        
        if visual_complexity > 0.7:
            factors.append("High visual complexity with diverse scenes and objects")
        if audio_complexity > 0.7:
            factors.append("Fast-paced dialogue with rich vocabulary")
        if content_complexity > 0.7:
            factors.append("Complex technical or conceptual content")
        
        if visual_complexity < 0.3:
            factors.append("Simple visual presentation")
        if audio_complexity < 0.3:
            factors.append("Slow-paced or minimal dialogue")
        if content_complexity < 0.3:
            factors.append("Basic or introductory content")
        
        return factors
    
    async def _analyze_target_audience(self, video_content: VideoContent) -> AudienceAnalysis:
        """Analyze target audience characteristics"""
        try:
            # Analyze content for audience indicators
            full_text = f"{video_content.metadata.title} {video_content.metadata.description}"
            if video_content.transcript:
                transcript_text = " ".join([seg.text for seg in video_content.transcript[:5]])
                full_text += f" {transcript_text}"
            
            # Determine age group based on content
            target_age_group = self._determine_age_group(full_text)
            
            # Determine education level
            education_level = self._determine_education_level(full_text)
            
            # Determine expertise level
            expertise_level = self._determine_expertise_level(full_text)
            
            # Identify engagement factors
            engagement_factors = self._identify_engagement_factors(full_text)
            
            # Calculate accessibility score
            accessibility_score = self._calculate_accessibility_score(video_content)
            
            # Assess content appropriateness
            content_appropriateness = self._assess_content_appropriateness(full_text)
            
            return AudienceAnalysis(
                target_age_group=target_age_group,
                education_level=education_level,
                expertise_level=expertise_level,
                engagement_factors=engagement_factors,
                accessibility_score=accessibility_score,
                content_appropriateness=content_appropriateness
            )
        
        except Exception as e:
            logger.error(f"Audience analysis failed: {e}")
            return AudienceAnalysis(
                target_age_group="General",
                education_level="Any",
                expertise_level="Beginner",
                engagement_factors=[],
                accessibility_score=0.5,
                content_appropriateness={}
            )
    
    def _determine_age_group(self, content: str) -> str:
        """Determine target age group from content"""
        content_lower = content.lower()
        
        # Age indicators
        if any(word in content_lower for word in ['kids', 'children', 'elementary', 'cartoon']):
            return "Children (5-12)"
        elif any(word in content_lower for word in ['teen', 'high school', 'college prep']):
            return "Teenagers (13-18)"
        elif any(word in content_lower for word in ['university', 'college', 'academic']):
            return "Young Adults (18-25)"
        elif any(word in content_lower for word in ['professional', 'career', 'business', 'advanced']):
            return "Adults (25-45)"
        elif any(word in content_lower for word in ['retirement', 'senior', 'mature']):
            return "Seniors (45+)"
        else:
            return "General Audience"
    
    def _determine_education_level(self, content: str) -> str:
        """Determine required education level"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['phd', 'research', 'academic', 'theoretical']):
            return "Graduate"
        elif any(word in content_lower for word in ['university', 'college', 'degree', 'advanced']):
            return "Undergraduate"
        elif any(word in content_lower for word in ['high school', 'basic', 'introduction']):
            return "High School"
        else:
            return "Any Level"
    
    def _determine_expertise_level(self, content: str) -> str:
        """Determine required expertise level"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['expert', 'advanced', 'professional', 'master']):
            return "Expert"
        elif any(word in content_lower for word in ['intermediate', 'some experience']):
            return "Intermediate"
        elif any(word in content_lower for word in ['beginner', 'introduction', 'basics', 'getting started']):
            return "Beginner"
        else:
            return "General"
    
    def _identify_engagement_factors(self, content: str) -> List[str]:
        """Identify factors that drive engagement"""
        factors = []
        content_lower = content.lower()
        
        engagement_indicators = {
            'interactive': ['interactive', 'hands-on', 'practice', 'exercise'],
            'visual': ['visual', 'demonstration', 'show', 'example'],
            'storytelling': ['story', 'narrative', 'case study', 'example'],
            'humor': ['funny', 'humor', 'comedy', 'entertaining'],
            'practical': ['practical', 'real-world', 'applicable', 'useful'],
            'current': ['latest', 'new', 'current', 'trending', 'recent']
        }
        
        for factor, keywords in engagement_indicators.items():
            if any(keyword in content_lower for keyword in keywords):
                factors.append(factor)
        
        return factors
    
    def _calculate_accessibility_score(self, video_content: VideoContent) -> float:
        """Calculate accessibility score"""
        score = 0.0
        
        # Has transcript
        if video_content.transcript:
            score += 0.4
        
        # Clear audio (based on transcript quality)
        if video_content.transcript and len(video_content.transcript) > 0:
            avg_segment_length = np.mean([len(seg.text) for seg in video_content.transcript])
            if avg_segment_length > 20:  # Reasonable segment length
                score += 0.3
        
        # Title and description available
        if video_content.metadata.title:
            score += 0.2
        if video_content.metadata.description:
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_content_appropriateness(self, content: str) -> Dict[str, str]:
        """Assess content appropriateness for different audiences"""
        content_lower = content.lower()
        
        # Simple content filtering
        inappropriate_indicators = ['explicit', 'violence', 'adult', 'mature']
        educational_indicators = ['learn', 'education', 'tutorial', 'guide']
        professional_indicators = ['business', 'professional', 'work', 'career']
        
        appropriateness = {}
        
        if any(word in content_lower for word in inappropriate_indicators):
            appropriateness['general'] = "Not suitable - mature content"
        elif any(word in content_lower for word in educational_indicators):
            appropriateness['general'] = "Suitable - educational content"
        elif any(word in content_lower for word in professional_indicators):
            appropriateness['general'] = "Suitable - professional content"
        else:
            appropriateness['general'] = "Suitable - general content"
        
        return appropriateness
    
    async def _identify_key_moments(self, video_content: VideoContent, visual_analysis: List[VisualAnalysis]) -> List[Dict[str, Any]]:
        """Identify key moments in the video"""
        key_moments = []
        
        try:
            # Identify moments with high activity
            for analysis in visual_analysis:
                if len(analysis.activities) > 2:  # High activity threshold
                    key_moments.append({
                        'timestamp': analysis.frame_timestamp,
                        'type': 'high_activity',
                        'description': f"High activity scene: {', '.join(analysis.activities)}",
                        'importance': 0.8
                    })
            
            # Identify scene changes
            if len(visual_analysis) > 1:
                for i in range(1, len(visual_analysis)):
                    if visual_analysis[i].scene_type != visual_analysis[i-1].scene_type:
                        key_moments.append({
                            'timestamp': visual_analysis[i].frame_timestamp,
                            'type': 'scene_change',
                            'description': f"Scene change to {visual_analysis[i].scene_type}",
                            'importance': 0.6
                        })
            
            # Identify transcript-based key moments
            if video_content.transcript:
                for segment in video_content.transcript:
                    # Look for emphasis words
                    if any(word in segment.text.lower() for word in ['important', 'key', 'remember', 'crucial']):
                        key_moments.append({
                            'timestamp': segment.start,
                            'type': 'emphasis',
                            'description': segment.text[:100] + "..." if len(segment.text) > 100 else segment.text,
                            'importance': 0.7
                        })
            
            # Sort by timestamp and limit
            key_moments.sort(key=lambda x: x['timestamp'])
            return key_moments[:10]  # Limit to top 10 moments
        
        except Exception as e:
            logger.warning(f"Key moments identification failed: {e}")
            return []
    
    async def _extract_content_themes(self, video_content: VideoContent) -> List[str]:
        """Extract main themes from video content"""
        try:
            if not video_content.transcript:
                return []
            
            # Combine transcript text
            full_text = " ".join([seg.text for seg in video_content.transcript])
            
            # Use TF-IDF to extract themes
            vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words='english',
                ngram_range=(1, 3),
                min_df=2
            )
            
            tfidf_matrix = vectorizer.fit_transform([full_text])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            
            # Get top themes
            top_indices = np.argsort(scores)[-10:][::-1]
            themes = [feature_names[i] for i in top_indices if scores[i] > 0]
            
            return themes[:8]  # Limit to 8 themes
        
        except Exception as e:
            logger.warning(f"Theme extraction failed: {e}")
            return []
    
    async def _generate_similar_content_suggestions(self, video_content: VideoContent) -> List[str]:
        """Generate suggestions for similar content"""
        try:
            suggestions = []
            
            # Based on title and description
            title_words = video_content.metadata.title.lower().split()
            
            # Generate topic-based suggestions
            if 'tutorial' in title_words or 'how to' in video_content.metadata.title.lower():
                suggestions.append("More beginner tutorials in this topic")
                suggestions.append("Advanced techniques and tips")
            
            if 'review' in title_words:
                suggestions.append("Comparison videos")
                suggestions.append("Alternative product reviews")
            
            # Based on content themes
            if video_content.topics:
                for topic in video_content.topics[:3]:
                    suggestions.append(f"Deep dive into {topic}")
                    suggestions.append(f"Latest trends in {topic}")
            
            # Generic suggestions based on category
            suggestions.extend([
                "Related case studies",
                "Expert interviews on this topic",
                "Community discussions and Q&A"
            ])
            
            return suggestions[:6]  # Limit to 6 suggestions
        
        except Exception as e:
            logger.warning(f"Similar content suggestions failed: {e}")
            return []
    
    def export_analysis(self, analysis: VideoPrismAnalysis, format: str = "json", output_path: str = None) -> str:
        """Export analysis results in various formats"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"videoprism_analysis_{analysis.video_metadata.video_id}_{timestamp}"
        
        if format.lower() == "json":
            output_file = f"{output_path}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(analysis), f, indent=2, ensure_ascii=False, default=str)
        
        elif format.lower() == "markdown":
            output_file = f"{output_path}.md"
            markdown_content = self._generate_analysis_markdown(analysis)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Analysis exported to {output_file}")
        return output_file
    
    def _generate_analysis_markdown(self, analysis: VideoPrismAnalysis) -> str:
        """Generate markdown representation of analysis"""
        md = f"""# 🎬 VideoPrism Analysis: {analysis.video_metadata.title}

## 📊 Content Category
**Primary Category**: {analysis.content_category.primary_category}
**Subcategories**: {', '.join(analysis.content_category.subcategories)}
**Confidence**: {analysis.content_category.confidence_scores.get(analysis.content_category.primary_category, 0):.2f}

{analysis.content_category.reasoning}

## 🎯 Target Audience
- **Age Group**: {analysis.audience_analysis.target_age_group}
- **Education Level**: {analysis.audience_analysis.education_level}
- **Expertise Level**: {analysis.audience_analysis.expertise_level}
- **Accessibility Score**: {analysis.audience_analysis.accessibility_score:.2f}/1.0

### Engagement Factors
{chr(10).join([f"- {factor}" for factor in analysis.audience_analysis.engagement_factors])}

## 📈 Complexity Analysis
- **Visual Complexity**: {analysis.video_complexity.visual_complexity:.2f}/1.0
- **Audio Complexity**: {analysis.video_complexity.audio_complexity:.2f}/1.0
- **Content Complexity**: {analysis.video_complexity.content_complexity:.2f}/1.0
- **Production Quality**: {analysis.video_complexity.production_quality:.2f}/1.0

### Complexity Factors
{chr(10).join([f"- {factor}" for factor in analysis.video_complexity.complexity_factors])}

## 🎨 Visual Analysis Summary
Analyzed {len(analysis.visual_analysis)} frames across the video.

### Scene Types Detected
{chr(10).join([f"- {scene}" for scene in set([va.scene_type for va in analysis.visual_analysis])])}

### Common Objects
{chr(10).join([f"- {obj}" for obj in set([obj for va in analysis.visual_analysis for obj in va.objects_detected])])}

## ⭐ Key Moments
"""
        
        for moment in analysis.key_moments:
            timestamp_str = f"{int(moment['timestamp']//60)}:{int(moment['timestamp']%60):02d}"
            md += f"- **[{timestamp_str}]** {moment['description']} (Importance: {moment['importance']:.1f})\n"
        
        md += f"""
## 🏷️ Content Themes
{chr(10).join([f"- {theme}" for theme in analysis.content_themes])}

## 💡 Similar Content Suggestions
{chr(10).join([f"- {suggestion}" for suggestion in analysis.similar_content_suggestions])}

---
*Analysis completed on {analysis.analysis_metadata['analyzed_at']}*
*Processing time: {analysis.analysis_metadata['analysis_duration']:.2f}s*
*Frames analyzed: {analysis.analysis_metadata['frames_analyzed']}*
"""
        
        return md

# Example usage
async def main():
    """Example usage of VideoPrism analyzer"""
    analyzer = VideoPrismAnalyzer()
    
    # Test video URL
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    
    try:
        # Perform analysis
        analysis = await analyzer.analyze_video(test_url)
        
        # Export results
        analyzer.export_analysis(analysis, "json")
        analyzer.export_analysis(analysis, "markdown")
        
        print(f"Analysis completed for: {analysis.video_metadata.title}")
        print(f"Category: {analysis.content_category.primary_category}")
        print(f"Target Audience: {analysis.audience_analysis.target_age_group}")
        print(f"Complexity: Visual={analysis.video_complexity.visual_complexity:.2f}, Content={analysis.video_complexity.content_complexity:.2f}")
        
    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())