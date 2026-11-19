import { api, multipart } from '@/shared/api';
import { invalidateDdTypes } from '../model/ddTypesCache';

// Every change to a DD type changes the cached lists.
const changing = request =>
  request.then(response => {
    invalidateDdTypes();
    return response;
  });

export const ddTypesAPI = {
  create: ddType => changing(api.post('/dd-types/', ddType)),
  update: (ddTypeCode, ddType) => changing(api.put(`/dd-types/${ddTypeCode}`, ddType)),
  delete: ddTypeCode => changing(api.delete(`/dd-types/${ddTypeCode}`)),
  importFromFile: formData => changing(api.post('/dd-types/import', formData, multipart)),
  activate: ddTypeCode => changing(api.post(`/dd-types/${ddTypeCode}/activate`)),
  deactivate: ddTypeCode => changing(api.post(`/dd-types/${ddTypeCode}/deactivate`)),
  validate: ddTypeCode => changing(api.put(`/dd-types/${ddTypeCode}/validate`)),
};
