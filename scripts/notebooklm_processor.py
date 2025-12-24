#!/usr/bin/env python3
"""
NotebookLM-Style Video Processor
AI-powered note generation and content analysis for video content
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import re

# Import our enhanced video extractor
from video_extractor_enhanced import (
    EnhancedVideoExtractor, VideoContent, TranscriptSegment, VideoMetadata
)

# AI processing imports
try:
    import openai
    from transformers import pipeline, AutoTokenizer, AutoModel
    import torch
    import numpy as np
    from sentence_transformers import SentenceTransformer
    HAS_AI_DEPS = True
except ImportError:
    HAS_AI_DEPS = False
    logging.warning("AI dependencies not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [NotebookLM] %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NotebookEntry:
    """Individual notebook entry with AI-generated insights"""
    timestamp: str
    content: str
    entry_type: str  # summary, key_point, question, insight, connection
    confidence: float
    related_segments: List[int]  # Indices of related transcript segments
    tags: List[str] = None

@dataclass
class VideoNotebook:
    """Complete notebook for a video with AI-generated content"""
    video_metadata: VideoMetadata
    executive_summary: str
    key_insights: List[str]
    main_topics: List[str]
    questions_raised: List[str]
    action_items: List[str]
    notebook_entries: List[NotebookEntry]
    concept_map: Dict[str, List[str]]  # Topic -> related concepts
    processing_metadata: Dict[str, Any]

class NotebookLMProcessor:
    """
    NotebookLM-style processor for video content analysis and note generation
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.openai_api_key = self.config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        
        # Initialize video extractor
        self.video_extractor = EnhancedVideoExtractor(config)
        
        # Initialize AI components
        if HAS_AI_DEPS:
            self._initialize_ai_components()
        else:
            logger.error("AI dependencies required for NotebookLM processor")
            self.ai_available = False
    
    def _initialize_ai_components(self):
        """Initialize AI models and pipelines"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Device set to use {self.device}")
        self.key_insight_model = "valhalla/t5-small-qg-hl"
        
        try:
            # Initialize AI pipelines
            self.summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", device=self.device)
            self.question_generator = pipeline("text2text-generation", model=self.key_insight_model, use_safetensors=True, device=self.device)
            self.topic_analyzer = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=self.device)
            self.action_item_extractor = pipeline("ner", model="ml6team/bert-base-uncased-road-ner", device=self.device)
            
            self.ai_available = True
            logger.info("AI components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI components: {e}")
            self.ai_available = False
    
    async def process_video_to_notebook(self, video_url: str, languages: List[str] = None) -> VideoNotebook:
        """Process video and generate comprehensive notebook"""
        if not self.ai_available:
            raise ValueError("AI components not available")
        
        logger.info(f"Creating notebook for video: {video_url}")
        start_time = datetime.now()
        
        # Extract video content
        video_content = await self.video_extractor.process_video(video_url, languages)
        
        if not video_content.transcript:
            raise ValueError("No transcript available for notebook generation")
        
        # Generate notebook components
        notebook_entries = await self._generate_notebook_entries(video_content)
        executive_summary = await self._generate_executive_summary(video_content)
        key_insights = await self._extract_key_insights(video_content)
        questions_raised = await self._generate_questions(video_content)
        action_items = await self._extract_action_items(video_content)
        concept_map = await self._build_concept_map(video_content)
        
        # Create notebook
        notebook = VideoNotebook(
            video_metadata=video_content.metadata,
            executive_summary=executive_summary,
            key_insights=key_insights,
            main_topics=video_content.topics or [],
            questions_raised=questions_raised,
            action_items=action_items,
            notebook_entries=notebook_entries,
            concept_map=concept_map,
            processing_metadata={
                'processed_at': start_time.isoformat(),
                'processing_duration': (datetime.now() - start_time).total_seconds(),
                'transcript_segments': len(video_content.transcript),
                'ai_models_used': ['bart-large-cnn', 't5-small-qg-hl', 'all-MiniLM-L6-v2']
            }
        )
        
        logger.info(f"Notebook generated with {len(notebook_entries)} entries")
        return notebook
    
    async def _generate_notebook_entries(self, video_content: VideoContent) -> List[NotebookEntry]:
        """Generate structured notebook entries from video content"""
        entries = []
        
        # Combine transcript into chunks for processing
        chunks = self._create_semantic_chunks(video_content.transcript)
        
        for i, chunk in enumerate(chunks):
            try:
                # Generate summary for chunk
                chunk_text = " ".join([seg.text for seg in chunk])
                
                if len(chunk_text) > 100:  # Only process substantial chunks
                    # Generate summary
                    summary = await self._generate_chunk_summary(chunk_text)
                    
                    # Extract key points
                    key_points = self._extract_chunk_key_points(chunk_text)
                    
                    # Calculate timestamp
                    timestamp = self._format_timestamp(chunk[0].start)
                    
                    # Create summary entry
                    if summary:
                        entries.append(NotebookEntry(
                            timestamp=timestamp,
                            content=summary,
                            entry_type="summary",
                            confidence=0.8,
                            related_segments=[j for j in range(len(chunk))],
                            tags=self._extract_tags(summary)
                        ))
                    
                    # Create key point entries
                    for point in key_points:
                        entries.append(NotebookEntry(
                            timestamp=timestamp,
                            content=point,
                            entry_type="key_point",
                            confidence=0.7,
                            related_segments=[j for j in range(len(chunk))],
                            tags=self._extract_tags(point)
                        ))
                
            except Exception as e:
                logger.warning(f"Failed to process chunk {i}: {e}")
                continue
        
        return entries
    
    def _create_semantic_chunks(self, transcript: List[TranscriptSegment], max_chunk_size: int = 500) -> List[List[TranscriptSegment]]:
        """Create semantically coherent chunks from transcript"""
        chunks = []
        current_chunk = []
        current_length = 0
        
        for segment in transcript:
            # Add segment to current chunk
            current_chunk.append(segment)
            current_length += len(segment.text)
            
            # Check if we should start a new chunk
            if (current_length >= max_chunk_size or 
                self._is_topic_boundary(segment.text)):
                
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_length = 0
        
        # Add remaining segments
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _is_topic_boundary(self, text: str) -> bool:
        """Detect potential topic boundaries in text"""
        boundary_indicators = [
            "now let's talk about",
            "moving on to",
            "next topic",
            "in conclusion",
            "to summarize",
            "on the other hand",
            "however",
            "meanwhile",
            "furthermore"
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in boundary_indicators)
    
    async def _generate_chunk_summary(self, text: str) -> str:
        """Generate summary for a text chunk"""
        try:
            if self.has_openai:
                # Use OpenAI for higher quality summaries
                response = await self._call_openai_api(
                    "Summarize the following text in 1-2 concise sentences:",
                    text
                )
                return response.strip()
            else:
                # Use local model
                if len(text) > 50:
                    summary_result = self.summarizer(
                        text, 
                        max_length=50, 
                        min_length=20, 
                        do_sample=False
                    )
                    return summary_result[0]['summary_text']
                else:
                    return text
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return ""
    
    def _extract_chunk_key_points(self, text: str) -> List[str]:
        """Extract key points from text chunk"""
        sentences = re.split(r'[.!?]+', text)
        key_points = []
        
        # Look for sentences with importance indicators
        importance_words = [
            'important', 'key', 'crucial', 'essential', 'significant',
            'remember', 'note that', 'keep in mind', 'it\'s worth',
            'main point', 'takeaway', 'conclusion'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if (len(sentence) > 30 and 
                any(word in sentence.lower() for word in importance_words)):
                key_points.append(sentence)
        
        return key_points[:3]  # Limit to top 3 per chunk
    
    async def _generate_executive_summary(self, video_content: VideoContent) -> str:
        """Generate executive summary of the entire video"""
        full_text = " ".join([seg.text for seg in video_content.transcript])
        
        try:
            if self.has_openai:
                prompt = f"""
                Create an executive summary of this video content. Include:
                1. Main topic and purpose
                2. Key findings or arguments
                3. Practical implications
                4. Target audience
                
                Video Title: {video_content.metadata.title}
                Content: {full_text[:2000]}...
                """
                
                summary = await self._call_openai_api(
                    "Generate an executive summary:",
                    prompt
                )
                return summary
            else:
                # Use existing summary if available, or generate new one
                if video_content.summary:
                    return video_content.summary
                else:
                    summary_result = self.summarizer(
                        full_text[:1000], 
                        max_length=200, 
                        min_length=100, 
                        do_sample=False
                    )
                    return summary_result[0]['summary_text']
        
        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return f"Executive summary unavailable. Video covers: {', '.join(video_content.topics[:5]) if video_content.topics else 'various topics'}"
    
    async def _extract_key_insights(self, video_content: VideoContent) -> List[str]:
        """Extract key insights from video content"""
        full_text = " ".join([seg.text for seg in video_content.transcript])
        insights = []
        
        try:
            if self.has_openai:
                prompt = f"""
                Extract 5-7 key insights from this video content. Focus on:
                - Novel ideas or perspectives
                - Practical applications
                - Important conclusions
                - Surprising findings
                
                Content: {full_text[:1500]}...
                """
                
                response = await self._call_openai_api(
                    "Extract key insights:",
                    prompt
                )
                
                # Parse insights from response
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                        insight = re.sub(r'^[-•\d\.\)]\s*', '', line)
                        if len(insight) > 20:
                            insights.append(insight)
            
            else:
                # Fallback: use existing key points or extract from text
                if video_content.key_points:
                    insights = video_content.key_points
                else:
                    # Simple extraction based on sentence patterns
                    sentences = re.split(r'[.!?]+', full_text)
                    insight_patterns = [
                        r'the key is',
                        r'what this means',
                        r'the important thing',
                        r'this shows that',
                        r'we can conclude',
                        r'this suggests'
                    ]
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if (len(sentence) > 30 and 
                            any(re.search(pattern, sentence.lower()) for pattern in insight_patterns)):
                            insights.append(sentence)
        
        except Exception as e:
            logger.error(f"Key insights extraction failed: {e}")
        
        return insights[:7]  # Limit to 7 insights
    
    async def _generate_questions(self, video_content: VideoContent) -> List[str]:
        """Generate thought-provoking questions based on content"""
        questions = []
        full_text = " ".join([seg.text for seg in video_content.transcript])
        
        try:
            if self.has_openai:
                prompt = f"""
                Generate 5-6 thought-provoking questions based on this video content.
                Questions should encourage deeper thinking and discussion.
                
                Content: {full_text[:1000]}...
                """
                
                response = await self._call_openai_api(
                    "Generate discussion questions:",
                    prompt
                )
                
                # Parse questions from response
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and ('?' in line):
                        question = re.sub(r'^[-•\d\.\)]\s*', '', line)
                        if len(question) > 10:
                            questions.append(question)
            
            else:
                # Use local question generation model
                try:
                    # Chunk text for question generation
                    chunks = [full_text[i:i+500] for i in range(0, len(full_text), 500)]
                    
                    for chunk in chunks[:3]:  # Limit to first 3 chunks
                        question_result = self.question_generator(
                            chunk,
                            max_length=50,
                            num_return_sequences=2
                        )
                        
                        for result in question_result:
                            question = result['generated_text'].strip()
                            if question and question not in questions:
                                questions.append(question)
                
                except Exception as e:
                    logger.warning(f"Local question generation failed: {e}")
                    # Fallback to pattern-based questions
                    questions = [
                        f"What are the main implications of the ideas discussed in '{video_content.metadata.title}'?",
                        "How might these concepts apply to real-world situations?",
                        "What questions does this content raise for further exploration?",
                        "How does this information challenge existing assumptions?",
                        "What would be the next logical steps to explore these ideas further?"
                    ]
        
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
        
        return questions[:6]  # Limit to 6 questions
    
    async def _extract_action_items(self, video_content: VideoContent) -> List[str]:
        """Extract actionable items from video content"""
        full_text = " ".join([seg.text for seg in video_content.transcript])
        action_items = []
        
        # Look for action-oriented language
        action_patterns = [
            r'you should (.+?)(?:[.!?]|$)',
            r'try to (.+?)(?:[.!?]|$)',
            r'make sure to (.+?)(?:[.!?]|$)',
            r'don\'t forget to (.+?)(?:[.!?]|$)',
            r'remember to (.+?)(?:[.!?]|$)',
            r'it\'s important to (.+?)(?:[.!?]|$)',
            r'next step is to (.+?)(?:[.!?]|$)'
        ]
        
        for pattern in action_patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                action = match.group(1).strip()
                if len(action) > 10 and len(action) < 100:
                    action_items.append(f"• {action}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_actions = []
        for action in action_items:
            if action.lower() not in seen:
                seen.add(action.lower())
                unique_actions.append(action)
        
        return unique_actions[:8]  # Limit to 8 action items
    
    async def _build_concept_map(self, video_content: VideoContent) -> Dict[str, List[str]]:
        """Build a concept map showing relationships between topics"""
        concept_map = {}
        
        if not video_content.topics:
            return concept_map
        
        # Use sentence transformer to find related concepts
        try:
            full_text = " ".join([seg.text for seg in video_content.transcript])
            
            # Extract sentences
            sentences = re.split(r'[.!?]+', full_text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
            
            # Encode sentences
            sentence_embeddings = self.sentence_transformer.encode(sentences)
            
            # For each topic, find related sentences and extract concepts
            for topic in video_content.topics[:5]:  # Limit to top 5 topics
                topic_embedding = self.sentence_transformer.encode([topic])
                
                # Find most similar sentences
                similarities = np.dot(sentence_embeddings, topic_embedding.T).flatten()
                top_indices = np.argsort(similarities)[-3:]  # Top 3 similar sentences
                
                related_concepts = []
                for idx in top_indices:
                    sentence = sentences[idx]
                    # Extract key terms from sentence
                    words = re.findall(r'\b[a-zA-Z]{4,}\b', sentence.lower())
                    # Filter and add unique concepts
                    for word in words:
                        if (word not in topic.lower() and 
                            word not in ['this', 'that', 'with', 'have', 'will', 'from'] and
                            word not in related_concepts):
                            related_concepts.append(word)
                
                concept_map[topic] = related_concepts[:5]  # Limit to 5 related concepts
        
        except Exception as e:
            logger.warning(f"Concept map generation failed: {e}")
        
        return concept_map
    
    async def _call_openai_api(self, system_prompt: str, user_content: str) -> str:
        """Call OpenAI API with error handling"""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from text"""
        # Simple tag extraction based on important words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Filter for meaningful tags
        meaningful_words = []
        stop_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'were', 'said'}
        
        for word in words:
            if word not in stop_words and len(word) > 4:
                meaningful_words.append(word)
        
        # Return unique tags, limited to 3
        return list(set(meaningful_words))[:3]
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS format"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"
    
    def export_notebook(self, notebook: VideoNotebook, format: str = "markdown", output_path: str = None) -> str:
        """Export notebook in various formats"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"notebook_{notebook.video_metadata.video_id}_{timestamp}"
        
        if format.lower() == "markdown":
            output_file = f"{output_path}.md"
            markdown_content = self._generate_notebook_markdown(notebook)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        
        elif format.lower() == "json":
            output_file = f"{output_path}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(notebook), f, indent=2, ensure_ascii=False, default=str)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Notebook exported to {output_file}")
        return output_file
    
    def _generate_notebook_markdown(self, notebook: VideoNotebook) -> str:
        """Generate markdown representation of notebook"""
        md = f"""# 📓 Video Notebook: {notebook.video_metadata.title}

