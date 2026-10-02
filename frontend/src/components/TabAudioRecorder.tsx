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
    <div className="w-full space-y-3">
      {!isRecording && !recordedFile && (
        <div className="border border-dashed border-[#242b3e] rounded-lg p-6 sm:p-7 text-center transition-colors bg-[#0d0f16] hover:border-[#333d57] flex flex-col items-center justify-center">
          <div className="w-9 h-9 rounded bg-[#151824] text-[#8e9cb5] flex items-center justify-center mb-3 border border-[#22283a]">
            <Radio className="w-4 h-4 text-blue-400" />
          </div>

          <h3 className="text-xs sm:text-sm font-medium text-[#edf1f8] mb-1">
            Capture Audio from Browser Tab
          </h3>

          <p className="text-xs text-[#7e8ba2] max-w-sm mb-4 leading-relaxed">
            Record meeting audio directly from a Google Meet, Zoom web, YouTube, or webinar tab.
          </p>

          <button
            type="button"
            onClick={startTabCapture}
            disabled={disabled}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded text-xs font-medium bg-[#1e2538] hover:bg-[#273048] text-white border border-[#303c5a] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Radio className="w-3.5 h-3.5 text-blue-400" />
            Select Tab & Begin Capture
          </button>

          <p className="text-[11px] text-[#5e6b83] mt-3">
            Ensure you enable <span className="text-[#a0afca]">"Also share tab audio"</span> in the browser prompt.
          </p>
        </div>
      )}

      {/* Recording in Progress State */}
      {isRecording && (
        <div className="p-4 sm:p-5 rounded-lg bg-[#11131b] border border-[#3b1d24] space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#1f2230]">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500" />
              </span>
              <div>
                <h4 className="text-xs sm:text-sm font-medium text-[#edf1f8]">Recording Tab Audio</h4>
                <p className="text-[11px] text-[#78859e]">Capturing active stream</p>
              </div>
            </div>

            <div className="font-mono text-sm font-medium text-rose-400 px-2.5 py-1 rounded bg-[#221015] border border-[#3d1921] tabular-nums">
              {formatTime(duration)}
            </div>
          </div>

          {/* Sound Meter */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[11px] text-[#6d7a94] font-mono">
              <span className="inline-flex items-center gap-1.5">
                <Volume2 className="w-3 h-3 text-[#58647d]" /> Signal Level
              </span>
              <span className="tabular-nums">{audioLevel}%</span>
            </div>
            <div className="w-full h-1.5 bg-[#0b0c11] rounded-full overflow-hidden border border-[#1a1f2e]">
              <div
                className="h-full bg-blue-500 transition-all duration-75"
                style={{ width: `${Math.max(2, audioLevel)}%` }}
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={handleStopRecording}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-[#291217] hover:bg-[#381820] text-rose-300 border border-[#481c25] transition-colors cursor-pointer"
            >
              <Square className="w-3 h-3 fill-current" /> Stop Recording
            </button>
          </div>
        </div>
      )}

      {/* Recorded File Ready State */}
      {recordedFile && (
        <div className="p-4 rounded-lg bg-[#10131d] border border-[#1b2d24] space-y-3">
          <div className="flex items-center justify-between pb-2.5 border-b border-[#182126]">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-7 h-7 rounded bg-[#10241b] text-emerald-400 border border-[#1b3d2d] flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="truncate">
                <h4 className="text-xs sm:text-sm font-medium text-[#edf1f8] truncate">{recordedFile.name}</h4>
                <p className="text-[11px] text-[#71809a] font-mono tabular-nums">
                  {(recordedFile.size / (1024 * 1024)).toFixed(2)} MB • {formatTime(duration)} captured
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleReset}
              disabled={disabled}
              className="text-xs px-2.5 py-1 rounded bg-[#161a26] hover:bg-[#1d2232] text-[#8e9cb5] border border-[#232a3d] flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className="w-3 h-3" /> Retake
            </button>
          </div>

          {/* Audio Preview Player */}
          {previewUrl && (
            <div className="flex items-center gap-3 bg-[#0c0d13] p-2.5 rounded border border-[#1b202e]">
              <button
                type="button"
                onClick={togglePlayback}
                className="w-7 h-7 rounded bg-[#1f2639] hover:bg-[#29324b] text-[#e2e8f5] border border-[#313c59] transition-colors cursor-pointer flex items-center justify-center shrink-0"
                title={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current ml-0.5" />}
              </button>
              <div className="flex-1 text-xs text-[#718099] min-w-0">
                <p className="font-medium text-[#d3dceb] text-xs truncate">Preview Tab Audio</p>
                <p className="text-[11px] text-[#5e6b83]">Verify sound clarity before pipeline processing</p>
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
        <div className="flex items-start gap-2 p-3 rounded bg-[#241115] border border-[#441a22] text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};
