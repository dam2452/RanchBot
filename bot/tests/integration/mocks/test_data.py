from typing import Dict, Any, List


class TestSegments:
    @staticmethod
    def get_geniusz_segment() -> Dict[str, Any]:
        return {
            'text': 'Ty jesteś geniusz!',
            'start': 123.45,
            'end': 125.67,
            'video_path': '/fake/videos/ranczo_s01e01.mp4',
            'episode_info': {
                'season': 1,
                'episode_number': 1,
                'title': 'Pilot',
            },
            '_quote_keywords': ['geniusz'],
        }

    @staticmethod
    def get_wilk_segment() -> Dict[str, Any]:
        return {
            'text': 'Wilk syty i owca cała',
            'start': 234.56,
            'end': 237.89,
            'video_path': '/fake/videos/ranczo_s01e02.mp4',
            'episode_info': {
                'season': 1,
                'episode_number': 2,
                'title': 'Episode 2',
            },
            '_quote_keywords': ['wilk', 'owca'],
        }

    @staticmethod
    def get_multiple_segments() -> List[Dict[str, Any]]:
        return [
            TestSegments.get_geniusz_segment(),
            TestSegments.get_wilk_segment(),
            {
                'text': 'Nie ma to jak u mamy',
                'start': 345.67,
                'end': 348.90,
                'video_path': '/fake/videos/ranczo_s01e03.mp4',
                'episode_info': {
                    'season': 1,
                    'episode_number': 3,
                    'title': 'Episode 3',
                },
                '_quote_keywords': ['mama', 'dom'],
            },
        ]

    @staticmethod
    def get_long_segment() -> Dict[str, Any]:
        return {
            'text': ' '.join(['Lorem ipsum dolor sit amet'] * 20),
            'start': 100.0,
            'end': 130.0,
            'video_path': '/fake/videos/ranczo_s01e01.mp4',
            'episode_info': {
                'season': 1,
                'episode_number': 1,
                'title': 'Pilot',
            },
            '_quote_keywords': ['lorem'],
        }
