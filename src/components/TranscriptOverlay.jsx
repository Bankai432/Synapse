import { useEffect } from "react";
import { playConfidenceTick } from "../sounds.js";

export default function TranscriptOverlay({ history, onClose }) {
  // ESC to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="absolute inset-0 z-50 flex justify-end animate-[fadeIn_0.4s_cubic-bezier(0.25,1,0.5,1)]">
      
      {/* Backdrop (click to close) */}
      <div 
        className="absolute inset-0 bg-black/20 dark:bg-black/60 backdrop-blur-sm cursor-pointer" 
        onClick={() => { playConfidenceTick(); onClose(); }} 
      />

      {/* Drawer Panel */}
      <div className="relative w-full md:w-[600px] h-full bg-white/75 dark:bg-[#050505]/95 backdrop-blur-3xl shadow-[-20px_0_60px_-15px_rgba(0,0,0,0.5)] border-l border-black/10 dark:border-white/10 flex flex-col pointer-events-auto transition-transform duration-700 ease-[cubic-bezier(0.25,1,0.5,1)]">
        
        {/* Header */}
        <div className="flex-shrink-0 flex items-center justify-between px-8 py-8 border-b border-black/5 dark:border-white/5">
          <div className="flex flex-col gap-1">
            <h2 className="font-tactical text-xl font-bold text-black dark:text-white uppercase tracking-widest">
              Session Transcript
            </h2>
            <span className="font-tactical text-[10px] uppercase text-gray-500 tracking-[0.25em]">
              Historical Logs
            </span>
          </div>
          <button 
            onClick={() => { playConfidenceTick(); onClose(); }}
            className="w-10 h-10 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center hover:bg-black/10 dark:hover:bg-white/10 transition-colors text-black dark:text-white"
          >
            ✕
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-8 py-8 flex flex-col gap-12 no-scrollbar">
          {history.length === 0 ? (
            <div className="flex items-center justify-center h-full text-center">
              <span className="font-tactical text-[11px] uppercase tracking-[0.2em] text-gray-400">
                No active history.
              </span>
            </div>
          ) : (
            history.map((turn) => {
              const hasUpdates = turn.conceptUpdates && turn.conceptUpdates.length > 0;
              const totalMasteryDelta = turn.conceptUpdates?.reduce((sum, u) => sum + (u.masteryDelta || 0), 0) || 0;
              
              return (
              <details key={turn.id} className="group flex flex-col mb-4">
                
                {/* ── Compressed Summary ── */}
                <summary onClick={() => playConfidenceTick()} className="flex items-center justify-between cursor-pointer outline-none select-none list-none px-5 py-3.5 rounded-xl transition-colors bg-black/[0.02] dark:bg-white/[0.015] border border-black/5 dark:border-white/5 hover:bg-black/[0.04] dark:hover:bg-white/[0.03]">
                  <div className="flex items-center justify-between w-full pr-6">
                    <div className="flex items-center gap-3 truncate min-w-0">
                      <span className="font-tactical text-[11px] font-bold text-black dark:text-white flex-shrink-0">
                        Q.{String(turn.id).padStart(2, "0")}
                      </span>
                      <span className="font-tactical text-[9px] uppercase tracking-[0.2em] text-gray-500 flex-shrink-0">
                        {turn.questionType || "EXPLORATION"}
                      </span>
                      {hasUpdates && (
                        <div className="flex items-center gap-2 min-w-0 truncate ml-1">
                          <div className="w-px h-2.5 bg-black/20 dark:bg-white/20 flex-shrink-0" />
                          <span className="font-tactical text-[8px] uppercase tracking-widest text-blue-600 dark:text-blue-400 truncate">
                            {turn.conceptUpdates.map(u => u.id).join(", ")}
                          </span>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-5">
                      <span className="font-tactical text-[9px] uppercase tracking-widest text-gray-400">
                        Conf: <span className="font-bold text-gray-800 dark:text-gray-200">{turn.confidence}%</span>
                      </span>
                      {totalMasteryDelta > 0 ? (
                         <span className="font-tactical text-[10px] font-bold text-green-600 dark:text-green-500">
                           + {totalMasteryDelta.toFixed(1)}% Gain
                         </span>
                      ) : (
                         <span className="font-tactical text-[9px] uppercase tracking-widest text-gray-400">
                           0.0% Gain
                         </span>
                      )}
                    </div>
                  </div>
                  <span className="font-tactical text-[10px] text-gray-400 group-open:rotate-180 transition-transform duration-300 transform origin-center flex-shrink-0">
                    ▼
                  </span>
                </summary>

                {/* ── Expanded Content ── */}
                <div className="flex flex-col gap-5 pt-8 pb-4 px-4 bg-transparent animate-[fadeIn_0.3s_ease-out]">
                  
                  {/* Tutor Row */}
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                      <span className="font-tactical text-[9px] uppercase tracking-[0.25em] text-gray-500">
                        Tutor Feedback & Next Query
                      </span>
                    </div>
                    <p className="font-voice text-[1.2rem] md:text-[1.4rem] text-black dark:text-gray-100 italic leading-snug ml-4">
                      {turn.question}
                    </p>
                  </div>

                  {/* User Row */}
                  <div className="flex flex-col gap-2 ml-4">
                    <div className="flex justify-between items-center">
                      <span className="font-tactical text-[9px] uppercase tracking-[0.25em] text-gray-700 dark:text-gray-400">
                        You
                      </span>
                      <span className="font-tactical text-[9px] uppercase tracking-widest text-gray-400">
                        Conf: {turn.confidence}%
                      </span>
                    </div>
                    <div className="bg-black/5 dark:bg-white/5 rounded-2xl px-5 py-4">
                      <p className="font-tactical font-light text-[0.95rem] leading-relaxed text-black dark:text-gray-200">
                        {turn.userInput || "— No input provided —"}
                      </p>
                    </div>
                  </div>

                  {/* Feedback Row */}
                  {(turn.gap || hasUpdates) && (
                    <div className="flex flex-col gap-2 ml-4 mt-2">
                      <span className="font-tactical text-[9px] uppercase tracking-[0.25em] text-gray-500">
                        System Analysis
                      </span>
                      <div className="border-l-2 border-black/10 dark:border-white/10 pl-4 py-1">
                        {turn.gap && (
                          <span className="font-tactical text-[0.85rem] leading-relaxed text-gray-700 dark:text-gray-400 mb-3 block">
                            {turn.gap}
                          </span>
                        )}
                        
                        {hasUpdates && (
                          <div className="flex flex-wrap gap-2">
                            {turn.conceptUpdates.map(u => {
                              const positive = u.masteryDelta > 0;
                              return (
                                <span key={u.id} className={`font-tactical text-[8px] uppercase tracking-widest px-2 py-1 rounded-sm ${
                                  positive 
                                    ? "bg-green-500/10 text-green-700 dark:text-green-400" 
                                    : "bg-black/5 dark:bg-white/5 text-gray-700 dark:text-gray-500"
                                }`}>
                                  {u.id} {positive ? "+" : ""}{(u.masteryDelta||0).toFixed(1)}%
                                </span>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                </div>
              </details>
            )})
          )}
        </div>
      </div>
    </div>
  );
}
