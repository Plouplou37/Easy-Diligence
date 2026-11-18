import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  CloudArrowUpIcon, 
  DocumentIcon, 
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { documentsAPI } from '../services/api';

const DocumentUpload = ({ sessionId, onUploadComplete, disabled = false }) => {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});

  const onDrop = useCallback(async (acceptedFiles) => {
    if (disabled || uploading) return;

    setUploading(true);
    const newProgress = {};
    
    // Initialize progress for each file
    acceptedFiles.forEach((file, index) => {
      newProgress[file.name] = { progress: 0, status: 'uploading' };
    });
    setUploadProgress(newProgress);

    try {
      // Simulate progress updates (in real implementation, this would come from upload progress)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const updated = { ...prev };
          Object.keys(updated).forEach(fileName => {
            if (updated[fileName].status === 'uploading' && updated[fileName].progress < 90) {
              updated[fileName].progress += Math.random() * 20;
            }
          });
          return updated;
        });
      }, 200);

      // Upload files
      const response = await documentsAPI.upload(sessionId, acceptedFiles);
      
      clearInterval(progressInterval);

      // Mark all as completed
      setUploadProgress(prev => {
        const updated = { ...prev };
        Object.keys(updated).forEach(fileName => {
          updated[fileName] = { progress: 100, status: 'completed' };
        });
        return updated;
      });

      // Add to uploaded files list
      const newFiles = acceptedFiles.map((file, index) => ({
        name: file.name,
        size: file.size,
        type: file.type,
        fileId: response.data.file_ids[index],
        uploadedAt: new Date()
      }));

      setUploadedFiles(prev => [...prev, ...newFiles]);
      
      // Notify parent component
      if (onUploadComplete) {
        onUploadComplete(response.data);
      }

      // Clear progress after a delay
      setTimeout(() => {
        setUploadProgress({});
      }, 2000);

    } catch (error) {
      // Mark all as failed
      setUploadProgress(prev => {
        const updated = { ...prev };
        Object.keys(updated).forEach(fileName => {
          updated[fileName] = { progress: 0, status: 'failed' };
        });
        return updated;
      });

      // Clear progress after a delay
      setTimeout(() => {
        setUploadProgress({});
      }, 3000);
    } finally {
      setUploading(false);
    }
  }, [sessionId, onUploadComplete, disabled, uploading]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: disabled || uploading,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: true
  });

  const removeFile = (index) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (type) => {
    if (type.includes('pdf')) return '=�';
    if (type.includes('word') || type.includes('document')) return '=�';
    if (type.includes('sheet') || type.includes('excel')) return '=�';
    if (type.includes('text')) return '=�';
    return '=�';
  };

  return (
    <div className="w-full">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors duration-200
          ${isDragActive 
            ? 'border-blue-400 bg-blue-50' 
            : disabled || uploading
            ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }
        `}
      >
        <input {...getInputProps()} />
        
        <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
        
        <div className="mt-4">
          <p className="text-sm font-medium text-gray-900">
            {isDragActive 
              ? 'Drop the files here...'
              : uploading 
              ? 'Uploading files...'
              : 'Drop files here, or click to select'
            }
          </p>
          <p className="text-xs text-gray-500 mt-1">
            PDF, DOC, DOCX, TXT, CSV, XLS, XLSX up to 50MB each
          </p>
        </div>

        {uploading && (
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-lg">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-sm text-gray-600 mt-2">Uploading...</p>
            </div>
          </div>
        )}
      </div>

      {/* Upload Progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="mt-4 space-y-2">
          {Object.entries(uploadProgress).map(([fileName, progress]) => (
            <div key={fileName} className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 truncate">
                  {fileName}
                </span>
                {progress.status === 'completed' && (
                  <CheckCircleIcon className="w-4 h-4 text-green-600" />
                )}
                {progress.status === 'failed' && (
                  <ExclamationTriangleIcon className="w-4 h-4 text-red-600" />
                )}
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full transition-all duration-300 ${
                    progress.status === 'completed' ? 'bg-green-500' :
                    progress.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${progress.progress}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-medium text-gray-900 mb-3">
            Uploaded Documents ({uploadedFiles.length})
          </h4>
          <div className="space-y-2">
            {uploadedFiles.map((file, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center space-x-3">
                  <span className="text-lg">
                    {getFileIcon(file.type)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(file.size)} " Uploaded {file.uploadedAt.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="ml-2 text-gray-400 hover:text-gray-600 transition-colors duration-200"
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Help Text */}
      <div className="mt-4 text-xs text-gray-500">
        <p>
          <strong>Supported formats:</strong> PDF documents, Word documents (.doc, .docx), 
          text files (.txt), spreadsheets (.xls, .xlsx, .csv)
        </p>
        <p className="mt-1">
          <strong>Note:</strong> Documents will be processed by OpenAI for analysis. 
          Ensure you have permission to upload these files.
        </p>
      </div>
    </div>
  );
};

export default DocumentUpload;