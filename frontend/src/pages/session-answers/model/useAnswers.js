import { useState, useEffect } from 'react';
import { sessionAPI } from '@/entities/session';
import { answersAPI } from '@/entities/answer';
import { fetchDdTypes } from '@/entities/dd-type';
import toast from 'react-hot-toast';

export const useAnswers = (sessionId, selectedDDType, selectedSection) => {
  const [session, setSession] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [ddTypes, setDdTypes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [sessionId, selectedDDType, selectedSection]);

  const loadData = async () => {
    try {
      setLoading(true);

      const [sessionResponse, ddTypesResponse] = await Promise.all([
        sessionAPI.get(sessionId),
        // Inactive types too: their answers are still reviewed.
        fetchDdTypes({ activeOnly: false }),
      ]);

      setSession(sessionResponse.data);
      setDdTypes(ddTypesResponse);

      const params = {};
      if (selectedDDType) params.dd_type = selectedDDType;
      if (selectedSection) params.section = selectedSection;

      const answersResponse = await answersAPI.getBySession(sessionId, params);

      let answersData = [];
      if (Array.isArray(answersResponse.data)) {
        answersData = answersResponse.data;
      } else if (answersResponse.data && typeof answersResponse.data === 'object') {
        if (Array.isArray(answersResponse.data.answers)) {
          answersData = answersResponse.data.answers;
        } else if (Array.isArray(answersResponse.data.items)) {
          answersData = answersResponse.data.items;
        } else if (Array.isArray(answersResponse.data.data)) {
          answersData = answersResponse.data.data;
        } else if (Array.isArray(answersResponse.data.results)) {
          answersData = answersResponse.data.results;
        } else {
          for (const [key, value] of Object.entries(answersResponse.data)) {
            if (Array.isArray(value)) {
              answersData = value;
              break;
            }
          }
        }
      }

      const mappedAnswers = answersData.map(answer => ({
        ...answer,
        text: answer.answer_text || answer.text,
        dd_type_name: answer.dd_type_code || answer.dd_type_name,
      }));

      setAnswers(mappedAnswers);
    } catch (error) {
      toast.error('Failed to load session data');
      setAnswers([]);
    } finally {
      setLoading(false);
    }
  };

  const updateAnswer = async (answerId, updates) => {
    // If this is a status update, call the API
    if (updates.status) {
      try {
        const response = await answersAPI.updateStatus(answerId, updates.status);
        // Update local state with the response data
        setAnswers(answers.map(answer =>
          answer.id === answerId
            ? { ...answer, status: response.data.status }
            : answer
        ));
      } catch (error) {
        console.error('Failed to update answer status:', error);
        throw error;
      }
    } else {
      // For other updates, just update local state
      setAnswers(answers.map(answer =>
        answer.id === answerId
          ? { ...answer, ...updates }
          : answer
      ));
    }
  };

  return {
    session,
    answers,
    ddTypes,
    loading,
    loadData,
    updateAnswer
  };
};
