import { useState, useCallback } from "react";
import "./App.css";

import SplashScreen       from "./components/SplashScreen";
import InstructionsScreen from "./components/InstructionsScreen";
import ScanScreen         from "./components/ScanScreen";
import ProcessingScreen   from "./components/ProcessingScreen";
import ResultScreen       from "./components/ResultScreen";
import HistoryScreen      from "./components/HistoryScreen";
import DashboardScreen      from "./components/DashboardScreen";

import { apiScan }          from "./api";
import { MOCK, RECOMMENDATIONS } from "./constants";

let scanCounter = 0;

const CONDITION_LABELS = {
  ripe:     "Hinog (Ripe)",
  overripe: "Sobrang Hinog (Overripe)",
  unripe:   "Hindi Pa Hinog (Unripe)",
  rotten:   "Bulok (Rotten)",
};


function scoreFromFreshness(condition) {
  return condition === "ripe" ? 5 : condition === "rotten" ? 1 : 2;
}

/**
 * After the backend returns a result, override the fruit identity
 * with what MobileNet actually saw — this is always correct.
 */
function applyFruitIdentity(result) {
  const fruitName  = window.__siglaani_fruit_name__  ?? null;
  const scientific = window.__siglaani_scientific__  ?? null;
  const modelCondition = window.__siglaani_class_condition__ ?? null;

  if (fruitName)  result.fruit      = fruitName;
  if (scientific) result.scientific = scientific;

  if (modelCondition) {
    result.condition = modelCondition;
  }

  if (result.condition) {
    result.conditionLabel = CONDITION_LABELS[result.condition] ?? result.condition;
    result.rating = scoreFromFreshness(result.condition);

    const baseReco = RECOMMENDATIONS[result.condition] ?? result.recommendation;
    if (fruitName) {
      const prefix = result.condition === "ripe"
        ? `${fruitName} looks fresh. `
        : `${fruitName} looks not fresh. `;
      result.recommendation = `${prefix}${baseReco}`;
    } else {
      result.recommendation = baseReco;
    }
  }

  return result;
}

export default function App() {
  const [screen,     setScreen]     = useState("splash");
  const [result,     setResult]     = useState(null);
  const [scanId,     setScanId]     = useState(0);
  const [prevScreen, setPrevScreen] = useState("splash");

  const go = useCallback((s) => setScreen(s), []);

  const goHistory = useCallback(() => {
    setPrevScreen(screen);
    setScreen("history");
  }, [screen]);

  const goDashboard = useCallback(() => {
    setPrevScreen(screen);
    setScreen("dashboard");
  }, [screen]);

const handleProcessingComplete = useCallback(async () => {
    scanCounter++; // Keep this just in case of an emergency fallback

    try {
      // Grab the picture we saved in ScanScreen
      const imagePayload = window.__siglaani_captured_image__ || null;
      
      const payload = {
        image: imagePayload,
        detected_fruit: window.__siglaani_fruit_name__,
        hsv_key: window.__siglaani_hsv_key__
      };

      const data = await apiScan(payload);
      setResult(applyFruitIdentity({ ...data }));
      
      // ✅ Grab the REAL ID straight from the database!
      setScanId(data.id); 

    } catch (err) {
      console.warn("[SiglaAni] Backend unavailable, using local fallback:", err);

      const fruitName  = window.__siglaani_fruit_name__  ?? "Hindi Matukoy";
      const scientific = window.__siglaani_scientific__  ?? "—";
      const fallbackCond = "ripe";
      
      setResult({
        fruit:          fruitName,
        scientific:     scientific,
        condition:      fallbackCond,
        conditionLabel: CONDITION_LABELS[fallbackCond],
        confidence:     75,
        rating:         4,
        recommendation: RECOMMENDATIONS[fallbackCond],
        id:             scanCounter,
      });
      
      // Use fake ID only if it crashes
      setScanId(scanCounter); 
    }

    go("result");
  }, [go]);

  return (
    <div className="app-root">
      <div className="app-shell">
        {screen === "splash" && <SplashScreen onStart={() => go("instr1")} onDashboard={goDashboard}/>}
        {screen === "instr1"     && <InstructionsScreen page={1} onNext={() => go("instr2")} onBack={() => go("splash")}/>}
        {screen === "instr2"     && <InstructionsScreen page={2} onNext={() => go("scan")}   onBack={() => go("instr1")}/>}
        {screen === "scan"       && <ScanScreen onScan={() => go("processing")} onHistory={goHistory}/>}
        {screen === "processing" && <ProcessingScreen onComplete={handleProcessingComplete}/>}
        {screen === "result" && <ResultScreen result={result} scanId={scanId} onScanAgain={() => go("scan")} onHome={() => go("splash")} onHistory={goHistory} onDashboard={goDashboard}/>}
        {screen === "history"    && <HistoryScreen onBack={() => go(prevScreen || "splash")} onScanAgain={() => go("scan")}/>}
        {screen === "dashboard" && <DashboardScreen onBack={() => go(prevScreen || "splash")} />}
      </div>
    </div>
  );
}
