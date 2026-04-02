import { useState } from "react";
import { motion } from "motion/react";
import { FileUpload } from "../features/files/components/FileUpload";
import { FileList } from "../features/files/components/FileList";
import { GcsSetupGuide } from "../features/files/components/GcsSetupGuide";
import { FileStorageHeader } from "../features/files/components/FileStorageHeader";
import { GcsBucketInfo } from "../features/files/components/GcsBucketInfo";
import { useFileStorage } from "../features/files/hooks/useFileStorage";
import { LoadingSpinner } from "../shared/components/LoadingSpinner";
import { ErrorMessage } from "../shared/components/ErrorMessage";
import { NotificationToast } from "../shared/components/notifications/NotificationToast";

export function FileUploadPage() {
  const {
    gcsConfigured,
    gcsBucketName,
    loading,
    stats,
    authError,
    defaultBucketId,
    notification,
    setNotification,
    checkGcsAndInitialize,
    handleUploadComplete,
    handleFileDelete,
  } = useFileStorage();

  const [refreshKey, setRefreshKey] = useState(0);

  const onUploadComplete = () => {
    handleUploadComplete();
    setRefreshKey((prev) => prev + 1);
  };

  const onFileDelete = () => {
    handleFileDelete();
    setRefreshKey((prev) => prev + 1);
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!gcsConfigured && window.location.hostname === "localhost") {
    return <GcsSetupGuide onRetryCheck={checkGcsAndInitialize} />;
  }

  if (authError) {
    return <ErrorMessage title="Authentication Required" message={authError} />;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {notification && (
        <NotificationToast
          type={notification.type}
          message={notification.message}
          onDismiss={() => setNotification(null)}
        />
      )}

      <FileStorageHeader stats={stats} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {gcsBucketName && <GcsBucketInfo bucketName={gcsBucketName} />}

        {defaultBucketId && (
          <>
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mb-6"
            >
              <FileUpload
                bucketId={defaultBucketId}
                maxFileSize={50 * 1024 * 1024} // 50MB
                onUploadComplete={onUploadComplete}
              />
            </motion.div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow dark:shadow-gray-900/50">
              <FileList
                key={refreshKey}
                bucketId={defaultBucketId}
                onFileDelete={onFileDelete}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
