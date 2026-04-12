import { useState, useEffect, useMemo, useRef } from "react";
import AnalyticalGraph from "./components/AnalyticalGraph";
import SettingsOverlay from "./components/SettingsOverlay";
import TranscriptOverlay from "./components/TranscriptOverlay";
import Typewriter from "./components/Typewriter";
import { EvaluationAPI } from "./api.js";
import {
  playSubmit,
  playQuestionAppear,
  playUnlock,
  playRecordingStart,
  playRecordingStop,
  playConfidenceTick,
  playAttach,
  playError,
} from "./sounds.js";

// ── Question type display labels ──────────────────────────────
const Q_TYPE_LABELS = {
  definition:  "DEFINITION",
  application: "APPLICATION",
  edge_case:   "EDGE CASE",
  comparison:  "COMPARISON",
  debug:       "DEBUG TRACE",
};

// ── Confidence labels ─────────────────────────────────────────
const CONFIDENCE_SEGMENTS = [
  { val: 20,  label: "Low" },
  { val: 50,  label: "Mid" },
  { val: 80,  label: "High" },
  { val: 100, label: "Max" },
];

// ── Student ID (localStorage, stable across sessions) ─────────
function getOrCreateStudentId() {
  const KEY = "als_student_id";
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = typeof crypto !== "undefined" && crypto.randomUUID
      ? `s_${crypto.randomUUID().slice(0, 8)}`
      : `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem(KEY, id);
  }
  return id;
}

const STUDENT_ID = getOrCreateStudentId();


// ── App ───────────────────────────────────────────────────────
export default function App() {

  // ── Backend state ────────────────────────────────────────
  const [question, setQuestion]         = useState("");
  const [questionType, setQuestionType] = useState("");
  const [questionKey, setQuestionKey]   = useState(0); // increments to trigger fade-in animation
  const [feedback, setFeedback]         = useState(null);
  const [graphData, setGraphData]       = useState({ nodes: [], links: [] });

  // ── Input state ──────────────────────────────────────────
  const [input, setInput]             = useState("");
  const [confidence, setConfidence]   = useState(50);
  const [explorationMode, setExplorationMode] = useState("Socratic");
  const [personalityMode, setPersonalityMode] = useState("Socratic");

  // ── Loading state ────────────────────────────────────────
  const [isLoading, setIsLoading]           = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [initError, setInitError]           = useState(null);
  const [transcription, setTranscription]   = useState(null);

  // ── Media state ──────────────────────────────────────────
  const [selectedImage, setSelectedImage] = useState(null); // base64
  const [isRecording, setIsRecording]     = useState(false);
  const [audioBase64, setAudioBase64]     = useState(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const fileInputRef = useRef(null);

  // ── Session tracking ─────────────────────────────────────
  const [sessionActiveIds, setSessionActiveIds] = useState(new Set());
  const [sessionStats, setSessionStats] = useState({
    interactions: 0,
    masteryDelta: 0,
    errorDelta: 0,
  });
  const [unlockedConcepts, setUnlockedConcepts] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);

  // ── UI settings ──────────────────────────────────────────
  const [isDarkMode, setIsDarkMode]           = useState(true);
  const [accentColor, setAccentColor]         = useState("blue");
  const [showSettings, setShowSettings]       = useState(false);
  const [showGraphLabels, setShowGraphLabels] = useState(false);
  const [showTranscript, setShowTranscript]   = useState(false);
  const [activeTab, setActiveTab]             = useState("session");


  // ── Effects ───────────────────────────────────────────────

  useEffect(() => {
    if (isDarkMode) document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");
  }, [isDarkMode]);

  useEffect(() => {
    document.documentElement.dataset.accent = accentColor;
  }, [accentColor]);

  // Init: load lifetime graph + generate first question in parallel
  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      setIsInitializing(true);
      setInitError(null);
      try {
        const [graph, firstQ] = await Promise.all([
          EvaluationAPI.getGraph(STUDENT_ID),
          EvaluationAPI.getFirstQuestion(STUDENT_ID),
        ]);
        if (cancelled) return;
        setGraphData({ nodes: graph.nodes, links: graph.links });
        setQuestion(firstQ.nextQuestion);
        setQuestionType(firstQ.questionType || "");
        setQuestionKey(1);
      } catch (e) {
        if (cancelled) return;
        console.error("ALS init failed:", e);
        setInitError(e.message || "Could not connect to backend.");
      } finally {
        if (!cancelled) setIsInitializing(false);
      }
    };
    init();
    return () => { cancelled = true; };
  }, []);


  // ── Derived data ──────────────────────────────────────────

  const sessionGraphData = useMemo(() => {
    const activeNodes = graphData.nodes.filter((n) => sessionActiveIds.has(n.id));
    const activeLinks = graphData.links.filter((l) => {
      const src = typeof l.source === "object" ? l.source.id : l.source;
      const tgt = typeof l.target === "object" ? l.target.id : l.target;
      return sessionActiveIds.has(src) && sessionActiveIds.has(tgt);
    });
    return { nodes: activeNodes, links: activeLinks };
  }, [graphData, sessionActiveIds]);

  const currentGraphData = activeTab === "lifetime" ? graphData : sessionGraphData;
  const nodesPool = graphData.nodes;
  const sysAvgMastery = Math.round(
    nodesPool.reduce((acc, n) => acc + (Number(n.mastery) || 0), 0) /
    (nodesPool.length || 1)
  );
  const questionNumber = String(sessionStats.interactions + 1).padStart(2, "0");


  // ── Handlers ──────────────────────────────────────────────

  const handleSubmit = async () => {
    if ((!input.trim() && !audioBase64 && !selectedImage) || isLoading || isInitializing || initError) return;
    playSubmit();
    setIsLoading(true);
    try {
      const result = await EvaluationAPI.evaluateResponse(
        question, input, confidence, STUDENT_ID, explorationMode, personalityMode, selectedImage, audioBase64
      );

      // Save the completed turn to history before advancing
      const completedTurn = {
        id: sessionStats.interactions + 1,
        question: question,
        questionType: questionType,
        userInput: input,
        confidence: confidence,
        gap: result.gap,
        conceptUpdates: result.conceptUpdates
      };
      setChatHistory(prev => [...prev, completedTurn]);

      setFeedback(result);

      // Advance to next question with fade-in animation
      if (result.nextQuestion) {
        setQuestion(result.nextQuestion);
        setQuestionType(result.questionType || "");
        setQuestionKey((k) => k + 1);
        setTimeout(() => playQuestionAppear(), 200);
      }

      if (result.transcription) {
        setTranscription(result.transcription);
        // If the user didn't type anything, maybe auto-fill the input with the transcription for them to edit?
        // Or just show it as feedback. Let's show it as feedback.
      }

      // Unlock notification
      if (result.newNodes?.length > 0) {
        setUnlockedConcepts(result.newNodes.map((n) => n.id));
        setTimeout(() => setUnlockedConcepts([]), 5000);
        setTimeout(() => playUnlock(), 80);
      }

      // Session stats
      const newTrackedIds = new Set(sessionActiveIds);
      let runMasteryDelta = 0, runErrorDelta = 0;
      result.conceptUpdates?.forEach((u) => {
        newTrackedIds.add(u.id);
        runMasteryDelta += u.masteryDelta || 0;
        runErrorDelta += u.errorDelta || 0;
      });
      setSessionActiveIds(newTrackedIds);
      setSessionStats((prev) => ({
        interactions: prev.interactions + 1,
        masteryDelta: prev.masteryDelta + runMasteryDelta,
        errorDelta: prev.errorDelta + runErrorDelta,
      }));

      // Apply graph mutations
      setGraphData((prev) => {
        const nodeMap = new Map(prev.nodes.map((n) => [n.id, { ...n }]));
        result.conceptUpdates?.forEach((u) => {
          const node = nodeMap.get(u.id);
          if (node) {
            node.mastery    = Math.max(0, Math.min(100, node.mastery    + (u.masteryDelta    || 0)));
            node.confidence = Math.max(0, Math.min(100, node.confidence + (u.confidenceDelta || 0)));
            node.error_rate = Math.max(0, Math.min(1,   node.error_rate + (u.errorDelta      || 0)));
          }
        });
        result.newNodes?.forEach((n) => {
          if (!nodeMap.has(n.id)) nodeMap.set(n.id, { ...n });
        });
        const existingLinks = prev.links.map((l) => ({
          source:   typeof l.source === "object" ? l.source.id : l.source,
          target:   typeof l.target === "object" ? l.target.id : l.target,
          strength: l.strength,
        }));
        const linkKeys = new Set(existingLinks.map((l) => `${l.source}|${l.target}`));
        const addedLinks = (result.newLinks || []).filter(
          (l) => !linkKeys.has(`${l.source}|${l.target}`)
        );
        return { nodes: Array.from(nodeMap.values()), links: [...existingLinks, ...addedLinks] };
      });

      setInput(""); // clear after successful evaluation
      setSelectedImage(null);
      setAudioBase64(null);
      setTranscription(null);

    } catch (e) {
      console.error("Evaluation failed:", e);
      playError();
      setFeedback({
        gap: e.message || "Request failed. Verify the backend is running on port 8000.",
        confidenceMismatch: false,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetryInit = () => {
    playSubmit();
    setIsInitializing(true);
    setInitError(null);
    setGraphData({ nodes: [], links: [] });
    Promise.all([
      EvaluationAPI.getGraph(STUDENT_ID),
      EvaluationAPI.getFirstQuestion(STUDENT_ID),
    ])
      .then(([graph, firstQ]) => {
        setGraphData({ nodes: graph.nodes, links: graph.links });
        setQuestion(firstQ.nextQuestion);
        setQuestionType(firstQ.questionType || "");
        setQuestionKey((k) => k + 1);
      })
      .catch((e) => setInitError(e.message || "Connection failed."))
      .finally(() => setIsInitializing(false));
  };

  const canSubmit = (input.trim().length > 0 || audioBase64 || selectedImage) && !isLoading && !isInitializing && !initError;

  // ── Media Handlers ───────────────────────────────────────

  const handleImageClick = () => fileInputRef.current?.click();

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    playAttach();
    const reader = new FileReader();
    reader.onloadend = () => setSelectedImage(reader.result);
    reader.readAsDataURL(file);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const reader = new FileReader();
        reader.onloadend = () => setAudioBase64(reader.result);
        reader.readAsDataURL(blob);
        stream.getTracks().forEach(t => t.stop());
      };

      recorder.start();
      setIsRecording(true);
      playRecordingStart();
    } catch (err) {
      console.error("Audio recording failed:", err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      playRecordingStop();
    }
  };


  // ── Render ────────────────────────────────────────────────

  return (
    <div className="h-screen w-full bg-white dark:bg-[#050505] text-black dark:text-white font-sans overflow-hidden flex relative">

      {/* ── Layer 0: Graph canvas — FIXED mask for typical screen widths ── */}
      <div
        className="absolute inset-0 z-0 pointer-events-auto"
        style={{
          WebkitMaskImage: "linear-gradient(to right, transparent 0px, transparent 360px, black 460px, black calc(100% - 460px), transparent calc(100% - 360px), transparent 100%)",
          maskImage:        "linear-gradient(to right, transparent 0px, transparent 360px, black 460px, black calc(100% - 460px), transparent calc(100% - 360px), transparent 100%)",
        }}
      >
        <AnalyticalGraph
          key={activeTab}
          graphData={currentGraphData}
          isDarkMode={isDarkMode}
          showLabels={showGraphLabels}
        />
      </div>

      {/* ── Settings overlay ── */}
      {showSettings && (
        <SettingsOverlay
          isDarkMode={isDarkMode}       setIsDarkMode={setIsDarkMode}
          accentColor={accentColor}     setAccentColor={setAccentColor}
          showLabels={showGraphLabels}  setShowLabels={setShowGraphLabels}
          onClose={() => setShowSettings(false)}
        />
      )}

      {/* ── Transcript overlay ── */}
      {showTranscript && (
        <TranscriptOverlay
          history={chatHistory}
          onClose={() => setShowTranscript(false)}
        />
      )}

      {/* ── Unlock notification ── */}
      {unlockedConcepts.length > 0 && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-50 flex gap-2 pointer-events-none animate-[fadeIn_0.5s_ease-out]">
          {unlockedConcepts.map((id) => (
            <span
              key={id}
              className="font-mono text-[9px] uppercase tracking-[0.2em] bg-green-500/10 border border-green-500/40 text-green-600 dark:text-green-400 px-3 py-1.5 rounded-full"
            >
              ↑ {id} Unlocked
            </span>
          ))}
        </div>
      )}

      {/* ── Layer 1: Floating UI panels ── */}
      <div className="absolute inset-0 z-10 pointer-events-none px-6 md:px-12 pt-6 md:pt-8 pb-6 flex flex-col md:flex-row justify-between gap-6">

        {/* ══════════════════════════════════════════
            LEFT PANEL: Thinking Surface
            Fixed structure — question + input ALWAYS visible.
        ══════════════════════════════════════════ */}
        <div className="w-full md:w-[420px] h-full pointer-events-auto flex-shrink-0 flex flex-col gap-5 overflow-hidden animate-[fadeIn_0.8s_cubic-bezier(0.25,1,0.5,1)] pb-2">

          {/* ─── SCROLLABLE QUESTION & FEEDBACK BOX ─── */}
          <div className="flex-1 min-h-0 px-2 py-2 flex flex-col gap-6 overflow-y-auto no-scrollbar relative z-10 w-full">

            {/* ─── SECTION 1: Question ─────────────────── */}
          <div className="flex flex-col gap-3 flex-shrink-0">

            {/* Meta row: type badge + question counter */}
            <div className="flex items-center justify-between px-1">
              <span className="font-tactical text-[9px] uppercase tracking-[0.3em] text-gray-700 dark:text-gray-500">
                {isInitializing ? "Connecting..." : (Q_TYPE_LABELS[questionType] || "—")}
              </span>
              <span className="font-tactical text-[11px] font-bold text-gray-600 dark:text-gray-700 tracking-[0.2em]">
                Q.{questionNumber}
              </span>
            </div>

            {/* Question text ── key triggers fade-in on each new question */}
            {initError ? (
              /* Error state */
              <div className="flex flex-col gap-4">
                <p className="font-serif italic text-2xl text-gray-700 dark:text-gray-600 leading-tight">
                  Connection failed.
                </p>
                <p className="font-mono text-[10px] text-red-500 dark:text-red-400 leading-relaxed uppercase tracking-widest break-all">
                  {initError}
                </p>
                <code className="font-mono text-[10px] text-black dark:text-white/80 bg-black/5 dark:bg-white/5 rounded-xl px-4 py-3 block leading-relaxed">
                  cd als_backend{"\n"}python -m uvicorn main:app --reload --port 8000
                </code>
                <button
                  onClick={handleRetryInit}
                  className="font-mono text-[10px] uppercase tracking-widest border border-black/10 dark:border-white/10 px-5 py-2.5 rounded-full w-max hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-all duration-500 mt-1"
                >
                  Retry Connection →
                </button>
              </div>
            ) : (
              /* Question text */
              <div>
                <h1
                  key={questionKey}
                  className="font-voice italic text-[1.4rem] md:text-[1.65rem] font-normal text-black dark:text-gray-100 tracking-tight leading-[1.35] animate-[fadeIn_0.6s_cubic-bezier(0.25,1,0.5,1)]"
                >
                  {isInitializing
                    ? <span className="font-tactical text-gray-700 dark:text-gray-700 animate-pulse text-[10px] uppercase tracking-[0.25em] not-italic">Initializing learning engine...</span>
                    : <Typewriter text={question} speed={12} />
                  }
                </h1>
              </div>
            )}

            {/* Instruction hint — only shows before first submission */}
            {!feedback && !isInitializing && !initError && (
              <p className="font-mono text-[9px] uppercase tracking-[0.25em] text-gray-600 dark:text-gray-600 px-1">
                ↓ Write your response below
              </p>
            )}
          </div>

          </div>{/* END SCROLLABLE QUESTION BOX */}

          {/* ─── SECTION 2: Input Card ───────────────── */}
          <div className="flex flex-col bg-white/75 dark:bg-white/[0.035] backdrop-blur-3xl border border-black/5 dark:border-white/5 rounded-[1.75rem] px-7 pt-7 pb-6 luxury-shadow-light dark:luxury-shadow-dark flex-shrink-0 transition-all duration-700">

            {/* Mode Controls */}
            <div className="flex gap-4 mb-5 pb-5 border-b border-black/5 dark:border-white/5">
              <div className="flex flex-col gap-1.5 w-full">
                <span className="font-tactical text-[7.5px] uppercase tracking-[0.25em] text-gray-400 font-bold ml-1">Exploration Mode</span>
                <select 
                  value={explorationMode} 
                  onChange={e => { playAttach(); setExplorationMode(e.target.value); }}
                  className="appearance-none font-tactical text-[10.5px] bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-full px-3 py-1.5 hover:bg-black/10 dark:hover:bg-white/10 transition-colors focus:outline-none focus:ring-1 focus:ring-black/20 dark:focus:ring-white/20 text-gray-800 dark:text-gray-300 cursor-pointer"
                >
                  <option className="bg-white dark:bg-[#111] text-black dark:text-gray-200" value="Socratic">Socratic (Balanced)</option>
                  <option className="bg-white dark:bg-[#111] text-black dark:text-gray-200" value="Depth">Depth (Mastery-focused)</option>
                  <option className="bg-white dark:bg-[#111] text-black dark:text-gray-200" value="Float">Float (Breadth-focused)</option>
                  <option className="bg-white dark:bg-[#111] text-black dark:text-gray-200" value="Drift">Drift (Connection-driven)</option>
                </select>
              </div>
              <div className="flex flex-col gap-1.5 w-full">
                <span className="font-tactical text-[7.5px] uppercase tracking-[0.25em] text-gray-400 font-bold ml-1">Personality Voice</span>
                <select 
                  value={personalityMode} 
                  onChange={e => { playAttach(); setPersonalityMode(e.target.value); }}
                  className="appearance-none font-tactical text-[10.5px] bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-full px-3 py-1.5 hover:bg-black/10 dark:hover:bg-white/10 transition-colors focus:outline-none focus:ring-1 focus:ring-black/20 dark:focus:ring-white/20 text-gray-800 dark:text-gray-300 cursor-pointer"
                >
                  <option className="bg-white dark:bg-[#111] text-black dark:text-gray-200" value="Socratic">Socratic</option>
                  <option className="bg-white dark:bg-[#111] text-black dark:text-gray-200" value="Nerdy">Nerdy</option>
                  <option className="bg-white dark:bg-[#111] text-black dark:text-gray-200" value="Strict">Strict (Fast)</option>
                  <option className="bg-white dark:bg-[#111] text-black dark:text-gray-200" value="Collaborative">Collaborative</option>
                </select>
              </div>
            </div>

            {/* Textarea */}
            <textarea
              spellCheck={false}
              autoComplete="off"
              autoCorrect="off"
              className="w-full bg-transparent border-0 rounded-none p-0 text-black dark:text-white focus:ring-0 focus:outline-none resize-none font-tactical font-light text-[0.95rem] leading-relaxed placeholder-gray-500 dark:placeholder-gray-600 disabled:opacity-40"
              rows={4}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
              }}
              placeholder="Explain your understanding — be precise about time complexity, edge cases, and trade-offs..."
              disabled={isInitializing || !!initError}
            />

            {/* Media Previews */}
            {(selectedImage || audioBase64 || isRecording) && (
              <div className="flex gap-4 mt-2 mb-4 animate-[fadeIn_0.5s_ease-out]">
                {selectedImage && (
                  <div className="relative group/img h-16 w-16 rounded-lg overflow-hidden border border-black/10 dark:border-white/10">
                    <img src={selectedImage} className="h-full w-full object-cover" alt="Selected" />
                    <button 
                      onClick={() => setSelectedImage(null)}
                      className="absolute inset-0 bg-black/40 opacity-0 group-hover/img:opacity-100 transition-opacity flex items-center justify-center text-white text-[10px] font-bold"
                    >
                      REMOVE
                    </button>
                  </div>
                )}
                {isRecording && (
                  <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 px-3 py-1.5 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                    <span className="font-mono text-[9px] text-red-600 dark:text-red-400 uppercase tracking-widest">Recording...</span>
                  </div>
                )}
                {audioBase64 && !isRecording && (
                  <div className="flex items-center gap-3 bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 px-3 py-1.5 rounded-full group/audio">
                    <span className="font-mono text-[9px] text-gray-700 dark:text-gray-400 uppercase tracking-widest">Audio Ready</span>
                    <button 
                      onClick={() => setAudioBase64(null)}
                      className="text-[8px] font-bold text-red-500/60 hover:text-red-500 transition-colors"
                    >
                      ✕
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* char count + confidence value row */}
            <div className="flex justify-between items-center mt-3 mb-5">
              <span className="font-mono text-[8px] text-gray-600 dark:text-gray-600 tabular-nums">
                {input.length > 0 ? `${input.length} chars` : ""}
              </span>
              <span className="font-mono text-[10px] text-gray-700 dark:text-gray-500 uppercase tracking-widest">
                Confidence: <span className="text-black dark:text-white font-bold">{confidence}%</span>
              </span>
            </div>

            {/* Confidence segmented control */}
            <div className="flex justify-between items-end mb-6">
              <span className="font-mono text-[9.5px] uppercase tracking-[0.25em] text-gray-500 font-bold">
                Certainty
              </span>
              <div className="flex items-end gap-3">
                {CONFIDENCE_SEGMENTS.map(({ val, label }) => (
                  <button
                    key={val}
                    onClick={() => { setConfidence(val); playConfidenceTick(); }}
                    title={`${val}% confidence`}
                    className="flex flex-col items-center gap-1.5 cursor-pointer group"
                  >
                    <span className={`h-0.5 rounded-full transition-all duration-700 ease-[cubic-bezier(0.25,1,0.5,1)] ${
                      confidence >= val
                        ? "bg-black dark:bg-white w-9"
                        : "bg-gray-200 dark:bg-white/[0.12] w-5 group-hover:bg-gray-300 dark:group-hover:bg-white/25"
                    }`} />
                    <span className={`font-mono text-[9px] uppercase transition-colors duration-300 ${
                      confidence >= val
                        ? "text-gray-800 dark:text-gray-200 font-bold"
                        : "text-gray-500 dark:text-gray-600 font-medium"
                    }`}>
                      {label}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Divider + Submit */}
            <div className="flex gap-8 items-center border-t border-black/5 dark:border-white/5 pt-5">
              <button
                className={`font-sans font-semibold text-sm tracking-wide relative transition-all duration-500 overflow-hidden group/btn ${
                  canSubmit
                    ? "text-black dark:text-white"
                    : "text-gray-700 dark:text-gray-700 cursor-not-allowed"
                }`}
                onClick={handleSubmit}
                disabled={!canSubmit}
              >
                <span className="relative z-10">
                  {isLoading ? "Synthesizing..." : "Synthesize →"}
                </span>
                {canSubmit && (
                  <span className="absolute bottom-[-3px] left-0 w-0 h-px bg-black dark:bg-white transition-all duration-700 ease-[cubic-bezier(0.25,1,0.5,1)] group-hover/btn:w-full" />
                )}
              </button>

              <span className="font-mono text-[8px] text-gray-600 dark:text-gray-600 uppercase tracking-widest">
                {isInitializing ? "Loading..." : canSubmit ? "⌘↵" : "Type to enable"}
              </span>

              <div className="flex-1" />

              <div className="flex gap-4">
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  accept="image/*" 
                  className="hidden" 
                />
                <button 
                  onClick={handleImageClick}
                  className={`p-2 rounded-full transition-all duration-300 ${selectedImage ? "bg-black text-white dark:bg-white dark:text-black" : "text-gray-400 hover:text-black dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5"}`}
                  title="Upload Image"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>
                </button>
                <button 
                  onClick={isRecording ? stopRecording : startRecording}
                  className={`p-2 rounded-full transition-all duration-300 ${isRecording ? "bg-red-500 text-white animate-pulse" : audioBase64 ? "bg-black text-white dark:bg-white dark:text-black" : "text-gray-400 hover:text-black dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5"}`}
                  title={isRecording ? "Stop Recording" : "Record Audio"}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
                </button>
              </div>
            </div>
          </div>

        </div>{/* END LEFT PANEL */}


        {/* ══════════════════════════════════════════
            RIGHT PANEL: Deep Architecture HUD
        ══════════════════════════════════════════ */}
        <div className="h-full pointer-events-auto overflow-y-auto no-scrollbar">
          <div className="flex flex-col items-end gap-12">

            {/* Navigation tabs */}
            <div className="flex gap-6 font-tactical text-[11px] font-bold uppercase tracking-[0.25em] text-gray-700 dark:text-gray-500 mt-2">
              {[
                { id: "lifetime", label: "Lifetime" },
                { id: "session",  label: "Session"  },
              ].map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => { playConfidenceTick(); setActiveTab(id); }}
                  className={`relative transition-all duration-700 ${
                    activeTab === id
                      ? "text-black dark:text-white"
                      : "hover:text-gray-700 dark:hover:text-gray-300"
                  }`}
                >
                  {label}
                  <span className={`absolute -bottom-2.5 left-1/2 w-1 h-1 bg-black dark:bg-white rounded-full -translate-x-1/2 transition-all duration-500 ${
                    activeTab === id ? "opacity-100 scale-100" : "opacity-0 scale-0"
                  }`} />
                </button>
              ))}
              <button
                onClick={() => { playConfidenceTick(); setShowTranscript(true); }}
                className="hover:text-black dark:hover:text-white transition-colors duration-500"
              >
                Transcript
              </button>
              <button
                onClick={() => { playConfidenceTick(); setShowSettings(!showSettings); }}
                className="hover:text-black dark:hover:text-white transition-colors duration-500"
              >
                Options
              </button>
            </div>

            {/* HUD metrics card */}
            <div className="flex flex-col gap-8 text-right bg-white/40 dark:bg-white/[0.03] backdrop-blur-xl px-8 py-7 rounded-[1.75rem] luxury-shadow-light dark:luxury-shadow-dark border border-black/5 dark:border-white/5 min-w-[240px]">

              {/* Primary metrics */}
              {(activeTab === "lifetime"
                ? [
                    { title: "Concepts Unlocked", val: nodesPool.length, sub: "of 200 total" },
                    { title: "Avg Mastery", val: `${sysAvgMastery}%`, sub: "across graph" },
                  ]
                : [
                    { title: "Concepts Visited", val: sessionActiveIds.size, sub: "this session" },
                    {
                      title: "Mastery Gain",
                      val: `${sessionStats.masteryDelta > 0 ? "+" : ""}${sessionStats.masteryDelta.toFixed(1)}%`,
                      sub: `${sessionStats.interactions} response${sessionStats.interactions !== 1 ? "s" : ""}`,
                    },
                  ]
              ).map((m, i) => (
                <div key={i} className="flex flex-col gap-1">
                  <span className="font-tactical text-[10px] uppercase tracking-[0.25em] text-gray-700 dark:text-gray-500 font-bold">
                    {m.title}
                  </span>
                  <span className="font-voice italic text-[2.8rem] leading-none text-black dark:text-white">
                    {m.val}
                  </span>
                  <span className="font-tactical text-[10px] text-gray-600 dark:text-gray-600 uppercase tracking-widest">
                    {m.sub}
                  </span>
                </div>
              ))}

              {/* Divider */}
              <div className="h-px bg-black/5 dark:bg-white/5" />

              {/* Signal legend */}
              <div className="flex flex-col gap-2.5">
                <span className="font-tactical text-[10px] uppercase tracking-[0.3em] text-gray-600 dark:text-gray-600 font-bold">
                  Signal Legend
                </span>
                {[
                  { label: "Stability ≥ 75", dot: "bg-green-500",  text: "text-green-600 dark:text-green-500",  name: "Stable"   },
                  { label: "Stability 45–74", dot: "bg-yellow-400", text: "text-yellow-600 dark:text-yellow-400", name: "Developing" },
                  { label: "Stability < 45",  dot: "bg-red-500",    text: "text-red-500",                         name: "At Risk"   },
                ].map(({ label, dot, text, name }) => (
                  <div key={name} className="flex items-center justify-end gap-2.5">
                    <div className="text-right">
                      <div className={`font-tactical text-[11px] uppercase font-bold ${text}`}>{name}</div>
                      <div className="font-tactical text-[9px] text-gray-600 dark:text-gray-600">{label}</div>
                    </div>
                    <span className={`w-2.5 h-2.5 rounded-full ${dot} flex-shrink-0`} />
                  </div>
                ))}
              </div>

              {/* System Insight / Critique */}
              {(() => {
                const isValuable = feedback && (
                  feedback.confidenceMismatch || 
                  (feedback.gap && feedback.gap.length > 30 && !feedback.gap.toLowerCase().includes("no gap"))
                );
                if (!isValuable) return null;
                
                return (
                  <div className="pt-4 border-t border-black/5 dark:border-white/5 animate-[fadeIn_0.5s_ease-out]">
                    <details className="group text-right">
                      <summary onClick={() => playConfidenceTick()} className="font-tactical text-[10px] uppercase font-bold text-yellow-600 dark:text-yellow-500 tracking-widest cursor-pointer hover:text-yellow-700 dark:hover:text-yellow-400 transition-colors outline-none select-none list-none flex items-center justify-end gap-2">
                        <span className="group-open:hidden">Show System Insight ↓</span>
                        <span className="hidden group-open:inline">Hide System Insight ↑</span>
                        <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.5)]" />
                      </summary>
                      <div className="flex flex-col gap-2 mt-4 text-right">
                        <p className="font-tactical text-[0.85rem] leading-[1.5] text-gray-700 dark:text-gray-300 font-light">
                          {feedback.gap}
                        </p>
                        {feedback.confidenceMismatch && (
                          <div className="flex items-center justify-end gap-2 mt-2">
                            <p className="font-tactical text-[8px] font-bold uppercase tracking-widest text-red-500 dark:text-red-400/80">
                              Calibration Drift Detected
                            </p>
                            <span className="w-1 h-1 rounded-full bg-red-500 flex-shrink-0" />
                          </div>
                        )}
                      </div>
                    </details>
                  </div>
                );
              })()}

              {/* Concept Deltas / Details */}
              {feedback?.conceptUpdates?.length > 0 && (
                <div className="pt-4 border-t border-black/5 dark:border-white/5">
                  <details className="group text-right">
                    <summary onClick={() => playConfidenceTick()} className="font-tactical text-[10px] uppercase font-bold text-gray-600 dark:text-gray-500 tracking-widest cursor-pointer hover:text-black dark:hover:text-white transition-colors outline-none select-none list-none">
                      <span className="group-open:hidden">Show Node Deltas ↓</span>
                      <span className="hidden group-open:inline">Hide Node Deltas ↑</span>
                    </summary>
                    <div className="flex flex-col gap-1.5 mt-3 text-right">
                      {feedback.conceptUpdates.map((u) => {
                        const delta = u.masteryDelta || 0;
                        const positive = delta > 0;
                        return (
                          <div key={u.id} className="flex flex-row-reverse items-center justify-between gap-4">
                            <span className="font-tactical text-[10px] text-gray-700 dark:text-gray-400 uppercase tracking-widest">
                              {u.id}
                            </span>
                            <span className={`font-tactical text-[10px] font-bold tabular-nums ${
                              positive
                                ? "text-green-600 dark:text-green-500"
                                : delta < 0
                                  ? "text-red-500/80"
                                  : "text-gray-400"
                            }`}>
                              {positive ? "+" : ""}{delta.toFixed(1)}%
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </details>
                </div>
              )}

              {/* Student ID */}
              <div className="pt-2 border-t border-black/5 dark:border-white/5 text-right">
                <span className="font-tactical text-[9px] text-gray-600 dark:text-gray-600 tracking-widest select-all uppercase">
                  {STUDENT_ID}
                </span>
              </div>

            </div>{/* END HUD CARD */}

          </div>
        </div>{/* END RIGHT PANEL */}

      </div>{/* END LAYER 1 */}

    </div>
  );
}