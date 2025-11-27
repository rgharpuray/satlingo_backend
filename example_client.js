/**
 * Example JavaScript/TypeScript API Client for SAT Prep Reading Comprehension API
 * 
 * This is a reference implementation showing how to integrate with the API.
 * Adapt this to your specific framework (React, Vue, Angular, etc.)
 */

class SATPrepAPIClient {
  constructor(baseURL = 'http://localhost:8000/api/v1') {
    this.baseURL = baseURL;
  }

  /**
   * Helper method for making API requests
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || `HTTP ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // ==================== PASSAGES ====================

  /**
   * Get all passages
   * @param {Object} filters - Optional filters
   * @param {string} filters.difficulty - Filter by difficulty (Easy, Medium, Hard)
   * @param {number} filters.limit - Number of results
   * @param {number} filters.offset - Pagination offset
   * @returns {Promise<Object>} Passages list
   */
  async getPassages(filters = {}) {
    const params = new URLSearchParams();
    if (filters.difficulty) params.append('difficulty', filters.difficulty);
    if (filters.limit) params.append('limit', filters.limit);
    if (filters.offset) params.append('offset', filters.offset);

    const query = params.toString();
    return this.request(`/passages${query ? `?${query}` : ''}`);
  }

  /**
   * Get passage detail (includes correct answers - use with caution)
   * @param {string} passageId - Passage UUID
   * @returns {Promise<Object>} Passage with questions
   */
  async getPassageDetail(passageId) {
    return this.request(`/passages/${passageId}`);
  }

  /**
   * Get passage questions without correct answers (for active sessions)
   * @param {string} passageId - Passage UUID
   * @returns {Promise<Object>} Questions with options
   */
  async getPassageQuestions(passageId) {
    return this.request(`/passages/${passageId}/questions`);
  }

  // ==================== QUESTIONS ====================

  /**
   * Get question detail
   * @param {string} questionId - Question UUID
   * @returns {Promise<Object>} Question with options
   */
  async getQuestion(questionId) {
    return this.request(`/questions/${questionId}`);
  }

  // ==================== PROGRESS ====================

  /**
   * Get user progress summary
   * @returns {Promise<Object>} Progress summary
   */
  async getProgress() {
    return this.request('/progress');
  }

  /**
   * Get progress for a specific passage
   * @param {string} passageId - Passage UUID
   * @returns {Promise<Object>} Passage progress
   */
  async getPassageProgress(passageId) {
    return this.request(`/progress/passages/${passageId}`);
  }

  /**
   * Start a passage session
   * @param {string} passageId - Passage UUID
   * @param {string} startedAt - ISO 8601 timestamp (optional)
   * @returns {Promise<Object>} Session info
   */
  async startSession(passageId, startedAt = null) {
    return this.request(`/progress/passages/${passageId}/start`, {
      method: 'POST',
      body: {
        started_at: startedAt || new Date().toISOString(),
      },
    });
  }

  /**
   * Submit answers for a passage
   * @param {string} passageId - Passage UUID
   * @param {Array} answers - Array of {question_id, selected_option_index}
   * @param {number} timeSpentSeconds - Time spent in seconds
   * @returns {Promise<Object>} Submission results
   */
  async submitPassage(passageId, answers, timeSpentSeconds = 0) {
    return this.request(`/progress/passages/${passageId}/submit`, {
      method: 'POST',
      body: {
        answers,
        time_spent_seconds: timeSpentSeconds,
      },
    });
  }

  /**
   * Get review data for a completed passage
   * @param {string} passageId - Passage UUID
   * @returns {Promise<Object>} Review data with explanations
   */
  async getReview(passageId) {
    return this.request(`/progress/passages/${passageId}/review`);
  }

  // ==================== ANSWERS ====================

  /**
   * Submit a single answer (for real-time tracking)
   * @param {string} questionId - Question UUID
   * @param {number} selectedOptionIndex - 0-based index
   * @returns {Promise<Object>} Answer record
   */
  async submitAnswer(questionId, selectedOptionIndex) {
    return this.request('/answers', {
      method: 'POST',
      body: {
        question_id: questionId,
        selected_option_index: selectedOptionIndex,
      },
    });
  }

  /**
   * Get all answers for a passage
   * @param {string} passageId - Passage UUID
   * @returns {Promise<Object>} Answers array
   */
  async getPassageAnswers(passageId) {
    return this.request(`/answers/passage/${passageId}`);
  }
}

// ==================== USAGE EXAMPLES ====================

/**
 * Example: Complete passage flow
 */
async function exampleCompleteFlow() {
  const client = new SATPrepAPIClient();

  try {
    // 1. Get all passages
    const passagesResponse = await client.getPassages({ difficulty: 'Medium' });
    console.log('Available passages:', passagesResponse.results);

    if (passagesResponse.results.length === 0) {
      console.log('No passages available');
      return;
    }

    const passage = passagesResponse.results[0];
    const passageId = passage.id;

    // 2. Start a session (optional)
    const session = await client.startSession(passageId);
    console.log('Session started:', session.session_id);

    // 3. Get questions (without correct answers)
    const questionsData = await client.getPassageQuestions(passageId);
    console.log('Questions:', questionsData.questions);

    // 4. Simulate user answering questions
    const userAnswers = [];
    const startTime = Date.now();

    for (const question of questionsData.questions) {
      // Simulate user selecting an option (in real app, this comes from UI)
      const selectedIndex = Math.floor(Math.random() * question.options.length);
      userAnswers.push({
        question_id: question.id,
        selected_option_index: selectedIndex,
      });

      // Optionally submit answer in real-time
      // await client.submitAnswer(question.id, selectedIndex);
    }

    // 5. Calculate time spent
    const timeSpent = Math.floor((Date.now() - startTime) / 1000);

    // 6. Submit final answers
    const results = await client.submitPassage(passageId, userAnswers, timeSpent);
    console.log('Results:', {
      score: results.score,
      correct: results.correct_count,
      total: results.total_questions,
    });

    // 7. Get review with explanations
    const review = await client.getReview(passageId);
    console.log('Review data:', review);

  } catch (error) {
    console.error('Error in flow:', error);
  }
}

/**
 * Example: Track progress
 */
async function exampleTrackProgress() {
  const client = new SATPrepAPIClient();

  try {
    // Get user's overall progress
    const progress = await client.getProgress();
    console.log('Progress:', {
      completed: progress.completed_count,
      total: progress.total_passages,
      scores: progress.scores,
    });

    // Get progress for a specific passage
    const passageId = '550e8400-e29b-41d4-a716-446655440000';
    const passageProgress = await client.getPassageProgress(passageId);
    console.log('Passage progress:', passageProgress);

  } catch (error) {
    console.error('Error tracking progress:', error);
  }
}

/**
 * Example: React Hook usage
 */
// import { useState, useEffect } from 'react';
// 
// function usePassage(passageId) {
//   const [passage, setPassage] = useState(null);
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState(null);
//   const client = new SATPrepAPIClient();
// 
//   useEffect(() => {
//     async function loadPassage() {
//       try {
//         setLoading(true);
//         const data = await client.getPassageQuestions(passageId);
//         setPassage(data);
//       } catch (err) {
//         setError(err);
//       } finally {
//         setLoading(false);
//       }
//     }
//     loadPassage();
//   }, [passageId]);
// 
//   return { passage, loading, error };
// }

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SATPrepAPIClient };
}

// Export for ES6 modules
if (typeof window !== 'undefined') {
  window.SATPrepAPIClient = SATPrepAPIClient;
}


