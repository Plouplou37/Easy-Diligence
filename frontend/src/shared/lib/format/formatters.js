export const formatBytes = bytes => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const getExpirationStatus = expiresAt => {
  if (!expiresAt) return 'never';
  const now = new Date();
  const expiry = new Date(expiresAt);
  const diffTime = expiry - now;
  const diffDays = diffTime / (1000 * 60 * 60 * 24);

  if (diffDays <= 0) return 'expired';
  if (diffDays <= 3) return 'critical';
  if (diffDays <= 7) return 'warning';
  return 'normal';
};

/** A duration in seconds, short: "45s", "3m 20s", "1h 5m". */
export const formatDuration = seconds => {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
};

/** Save a downloaded blob under a file name. */
export const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

/** How long ago `iso` was, briefly ("5 min ago"), then the date after a week. */
export const formatRelative = iso => {
  if (!iso) return '—';
  const date = new Date(iso);
  const minutes = Math.round((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} d ago`;
  return date.toLocaleDateString();
};
