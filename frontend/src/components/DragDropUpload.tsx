import React, { useRef, useState, useCallback } from 'react';
import { UploadCloud, FileAudio, AlertCircle, X } from 'lucide-react';

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
      setErrorMessage(`Unsupported format (${ext}). Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`);
      return;
    }

    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > MAX_FILE_SIZE_MB) {
      setErrorMessage(`File exceeds max size of ${MAX_FILE_SIZE_MB}MB (${fileSizeMB.toFixed(1)}MB).`);
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
    <div className="w-full space-y-3">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-200 cursor-pointer flex flex-col items-center justify-center min-h-[220px] ${
          isDragOver
            ? 'border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/10 scale-[1.01]'
            : 'border-slate-800 bg-slate-900/50 hover:bg-slate-900/80 hover:border-slate-700'
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

        <div className="p-4 rounded-2xl bg-indigo-500/10 text-indigo-400 mb-3 border border-indigo-500/20">
          <UploadCloud className="w-8 h-8" />
        </div>

        <h3 className="text-base font-semibold text-slate-100 mb-1">
          {isDragOver ? 'Drop audio file here' : 'Click to browse or drag & drop'}
        </h3>
        
        <p className="text-xs text-slate-400 max-w-sm mb-3 leading-relaxed">
          Upload recorded meetings, lectures, or conference discussions. Supported formats: MP3, WAV, M4A, MP4, AAC, FLAC (up to 150MB).
        </p>

        <div className="flex flex-wrap items-center justify-center gap-1.5 text-[11px] text-slate-500">
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">.mp3</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">.wav</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">.m4a</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">.mp4</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">.webm</span>
        </div>
      </div>

      {selectedFile && (
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 text-sm">
          <div className="flex items-center space-x-3 overflow-hidden">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 flex-shrink-0">
              <FileAudio className="w-4 h-4" />
            </div>
            <div className="truncate">
              <p className="font-medium text-slate-100 truncate">{selectedFile.name}</p>
              <p className="text-xs text-slate-400">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
            </div>
          </div>
          {!disabled && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                clearFile();
              }}
              className="p-1 hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-200 transition-colors"
              title="Remove file"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="flex items-start space-x-2.5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
};
