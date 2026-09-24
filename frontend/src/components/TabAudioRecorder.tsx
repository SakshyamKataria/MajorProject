import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Volume2, Square, AlertCircle, RefreshCw, CheckCircle2, Play, Pause, Radio } from 'lucide-react';

interface TabAudioRecorderProps {
  onRecordingComplete: (file: File) => void;
  disabled?: boolean;
}

export const TabAudioRecorder: React.FC<TabAudioRecorderProps> = ({ onRecordingComplete, disabled }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [recordedFile, setRecordedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState<number>(0);

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const cleanupAudioNodes = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  }, []);

  const stopAllMediaTracks = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // ignore
        }
      });
      mediaStreamRef.current = null;
    }
  }, []);

  const handleStopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    cleanupAudioNodes();

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    } else {
      setIsRecording(false);
      stopAllMediaTracks();
    }
  }, [cleanupAudioNodes, stopAllMediaTracks]);

  const startTabCapture = async () => {
    setError(null);
    audioChunksRef.current = [];

    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      setError('Screen & Tab audio capture is not supported in this browser. Please use Chrome, Edge, or Brave.');
      return;
    }

    try {
      // Prompt browser tab/window picker with audio capture enabled
      const displayStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true,
      });

      // Check for audio track
      const audioTracks = displayStream.getAudioTracks();
      if (audioTracks.length === 0) {
        // User picked a window or forgot to check 'Also share tab audio'
        displayStream.getTracks().forEach((t) => t.stop());
        setError(
          "No audio stream detected. When picking your browser tab, please make sure 'Also share tab audio' is checked."
        );
        return;
      }

      // Stop video track immediately to save CPU/GPU memory - we only need tab audio!
      displayStream.getVideoTracks().forEach((vt) => {
        try {
          vt.stop();
        } catch {
          // ignore
        }
      });

      // Build dedicated audio-only stream
      const audioStream = new MediaStream(audioTracks);
      mediaStreamRef.current = audioStream;

      // Handle user stopping share from browser floating toolbar
      audioTracks[0].onended = () => {
        if (isRecording) {
          handleStopRecording();
        }
      };

      // Set up Web Audio Analyser for live visual feedback
      try {
        const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const audioCtx = new AudioCtx();
        audioContextRef.current = audioCtx;
        const sourceNode = audioCtx.createMediaStreamSource(audioStream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        sourceNode.connect(analyser);
        analyserRef.current = analyser;

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const updateLevel = () => {
          if (analyserRef.current) {
            analyserRef.current.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const avg = sum / dataArray.length;
            setAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
            animFrameRef.current = requestAnimationFrame(updateLevel);
          }
        };
        updateLevel();
      } catch (audioErr) {
        console.warn('AudioContext visualizer initialization skipped:', audioErr);
      }

      // Select supported MediaRecorder mimeType
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
      ];
      let selectedMimeType = '';
      for (const m of mimeTypes) {
        if (MediaRecorder.isTypeSupported(m)) {
          selectedMimeType = m;
          break;
        }
      }

      const recorder = selectedMimeType
        ? new MediaRecorder(audioStream, { mimeType: selectedMimeType })
        : new MediaRecorder(audioStream);

      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        stopAllMediaTracks();
        setIsRecording(false);

        const mime = selectedMimeType || 'audio/webm';
        const blob = new Blob(audioChunksRef.current, { type: mime });
        if (blob.size === 0) {
          setError('Recorded audio buffer was empty. Please check if audio was playing in the tab.');
          return;
        }

        const now = new Date();
        const pad = (n: number) => n.toString().padStart(2, '0');
        const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}`;
        const fileName = `Tab_Recording_${timestamp}.webm`;
        const file = new File([blob], fileName, { type: mime });

        setRecordedFile(file);
        const objectUrl = URL.createObjectURL(blob);
        setPreviewUrl(objectUrl);
        onRecordingComplete(file);
      };

      // Start recording with 500ms timeSlice chunks for safe data flushing
      recorder.start(500);
      setIsRecording(true);
      setDuration(0);

      timerRef.current = window.setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    } catch (err: unknown) {
      cleanupAudioNodes();
      stopAllMediaTracks();
      const errName = err instanceof Error ? err.name : '';
      if (errName === 'NotAllowedError' || errName === 'AbortError') {
        return;
      }
      setError(err instanceof Error ? err.message : 'Could not initialize tab capture.');
    }
  };

  const handleReset = () => {
    handleStopRecording();
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    setRecordedFile(null);
    setDuration(0);
    setError(null);
    setIsPlaying(false);
  };

  const togglePlayback = () => {
    if (!audioPlayerRef.current) return;
    if (isPlaying) {
      audioPlayerRef.current.pause();
      setIsPlaying(false);
    } else {
      audioPlayerRef.current.play().catch(() => setIsPlaying(false));
      setIsPlaying(true);
    }
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      cleanupAudioNodes();
      stopAllMediaTracks();
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [cleanupAudioNodes, stopAllMediaTracks, previewUrl]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full space-y-4">
      {!isRecording && !recordedFile && (
        <div className="relative border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-200 flex flex-col items-center justify-center min-h-[220px] border-slate-800 bg-slate-900/50 hover:border-slate-700">
          <div className="p-4 rounded-2xl bg-indigo-500/10 text-indigo-400 mb-3 border border-indigo-500/20">
            <Radio className="w-8 h-8" />
          </div>

          <h3 className="text-base font-semibold text-slate-100 mb-1">
            Record Live Audio from Browser Tab
          </h3>

          <p className="text-xs text-slate-400 max-w-sm mb-5 leading-relaxed">
            Capture sound from a YouTube lecture, Google Meet, webinar, or podcast tab directly into Whisper & Gemini.
          </p>

          <button
            type="button"
            onClick={startTabCapture}
            disabled={disabled}
            className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-all hover:scale-[1.02] cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Radio className="w-4 h-4 text-rose-300 animate-pulse" />
            Select Tab & Start Recording
          </button>

          <p className="text-[11px] text-slate-500 mt-3">
            Make sure to check <span className="text-indigo-400 font-medium">'Also share tab audio'</span> in the browser popup.
          </p>
        </div>
      )}

      {/* Recording in Progress State */}
      {isRecording && (
        <div className="p-6 rounded-2xl bg-slate-900/90 border border-rose-500/30 shadow-2xl space-y-5 animate-in fade-in duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center">
                <div className="w-3 h-3 rounded-full bg-rose-500 animate-ping absolute" />
                <div className="w-3 h-3 rounded-full bg-rose-500 relative" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-100">Recording Tab Audio...</h4>
                <p className="text-xs text-slate-400">Capturing active audio stream</p>
              </div>
            </div>
            <div className="font-mono text-lg font-bold text-rose-400 px-3 py-1 rounded-lg bg-rose-500/10 border border-rose-500/20">
              {formatTime(duration)}
            </div>
          </div>

          {/* Sound Meter / Visualizer */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[11px] text-slate-400">
              <span className="inline-flex items-center gap-1.5">
                <Volume2 className="w-3.5 h-3.5 text-indigo-400" /> Audio Activity Level
              </span>
              <span className="font-mono">{audioLevel}%</span>
            </div>
            <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 via-emerald-400 to-rose-400 rounded-full transition-all duration-75"
                style={{ width: `${Math.max(4, audioLevel)}%` }}
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleStopRecording}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/20 transition-all hover:scale-[1.02] cursor-pointer"
            >
              <Square className="w-3.5 h-3.5 fill-current" /> Stop Recording
            </button>
          </div>
        </div>
      )}

      {/* Recorded File Ready State */}
      {recordedFile && (
        <div className="p-5 rounded-2xl bg-slate-900 border border-emerald-500/30 space-y-4 animate-in fade-in duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex-shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div className="truncate">
                <h4 className="text-sm font-semibold text-slate-100 truncate">{recordedFile.name}</h4>
                <p className="text-xs text-slate-400 font-mono">
                  {(recordedFile.size / (1024 * 1024)).toFixed(2)} MB • {formatTime(duration)} captured
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleReset}
              disabled={disabled}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className="w-3 h-3" /> Record Again
            </button>
          </div>

          {/* Audio Preview Player */}
          {previewUrl && (
            <div className="flex items-center gap-3 bg-slate-950/80 p-3 rounded-xl border border-slate-800">
              <button
                type="button"
                onClick={togglePlayback}
                className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-all cursor-pointer flex-shrink-0"
                title={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
              </button>
              <div className="flex-1 text-xs text-slate-400">
                <p className="font-medium text-slate-200">Preview Tab Recording</p>
                <p className="text-[11px]">Listen back to verify clarity before AI processing</p>
              </div>
              <audio
                ref={audioPlayerRef}
                src={previewUrl}
                onEnded={() => setIsPlaying(false)}
                className="hidden"
              />
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="flex items-start space-x-2.5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};
