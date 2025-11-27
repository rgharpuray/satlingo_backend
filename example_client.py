"""
Example Python API Client for SAT Prep Reading Comprehension API

This is a reference implementation showing how to integrate with the API from Python.
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime


class SATPrepAPIClient:
    """Client for interacting with the SAT Prep Reading Comprehension API"""

    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an API request"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_data = e.response.json() if e.response.content else {}
            raise Exception(
                error_data.get('error', {}).get('message', str(e))
            ) from e

    # ==================== PASSAGES ====================

    def get_passages(
        self,
        difficulty: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get all passages with optional filtering"""
        params = {}
        if difficulty:
            params['difficulty'] = difficulty
        if limit:
            params['limit'] = limit
        if offset:
            params['offset'] = offset
        
        return self._request('GET', '/passages', params=params)

    def get_passage_detail(self, passage_id: str) -> Dict[str, Any]:
        """Get passage detail (includes correct answers - use with caution)"""
        return self._request('GET', f'/passages/{passage_id}')

    def get_passage_questions(self, passage_id: str) -> Dict[str, Any]:
        """Get passage questions without correct answers (for active sessions)"""
        return self._request('GET', f'/passages/{passage_id}/questions')

    # ==================== QUESTIONS ====================

    def get_question(self, question_id: str) -> Dict[str, Any]:
        """Get question detail"""
        return self._request('GET', f'/questions/{question_id}')

    # ==================== PROGRESS ====================

    def get_progress(self) -> Dict[str, Any]:
        """Get user progress summary"""
        return self._request('GET', '/progress')

    def get_passage_progress(self, passage_id: str) -> Dict[str, Any]:
        """Get progress for a specific passage"""
        return self._request('GET', f'/progress/passages/{passage_id}')

    def start_session(
        self,
        passage_id: str,
        started_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a passage session"""
        data = {
            'started_at': started_at or datetime.utcnow().isoformat() + 'Z'
        }
        return self._request('POST', f'/progress/passages/{passage_id}/start', data=data)

    def submit_passage(
        self,
        passage_id: str,
        answers: List[Dict[str, Any]],
        time_spent_seconds: int = 0
    ) -> Dict[str, Any]:
        """Submit answers for a passage"""
        data = {
            'answers': answers,
            'time_spent_seconds': time_spent_seconds
        }
        return self._request('POST', f'/progress/passages/{passage_id}/submit', data=data)

    def get_review(self, passage_id: str) -> Dict[str, Any]:
        """Get review data for a completed passage"""
        return self._request('GET', f'/progress/passages/{passage_id}/review')

    # ==================== ANSWERS ====================

    def submit_answer(
        self,
        question_id: str,
        selected_option_index: int
    ) -> Dict[str, Any]:
        """Submit a single answer (for real-time tracking)"""
        data = {
            'question_id': question_id,
            'selected_option_index': selected_option_index
        }
        return self._request('POST', '/answers', data=data)

    def get_passage_answers(self, passage_id: str) -> Dict[str, Any]:
        """Get all answers for a passage"""
        return self._request('GET', f'/answers/passage/{passage_id}')


# ==================== USAGE EXAMPLES ====================

def example_complete_flow():
    """Example: Complete passage flow"""
    client = SATPrepAPIClient()

    try:
        # 1. Get all passages
        passages_response = client.get_passages(difficulty='Medium')
        print(f"Available passages: {len(passages_response.get('results', []))}")

        if not passages_response.get('results'):
            print('No passages available')
            return

        passage = passages_response['results'][0]
        passage_id = passage['id']

        # 2. Start a session (optional)
        session = client.start_session(passage_id)
        print(f"Session started: {session['session_id']}")

        # 3. Get questions (without correct answers)
        questions_data = client.get_passage_questions(passage_id)
        questions = questions_data.get('questions', [])
        print(f"Found {len(questions)} questions")

        # 4. Simulate user answering questions
        import random
        user_answers = []
        start_time = datetime.now()

        for question in questions:
            # Simulate user selecting an option
            selected_index = random.randint(0, len(question['options']) - 1)
            user_answers.append({
                'question_id': question['id'],
                'selected_option_index': selected_index
            })

        # 5. Calculate time spent
        time_spent = int((datetime.now() - start_time).total_seconds())

        # 6. Submit final answers
        results = client.submit_passage(passage_id, user_answers, time_spent)
        print(f"Results: Score={results['score']}%, "
              f"Correct={results['correct_count']}/{results['total_questions']}")

        # 7. Get review with explanations
        review = client.get_review(passage_id)
        print(f"Review data retrieved: {len(review.get('answers', []))} answers")

    except Exception as e:
        print(f"Error in flow: {e}")


def example_track_progress():
    """Example: Track progress"""
    client = SATPrepAPIClient()

    try:
        # Get user's overall progress
        progress = client.get_progress()
        print(f"Progress: {progress['completed_count']}/{progress['total_passages']} completed")
        print(f"Scores: {progress['scores']}")

    except Exception as e:
        print(f"Error tracking progress: {e}")


if __name__ == '__main__':
    # Run examples
    print("=== Complete Flow Example ===")
    example_complete_flow()
    
    print("\n=== Progress Tracking Example ===")
    example_track_progress()


