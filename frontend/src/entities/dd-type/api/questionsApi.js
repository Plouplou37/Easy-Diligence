import { api } from '@/shared/api';
import { invalidateDdTypes } from '../model/ddTypesCache';

// Every change to a section or a question changes the cached structures.
const changing = (request) =>
  request.then((response) => {
    invalidateDdTypes();
    return response;
  });

export const questionsAPI = {
  createQuestion: (ddTypeCode, sectionId, question) =>
    changing(api.post(`/questions/dd-types/${ddTypeCode}/sections/${sectionId}/questions`, question)),
  updateQuestion: (questionId, question) =>
    changing(api.put(`/questions/questions/${questionId}`, question)),
  deleteQuestion: (questionId) => changing(api.delete(`/questions/questions/${questionId}`)),
  reorderQuestion: (questionId, newOrder) =>
    changing(api.patch(`/questions/questions/${questionId}/reorder`, { new_order: newOrder })),
  createSection: (ddTypeCode, section) =>
    changing(api.post(`/questions/dd-types/${ddTypeCode}/sections`, section)),
  updateSection: (sectionId, section) =>
    changing(api.put(`/questions/sections/${sectionId}`, section)),
  deleteSection: (sectionId) => changing(api.delete(`/questions/sections/${sectionId}`)),
  reorderSection: (sectionId, newOrder) =>
    changing(api.patch(`/questions/sections/${sectionId}/reorder`, { new_order: newOrder })),
};
