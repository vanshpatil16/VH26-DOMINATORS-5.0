import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Volume2, VolumeX, ArrowRight, Play } from "lucide-react";

interface VideoIntroProps {
  onComplete: () => void;
  videoSrc?: string;
}

export default function VideoIntro({
  onComplete,
  videoSrc = "/landing_video.mp4",
}: VideoIntroProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isMuted, setIsMuted] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // Try playing video automatically
    const playPromise = video.play();
    if (playPromise !== undefined) {
      playPromise
        .then(() => {
          setIsPlaying(true);
        })
        .catch((error) => {
          console.warn("Autoplay blocked or failed:", error);
          setIsPlaying(false);
        });
    }
  }, []);

  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (video && video.duration) {
      setProgress((video.currentTime / video.duration) * 100);
    }
  };

  const handleFinish = () => {
    if (isExiting) return;
    setIsExiting(true);
    setTimeout(() => {
      onComplete();
    }, 600); // Allow fade-out duration
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handlePlayManual = () => {
    if (videoRef.current) {
      videoRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => console.error("Manual play error:", err));
    }
  };

  return (
    <AnimatePresence>
      {!isExiting && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.02 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black overflow-hidden select-none"
        >
          {/* Video Player */}
          <video
            ref={videoRef}
            src={videoSrc}
            autoPlay
            muted={isMuted}
            playsInline
            onTimeUpdate={handleTimeUpdate}
            onEnded={handleFinish}
            onError={(e) => {
              console.error("Video load error:", e);
              handleFinish();
            }}
            className="w-full h-full object-cover object-center"
          />

          {/* Top Bar with Controls */}
          <div className="absolute top-6 left-6 right-6 flex items-center justify-between pointer-events-auto z-10">
            <div className="flex items-center space-x-3 bg-black/40 backdrop-blur-md px-3.5 py-1.5 rounded-full border border-white/10">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-mono tracking-widest text-zinc-300 uppercase">
                INTRO PREVIEW
              </span>
            </div>

            <div className="flex items-center space-x-3">
              {/* Sound Toggle */}
              <button
                onClick={toggleMute}
                className="flex items-center space-x-2 bg-black/40 hover:bg-black/70 backdrop-blur-md text-zinc-300 hover:text-white px-3.5 py-1.5 rounded-full border border-white/10 hover:border-white/20 transition-all text-xs font-mono"
                title={isMuted ? "Unmute sound" : "Mute sound"}
              >
                {isMuted ? (
                  <>
                    <VolumeX className="w-3.5 h-3.5 text-zinc-400" />
                    <span>MUTED</span>
                  </>
                ) : (
                  <>
                    <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>SOUND ON</span>
                  </>
                )}
              </button>

              {/* Skip Button */}
              <button
                onClick={handleFinish}
                className="group flex items-center space-x-2 bg-white/10 hover:bg-white/20 backdrop-blur-md text-white px-4 py-1.5 rounded-full border border-white/20 hover:border-white/40 transition-all text-xs font-mono tracking-wide"
              >
                <span>SKIP INTRO</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
              </button>
            </div>
          </div>

          {/* Center Play Button if Autoplay was blocked */}
          {!isPlaying && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-xs z-20">
              <button
                onClick={handlePlayManual}
                className="flex items-center space-x-3 bg-white text-black px-6 py-3 rounded-full font-medium shadow-2xl hover:scale-105 transition-all cursor-pointer"
              >
                <Play className="w-5 h-5 fill-black" />
                <span>Play Intro Video</span>
              </button>
            </div>
          )}

          {/* Bottom Progress Bar */}
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/10 z-10">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 transition-all duration-150 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