## 📋 Executive Summary
{notebook.executive_summary}

## 🎯 Key Insights
"""
        
        for i, insight in enumerate(notebook.key_insights, 1):
            md += f"{i}. {insight}\n"
        
        md += f"""
## 🤔 Discussion Questions
"""
        
        for question in notebook.questions_raised:
            md += f"- {question}\n"
        
        md += f"""
## ✅ Action Items
"""
        
        for action in notebook.action_items:
            md += f"{action}\n"
        
        md += f"""
## 🗺️ Concept Map
"""
        
        for topic, concepts in notebook.concept_map.items():
            md += f"**{topic}**: {', '.join(concepts)}\n"
        
        md += f"""
## 📝 Detailed Notes

"""
        
        # Group entries by type
        entry_types = {}
        for entry in notebook.notebook_entries:
            if entry.entry_type not in entry_types:
                entry_types[entry.entry_type] = []
            entry_types[entry.entry_type].append(entry)
        
        for entry_type, entries in entry_types.items():
            md += f"### {entry_type.replace('_', ' ').title()}\n\n"
            
            for entry in entries:
                md += f"**[{entry.timestamp}]** {entry.content}\n"
                if entry.tags:
                    md += f"*Tags: {', '.join(entry.tags)}*\n"
                md += "\n"
        
        md += f"""
---
*Generated on {notebook.processing_metadata['processed_at']}*
*Processing time: {notebook.processing_metadata['processing_duration']:.2f}s*
"""
        
        return md

# Example usage
async def main():
    """Example usage of NotebookLM processor"""
    processor = NotebookLMProcessor()
    
    # Test video URL
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    
    try:
        # Generate notebook
        notebook = await processor.process_video_to_notebook(test_url)
        
        # Export notebook
        processor.export_notebook(notebook, "markdown")
        processor.export_notebook(notebook, "json")
        
        print(f"Notebook generated for: {notebook.video_metadata.title}")
        print(f"Insights: {len(notebook.key_insights)}")
        print(f"Questions: {len(notebook.questions_raised)}")
        print(f"Entries: {len(notebook.notebook_entries)}")
        
    except Exception as e:
        print(f"Notebook generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())