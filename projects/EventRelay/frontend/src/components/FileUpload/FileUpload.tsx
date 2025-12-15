import React, { useState, useCallback } from 'react';

const FileUpload: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('video', selectedFile);

    try {
      // Replace with your actual API endpoint
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('File upload failed');
      }

      // Handle successful upload
      console.log('File uploaded successfully');
    } catch (err: any) {
      setUploadError(err.message);
    } finally {
      setIsUploading(false);
    }
  }, [selectedFile]);

  return (
    <div className="p-4 border-dashed border-2 border-gray-300 rounded-lg">
      <input type="file" accept=".mp4,.mov,.avi" onChange={handleFileChange} className="mb-4" />
      <button
        onClick={handleUpload}
        disabled={!selectedFile || isUploading}
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:bg-gray-400"
      >
        {isUploading ? 'Uploading...' : 'Upload Video'}
      </button>
      {uploadError && <p className="text-red-500 mt-2">{uploadError}</p>}
    </div>
  );
};

export default FileUpload;
