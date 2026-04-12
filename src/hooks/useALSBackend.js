import { useState, useEffect, useMemo } from 'react';
import { EvaluationAPI } from '../api.js';
import { playSubmit, playQuestionAppear, playUnlock, playError } from '../sounds.js';

export function useALSBackend(studentId, explorationMode, personalityMode) {
  const [question, setQuestion] = useState("");
  const [questionType, setQuestionType] = useState("");
  const [questionKey, setQuestionKey] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [initError, setInitError] = useState(null);
  const [transcription, setTranscription] = useState(null);
  
  const [sessionActiveIds, setSessionActiveIds] = useState(new Set());
  const [sessionStats, setSessionStats] = useState({ interactions: 0, masteryDelta: 0, errorDelta: 0 });
  const [unlockedConcepts, setUnlockedConcepts] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  
  useEffect(() => {
    let cancelled = false;
    const init = async () => {
      setIsInitializing(true);
      setInitError(null);
      try {
        const [graph, firstQ] = await Promise.all([
          EvaluationAPI.getGraph(studentId),
          EvaluationAPI.getFirstQuestion(studentId),
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
  }, [studentId]);

  const evaluateInput = async (input, confidence, selectedImage, audioBase64) => {
    playSubmit();
    setIsLoading(true);
    try {
      const result = await EvaluationAPI.evaluateResponse(
        question, input, confidence, studentId, explorationMode, personalityMode, selectedImage, audioBase64
      );

      const completedTurn = {
        id: sessionStats.interactions + 1,
        question, questionType, userInput: input, confidence, gap: result.gap, conceptUpdates: result.conceptUpdates
      };
      setChatHistory(prev => [...prev, completedTurn]);
      setFeedback(result);

      if (result.nextQuestion) {
        setQuestion(result.nextQuestion);
        setQuestionType(result.questionType || "");
        setQuestionKey(k => k + 1);
        setTimeout(() => playQuestionAppear(), 200);
      }

      if (result.transcription) {
        setTranscription(result.transcription);
      }

      if (result.newNodes?.length > 0) {
        setUnlockedConcepts(result.newNodes.map(n => n.id));
        setTimeout(() => setUnlockedConcepts([]), 5000);
        setTimeout(() => playUnlock(), 80);
      }

      const newTrackedIds = new Set(sessionActiveIds);
      let runMasteryDelta = 0, runErrorDelta = 0;
      result.conceptUpdates?.forEach(u => {
        newTrackedIds.add(u.id);
        runMasteryDelta += u.masteryDelta || 0;
        runErrorDelta += u.errorDelta || 0;
      });
      setSessionActiveIds(newTrackedIds);
      setSessionStats(prev => ({
        interactions: prev.interactions + 1,
        masteryDelta: prev.masteryDelta + runMasteryDelta,
        errorDelta: prev.errorDelta + runErrorDelta,
      }));

      setGraphData(prev => {
        const nodeMap = new Map(prev.nodes.map(n => [n.id, { ...n }]));
        result.conceptUpdates?.forEach(u => {
          const node = nodeMap.get(u.id);
          if (node) {
            node.mastery = Math.max(0, Math.min(100, node.mastery + (u.masteryDelta || 0)));
            node.confidence = Math.max(0, Math.min(100, node.confidence + (u.confidenceDelta || 0)));
            node.error_rate = Math.max(0, Math.min(1, node.error_rate + (u.errorDelta || 0)));
          }
        });
        result.newNodes?.forEach(n => {
          if (!nodeMap.has(n.id)) nodeMap.set(n.id, { ...n });
        });
        const existingLinks = prev.links.map(l => ({
          source: typeof l.source === "object" ? l.source.id : l.source,
          target: typeof l.target === "object" ? l.target.id : l.target,
          strength: l.strength,
        }));
        const linkKeys = new Set(existingLinks.map(l => `${l.source}|${l.target}`));
        const addedLinks = (result.newLinks || []).filter(l => !linkKeys.has(`${l.source}|${l.target}`));
        return { nodes: Array.from(nodeMap.values()), links: [...existingLinks, ...addedLinks] };
      });

      return { success: true };
    } catch (e) {
      console.error("Evaluation failed:", e);
      playError();
      setFeedback({
        gap: e.message || "Request failed. Verify the backend is running on port 8000.",
        confidenceMismatch: false,
      });
      return { success: false };
    } finally {
      setIsLoading(false);
    }
  };

  const retryInit = () => {
    playSubmit();
    setIsInitializing(true);
    setInitError(null);
    setGraphData({ nodes: [], links: [] });
    Promise.all([
      EvaluationAPI.getGraph(studentId),
      EvaluationAPI.getFirstQuestion(studentId),
    ])
      .then(([graph, firstQ]) => {
        setGraphData({ nodes: graph.nodes, links: graph.links });
        setQuestion(firstQ.nextQuestion);
        setQuestionType(firstQ.questionType || "");
        setQuestionKey(k => k + 1);
      })
      .catch((e) => setInitError(e.message || "Connection failed."))
      .finally(() => setIsInitializing(false));
  };

  return {
    question, setQuestion, questionType, setQuestionType, questionKey, setQuestionKey,
    feedback, setFeedback, graphData, setGraphData,
    isLoading, setIsLoading, isInitializing, setIsInitializing, initError, setInitError,
    transcription, setTranscription,
    sessionActiveIds, setSessionActiveIds, sessionStats, setSessionStats,
    unlockedConcepts, setUnlockedConcepts, chatHistory, setChatHistory,
    evaluateInput, retryInit
  };
}
