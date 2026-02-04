
import unittest
from src.youtube_extension.processors.scoring_engine import ScoringEngine

class TestScoringEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ScoringEngine()
        
        # Common test data
        self.video_info = {
            'id': 'test_video_1',
            'snippet': {
                'title': 'Test Video',
                'description': 'A test video for unit testing'
            },
            'contentDetails': {
                'duration': 'PT10M30S' # 10m 30s = 630s
            },
            'statistics': {
                'viewCount': '1000',
                'likeCount': '100',
                'commentCount': '50'
            }
        }
        
        self.transcript = [
            {'text': 'Welcome to this tutorial on Python programming', 'start': 0, 'duration': 5},
            {'text': 'We will learn about algorithms and data structures', 'start': 5, 'duration': 5},
            {'text': 'This framework is optimized for scalability and performance', 'start': 10, 'duration': 5},
            {'text': 'Let us implement a secure API endpoint', 'start': 15, 'duration': 5},
            {'text': 'Testing and debugging are crucial for enterprise applications', 'start': 20, 'duration': 5}
        ]

    def test_calculate_all_scores_structure(self):
        scores = self.engine.calculate_all_scores(self.video_info, self.transcript)
        
        expected_keys = [
            "content_quality", 
            "engagement_metrics", 
            "learning_potential", 
            "technical_depth", 
            "world_class_indicators", 
            "recommendations"
        ]
        
        for key in expected_keys:
            self.assertIn(key, scores)

    def test_content_quality_analysis(self):
        quality = self.engine._analyze_content_quality(self.video_info, self.transcript)
        
        self.assertEqual(quality['duration_seconds'], 630)
        self.assertEqual(quality['view_count'], 1000)
        # Engagement rate: (100+50)/1000 * 100 = 15.0
        self.assertEqual(quality['engagement_rate'], 15.0)
        self.assertIn('transcript_quality', quality)

    def test_engagement_analysis(self):
        engagement = self.engine._analyze_engagement(self.video_info)
        
        self.assertEqual(engagement['view_count'], 1000)
        self.assertEqual(engagement['like_count'], 100)
        self.assertEqual(engagement['comment_count'], 50)
        self.assertEqual(engagement['engagement_rate'], 15.0)
        # Viral potential: 0.15 * 1000 = 150 -> max capped at 10
        self.assertEqual(engagement['viral_potential'], 10.0)

    def test_learning_potential_analysis(self):
        # Transcript contains: tutorial, learn
        potential = self.engine._analyze_learning_potential(self.transcript)
        
        self.assertTrue(potential['learning_score'] >= 2)
        self.assertTrue(potential['educational_value'] > 0)
        self.assertIn('tutorial', potential['key_learning_indicators'])

    def test_technical_depth_analysis(self):
        # Transcript contains: algorithm, framework, optimized, scalability, performance, api, testing, debugging
        depth = self.engine._analyze_technical_depth(self.transcript)
        
        self.assertTrue(depth['technical_score'] >= 5)
        self.assertTrue(depth['technical_density'] > 0)
        self.assertIn('algorithm', depth['technical_topics'])
        
        # With high density (score/len = >1.0?), it should be Expert or Advanced
        # 5 items, >5 keywords -> density > 1.0. 
        # _determine_complexity_level: >0.3 is Expert
        self.assertEqual(depth['complexity_level'], 'Expert')

    def test_generate_actions(self):
        # Create analysis dict that triggers all actions
        analysis = {
            'learning_potential': {'educational_value': 8}, # > 7
            'technical_depth': {'technical_density': 0.2}, # > 0.15
            'world_class_indicators': {'community_impact': {'score': 8}} # > 7
        }
        
        actions = self.engine.generate_actions(analysis)
        
        self.assertEqual(len(actions), 3)
        action_types = [a['type'] for a in actions]
        self.assertIn('learning_pathway', action_types)
        self.assertIn('implementation', action_types)
        self.assertIn('community', action_types)

    def test_parse_duration(self):
        self.assertEqual(self.engine._parse_duration("PT1H2M3S"), 3723)
        self.assertEqual(self.engine._parse_duration("PT1M"), 60)
        self.assertEqual(self.engine._parse_duration("PT10S"), 10)
        self.assertEqual(self.engine._parse_duration("P1DT1H"), 0) # Regex expects PT start

    def test_zero_division_resilience(self):
        empty_info = {
            'statistics': {'viewCount': '0', 'likeCount': '0', 'commentCount': '0'},
            'contentDetails': {'duration': 'PT0S'}
        }
        empty_transcript = []
        
        # Should not raise exception
        scores = self.engine.calculate_all_scores(empty_info, empty_transcript)
        
        self.assertEqual(scores['content_quality']['view_count'], 0)
        self.assertEqual(scores['engagement_metrics']['engagement_rate'], 0.0)

if __name__ == '__main__':
    unittest.main()
