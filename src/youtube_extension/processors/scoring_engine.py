from typing import Dict, Any, List
import re

class ScoringEngine:
    """
    Encapsulates the 'World Class' scoring and analysis logic.
    Originally from MCPEnhancedVideoProcessor.
    """

    def calculate_all_scores(self, video_info: Dict[str, Any], transcript: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform comprehensive world-class analysis"""
        return {
            "content_quality": self._analyze_content_quality(video_info, transcript),
            "engagement_metrics": self._analyze_engagement(video_info),
            "learning_potential": self._analyze_learning_potential(transcript),
            "technical_depth": self._analyze_technical_depth(transcript),
            "world_class_indicators": self._identify_world_class_indicators(video_info, transcript),
            "recommendations": self._generate_world_class_recommendations(video_info, transcript)
        }
    
    def generate_actions(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable insights based on world-class analysis"""
        actions = []
        
        # Learning pathway actions
        if analysis.get('learning_potential', {}).get('educational_value', 0) > 7:
            actions.append({
                "type": "learning_pathway",
                "priority": "high",
                "title": "Create Structured Learning Module",
                "description": "Break down content into digestible learning units",
                "estimated_time": "45 minutes",
                "impact": "Increase learning retention by 80%"
            })
        
        # Implementation actions
        if analysis.get('technical_depth', {}).get('technical_density', 0) > 0.15:
            actions.append({
                "type": "implementation",
                "priority": "high",
                "title": "Build Practical Implementation",
                "description": "Create working code examples and projects",
                "estimated_time": "90 minutes",
                "impact": "Reinforce technical concepts through practice"
            })
        
        # Community building actions
        if analysis.get('world_class_indicators', {}).get('community_impact', {}).get('score', 0) > 7:
            actions.append({
                "type": "community",
                "priority": "medium",
                "title": "Share and Collaborate",
                "description": "Create discussion forums and collaboration opportunities",
                "estimated_time": "30 minutes",
                "impact": "Build knowledge-sharing community"
            })
        
        return actions

    def _analyze_content_quality(self, video_info: Dict, transcript: List) -> Dict[str, Any]:
        duration = video_info.get('contentDetails', {}).get('duration', 'PT0S')
        view_count = int(video_info.get('statistics', {}).get('viewCount', 0))
        like_count = int(video_info.get('statistics', {}).get('likeCount', 0))
        comment_count = int(video_info.get('statistics', {}).get('commentCount', 0))
        
        engagement_rate = (like_count + comment_count) / max(view_count, 1) * 100
        transcript_length = sum(len(segment.get('text', '')) for segment in transcript)
        avg_segment_length = transcript_length / max(len(transcript), 1)
        
        return {
            "duration_seconds": self._parse_duration(duration),
            "view_count": view_count,
            "engagement_rate": round(engagement_rate, 2),
            "transcript_quality": {
                "total_words": transcript_length,
                "avg_segment_length": round(avg_segment_length, 2),
                "coverage_score": min(len(transcript) / 10, 1.0)
            },
            "quality_score": self._calculate_quality_score(video_info, transcript)
        }

    def _analyze_engagement(self, video_info: Dict) -> Dict[str, Any]:
        stats = video_info.get('statistics', {})
        view_count = int(stats.get('viewCount', 0))
        like_count = int(stats.get('likeCount', 0))
        comment_count = int(stats.get('commentCount', 0))
        
        return {
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "engagement_rate": round((like_count + comment_count) / max(view_count, 1) * 100, 2),
            "viral_potential": self._calculate_viral_potential(view_count, like_count, comment_count)
        }

    def _analyze_learning_potential(self, transcript: List) -> Dict[str, Any]:
        learning_keywords = [
            'tutorial', 'guide', 'how to', 'step by step', 'explanation',
            'learn', 'understand', 'concept', 'example', 'demonstration',
            'best practice', 'technique', 'method', 'approach', 'strategy'
        ]
        full_text = ' '.join(segment.get('text', '').lower() for segment in transcript)
        learning_score = sum(1 for keyword in learning_keywords if keyword in full_text)
        learning_density = learning_score / max(len(transcript), 1)
        
        return {
            "learning_score": learning_score,
            "learning_density": round(learning_density, 3),
            "educational_value": min(learning_density * 10, 10),
            "key_learning_indicators": [kw for kw in learning_keywords if kw in full_text]
        }

    def _analyze_technical_depth(self, transcript: List) -> Dict[str, Any]:
        technical_keywords = [
            'algorithm', 'architecture', 'framework', 'api', 'database',
            'optimization', 'performance', 'scalability', 'security',
            'deployment', 'testing', 'monitoring', 'debugging', 'profiling'
        ]
        full_text = ' '.join(segment.get('text', '').lower() for segment in transcript)
        technical_score = sum(1 for keyword in technical_keywords if keyword in full_text)
        technical_density = technical_score / max(len(transcript), 1)
        
        return {
            "technical_score": technical_score,
            "technical_density": round(technical_density, 3),
            "complexity_level": self._determine_complexity_level(technical_density),
            "technical_topics": [kw for kw in technical_keywords if kw in full_text]
        }

    def _identify_world_class_indicators(self, video_info: Dict, transcript: List) -> Dict[str, Any]:
        return {
            "production_quality": self._assess_production_quality(video_info),
            "expertise_level": self._assess_expertise_level(transcript),
            "innovation_factor": self._assess_innovation_factor(transcript),
            "practical_value": self._assess_practical_value(transcript),
            "community_impact": self._assess_community_impact(video_info)
        }

    def _generate_world_class_recommendations(self, video_info: Dict, transcript: List) -> List[Dict[str, Any]]:
        recommendations = []
        if len(transcript) < 10:
            recommendations.append({
                "type": "content_improvement",
                "priority": "high",
                "suggestion": "Add more detailed explanations and examples",
                "impact": "Increase learning effectiveness by 40%"
            })
        
        stats = video_info.get('statistics', {})
        engagement_rate = (int(stats.get('likeCount', 0)) + int(stats.get('commentCount', 0))) / max(int(stats.get('viewCount', 1)), 1)
        
        if engagement_rate < 0.05:
            recommendations.append({
                "type": "engagement_optimization",
                "priority": "medium",
                "suggestion": "Add interactive elements and call-to-actions",
                "impact": "Increase engagement by 60%"
            })
            
        technical_score = self._analyze_technical_depth(transcript)
        if technical_score['technical_density'] < 0.1:
            recommendations.append({
                "type": "technical_depth",
                "priority": "medium",
                "suggestion": "Include more technical details and code examples",
                "impact": "Enhance technical credibility"
            })
        return recommendations

    def _parse_duration(self, duration: str) -> int:
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0

    def _calculate_quality_score(self, video_info: Dict, transcript: List) -> float:
        stats = video_info.get('statistics', {})
        view_count = int(stats.get('viewCount', 0))
        like_count = int(stats.get('likeCount', 0))
        comment_count = int(stats.get('commentCount', 0))
        
        engagement_score = min((like_count + comment_count) / max(view_count, 1) * 100, 10)
        content_score = min(len(transcript) / 20, 5)
        duration = self._parse_duration(video_info.get('contentDetails', {}).get('duration', 'PT0S'))
        duration_score = min(duration / 1800, 5)
        return min(engagement_score + content_score + duration_score, 10)

    def _calculate_viral_potential(self, view_count: int, like_count: int, comment_count: int) -> float:
        if view_count == 0: return 0
        engagement_rate = (like_count + comment_count) / view_count
        return round(min(engagement_rate * 1000, 10), 2)

    def _determine_complexity_level(self, technical_density: float) -> str:
        if technical_density > 0.3: return "Expert"
        elif technical_density > 0.15: return "Advanced"
        elif technical_density > 0.05: return "Intermediate"
        return "Beginner"

    def _assess_production_quality(self, video_info: Dict) -> Dict[str, Any]:
        duration = self._parse_duration(video_info.get('contentDetails', {}).get('duration', 'PT0S'))
        duration_score = min(duration / 1800, 5)
        return {
            "score": round(duration_score, 2),
            "indicators": ["structured_content", "professional_presentation"],
            "recommendations": ["improve_audio_quality", "add_visual_aids"]
        }

    def _assess_expertise_level(self, transcript: List) -> Dict[str, Any]:
        expert_keywords = ['expert', 'professional', 'industry', 'enterprise', 'scalable', 'production', 'best practice', 'architecture', 'optimization']
        full_text = ' '.join(segment.get('text', '').lower() for segment in transcript)
        expert_mentions = sum(1 for keyword in expert_keywords if keyword in full_text)
        return {
            "score": min(expert_mentions / 5, 10),
            "expertise_indicators": [kw for kw in expert_keywords if kw in full_text],
            "level": "Expert" if expert_mentions > 3 else "Intermediate"
        }

    def _assess_innovation_factor(self, transcript: List) -> Dict[str, Any]:
        innovation_keywords = ['new', 'innovative', 'breakthrough', 'revolutionary', 'cutting-edge', 'latest', 'advanced', 'next-generation', 'future', 'emerging']
        full_text = ' '.join(segment.get('text', '').lower() for segment in transcript)
        innovation_mentions = sum(1 for keyword in innovation_keywords if keyword in full_text)
        return {
            "score": min(innovation_mentions / 3, 10),
            "innovation_indicators": [kw for kw in innovation_keywords if kw in full_text]
        }

    def _assess_practical_value(self, transcript: List) -> Dict[str, Any]:
        practical_keywords = ['implement', 'build', 'create', 'develop', 'deploy', 'test', 'debug', 'optimize', 'monitor', 'maintain']
        full_text = ' '.join(segment.get('text', '').lower() for segment in transcript)
        practical_mentions = sum(1 for keyword in practical_keywords if keyword in full_text)
        return {
            "score": min(practical_mentions / 5, 10),
            "practical_indicators": [kw for kw in practical_keywords if kw in full_text]
        }

    def _assess_community_impact(self, video_info: Dict) -> Dict[str, Any]:
        stats = video_info.get('statistics', {})
        view_count = int(stats.get('viewCount', 0))
        comment_count = int(stats.get('commentCount', 0))
        engagement_rate = comment_count / max(view_count, 1)
        return {
            "score": min(engagement_rate * 100, 10),
            "community_indicators": ["high_engagement", "active_discussion"],
            "impact_level": "High" if engagement_rate > 0.01 else "Medium"
        }
