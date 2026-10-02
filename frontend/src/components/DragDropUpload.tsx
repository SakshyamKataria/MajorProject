import React, { useRef, useState, useCallback } from 'react';
import { Upload, FileAudio, AlertCircle, X } from 'lucide-react';

interface DragDropUploadProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

const ALLOWED_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.mp4', '.ogg', '.webm', '.mov', '.aac', '.flac'];
const MAX_FILE_SIZE_MB = 150;

export const DragDropUpload: React.FC<DragDropUploadProps> = ({ onFileSelect, disabled }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndHandleFile = useCallback((file: File) => {
    setErrorMessage(null);
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setErrorMessage(`Unsupported format (${ext}). Supported: ${ALLOWED_EXTENSIONS.join(', ')}`);
      return;
    }

    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > MAX_FILE_SIZE_MB) {
      setErrorMessage(`File exceeds maximum size of ${MAX_FILE_SIZE_MB}MB (${fileSizeMB.toFixed(1)}MB).`);
      return;
    }

    if (file.size === 0) {
      setErrorMessage('Selected file is empty (0 bytes).');
      return;
    }

    setSelectedFile(file);
    onFileSelect(file);
  }, [onFileSelect]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      validateAndHandleFile(file);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndHandleFile(e.target.files[0]);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setErrorMessage(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="w-full space-y-2.5">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`border border-dashed rounded-lg p-6 sm:p-8 text-center transition-colors cursor-pointer flex flex-col items-center justify-center min-h-[190px] ${
          isDragOver
            ? 'border-blue-500 bg-[#121826]'
            : 'border-[#262c3e] bg-[#0c0d14] hover:bg-[#10121b] hover:border-[#353d54]'
        } ${disabled ? 'opacity-60 cursor-not-allowed' : ''}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_EXTENSIONS.join(',')}
          className="hidden"
          disabled={disabled}
          onChange={handleInputChange}
        />

        <div className="w-9 h-9 rounded bg-[#161a26] border border-[#242b3e] text-[#8694ad] flex items-center justify-center mb-2.5">
          <Upload className="w-4 h-4 text-blue-400" />
        </div>

        <h3 className="text-xs sm:text-sm font-medium text-[#edf1f8] mb-1">
          {isDragOver ? 'Drop audio recording to upload' : 'Click to select or drag and drop audio file'}
        </h3>
        
        <p className="text-xs text-[#717e97] max-w-sm mb-3 leading-relaxed">
          Supports meeting recordings, board sessions, and team discussions up to 150MB.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-1 text-[11px] text-[#5e6b83] font-mono">
          <span className="px-1.5 py-0.5 rounded bg-[#131622] border border-[#1e2334]">.mp3</span>
          <span className="px-1.5 py-0.5 rounded bg-[#131622] border border-[#1e2334]">.wav</span>
          <span className="px-1.5 py-0.5 rounded bg-[#131622] border border-[#1e2334]">.m4a</span>
          <span className="px-1.5 py-0.5 rounded bg-[#131622] border border-[#1e2334]">.mp4</span>
          <span className="px-1.5 py-0.5 rounded bg-[#131622] border border-[#1e2334]">.webm</span>
        </div>
      </div>

      {selectedFile && (
        <div className="flex items-center justify-between p-3 rounded bg-[#11131b] border border-[#1f2434] text-xs">
          <div className="flex items-center space-x-2.5 overflow-hidden">
            <FileAudio className="w-4 h-4 text-blue-400 shrink-0" />
            <div className="truncate">
              <p className="font-medium text-[#edf1f8] truncate">{selectedFile.name}</p>
              <p className="text-[11px] text-[#717e97] font-mono tabular-nums">
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
              </p>
            </div>
          </div>
          {!disabled && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                clearFile();
              }}
              className="p-1 hover:bg-[#1a1f2e] rounded text-[#6c7891] hover:text-[#d3dbe9] transition-colors cursor-pointer"
              title="Remove file"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="flex items-center gap-1.5 text-xs text-rose-400 p-2.5 rounded bg-[#241113] border border-[#441a1f]">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
};
