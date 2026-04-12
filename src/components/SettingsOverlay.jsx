// ──────────────────────────────────────────────────────────────
// SettingsOverlay — Floating settings panel
//
// Props:
//   isDarkMode      boolean
//   setIsDarkMode   fn
//   accentColor     string ("blue" | "emerald" | "purple" | "rose")
//   setAccentColor  fn
//   showLabels      boolean
//   setShowLabels   fn
//   onClose         fn
// ──────────────────────────────────────────────────────────────
import { playConfidenceTick, playAttach } from "../sounds.js";

const ACCENT_COLORS = [
  { key: "blue",    label: "Blue",    dot: "bg-blue-500" },
  { key: "emerald", label: "Emerald", dot: "bg-emerald-500" },
  { key: "purple",  label: "Purple",  dot: "bg-purple-500" },
  { key: "rose",    label: "Rose",    dot: "bg-rose-500" },
];

export default function SettingsOverlay({
  isDarkMode,
  setIsDarkMode,
  accentColor,
  setAccentColor,
  showLabels,
  setShowLabels,
  onClose,
}) {
  return (
    <div className="absolute top-8 right-8 z-50 bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-3xl border border-black/5 dark:border-white/5 p-6 w-80 luxury-shadow-light dark:luxury-shadow-dark rounded-3xl pointer-events-auto animate-[fadeIn_0.5s_cubic-bezier(0.25,1,0.5,1)]">
      <div className="flex justify-between items-center mb-6">
        <h3 className="font-mono text-[10px] font-bold tracking-[0.2em] text-gray-400 uppercase">
          System Settings
        </h3>
        <button
          onClick={() => { playConfidenceTick(); onClose(); }}
          className="text-gray-400 hover:text-black dark:hover:text-white transition-colors duration-500"
          aria-label="Close settings"
        >
          ✕
        </button>
      </div>

      <div className="space-y-6">
        {/* Interface Mode */}
        <div className="flex justify-between items-center">
          <span className="font-sans text-sm tracking-wide text-gray-800 dark:text-gray-200">
            Interface Mode
          </span>
          <button
            onClick={() => { playAttach(); setIsDarkMode(!isDarkMode); }}
            className="font-mono text-[10px] border border-black/10 dark:border-white/10 px-4 py-1.5 rounded-full hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-all duration-500 ease-out uppercase tracking-widest"
          >
            {isDarkMode ? "Light" : "Dark"}
          </button>
        </div>

        {/* Semantic Labels */}
        <div className="flex justify-between items-center">
          <span className="font-sans text-sm tracking-wide text-gray-800 dark:text-gray-200">
            Semantic Labels
          </span>
          <button
            onClick={() => { playAttach(); setShowLabels(!showLabels); }}
            className="font-mono text-[10px] border border-black/10 dark:border-white/10 px-4 py-1.5 rounded-full hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-all duration-500 ease-out uppercase tracking-widest"
          >
            {showLabels ? "Always" : "Hover"}
          </button>
        </div>

        {/* Accent Color */}
        <div className="flex flex-col gap-3">
          <span className="font-sans text-sm tracking-wide text-gray-800 dark:text-gray-200">
            Accent Colour
          </span>
          <div className="flex gap-3">
            {ACCENT_COLORS.map(({ key, label, dot }) => (
              <button
                key={key}
                onClick={() => { playConfidenceTick(); setAccentColor(key); }}
                title={label}
                className={`w-7 h-7 rounded-full ${dot} transition-all duration-300 ${
                  accentColor === key
                    ? "ring-2 ring-offset-2 ring-offset-white dark:ring-offset-black ring-current scale-110"
                    : "opacity-50 hover:opacity-100"
                }`}
                aria-label={`Set ${label} accent`}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
