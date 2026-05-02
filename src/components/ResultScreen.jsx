import LeafSVG from './shared/LeafSVG';
import { badge } from '../constants';


// ── Likert rating config ──────────────────────────────────────────────────────
const LIKERT = [
  { stars: 1, label: "Hindi Nakakain",  color: "#ef5350" },
  { stars: 2, label: "Medyo Luma",    color: "#f97316" },
  { stars: 3, label: "Katamtaman",      color: "#f9a825" },
  { stars: 4, label: "Sariwa",          color: "#66bb6a" },
  { stars: 5, label: "Napakasariwa",    color: "#5cb83a" },
];

function StarRating({ rating = 3 }) {
  const info  = LIKERT[Math.min(Math.max(rating, 1), 5) - 1];
  return (
    <div className="star-rating-wrap">
      <div className="star-row">
        {[1,2,3,4,5].map(n => (
          <svg key={n} width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 2l2.9 6.1L22 9.3l-5 4.9 1.2 6.8L12 17.8l-6.2 3.2L7 14.2 2 9.3l7.1-1.2z"
              fill={n <= rating ? info.color : "rgba(255,255,255,0.12)"}
              stroke={n <= rating ? info.color : "rgba(255,255,255,0.15)"}
              strokeWidth="1"
            />
          </svg>
        ))}
      </div>
      <div className="star-label" style={{ color: info.color }}>{info.label}</div>
    </div>
  );
}

// ── Result Screen ─────────────────────────────────────────────────────────────
export default function ResultScreen({ result, scanId, onScanAgain, onHome, onHistory, onDashboard }) {
  const now    = new Date().toLocaleTimeString("en-PH", { hour:"2-digit", minute:"2-digit" });
  const b      = badge(result?.condition ?? "ripe");
  const rating = result?.rating ?? 3;

  return (
    <div className="screen result-screen">

      {/* ── Top bar ── */}
      <div className="result-header">
        <div className="header-logo">
          <LeafSVG size={22}/>
          <span className="header-logo-text">SIGLA ANI</span>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <button className="tb-hist-btn tb-hist-btn--dark" onClick={onHistory}>
            <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
              <rect x="2" y="4"    width="16" height="2.5" rx="1.2" fill="currentColor"/>
              <rect x="2" y="8.75" width="16" height="2.5" rx="1.2" fill="currentColor"/>
              <rect x="2" y="13.5" width="10" height="2.5" rx="1.2" fill="currentColor"/>
            </svg>
            History
          </button>
          <div className={`result-badge ${b.cls}`}>{b.label}</div>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="result-body">

        {/* Left — captured photo */}
        <div className="res-left">
          {window.__siglaani_capture__
            ? <img src={window.__siglaani_capture__} className="res-captured" alt="scan"/>
            : result?.thumbnail
            ? <img src={`data:image/jpeg;base64,${result.thumbnail}`} className="res-captured" alt="scan"/>
            : <div className="result-fruit-img"><div className="result-fruit-shine"/></div>
          }
        </div>

        {/* Right — info */}
        <div className="res-right">

          {/* Fruit name + badge */}
          <div className="res-name-row">
            <div>
              <div className="result-fruit-name">{result?.fruit ?? "Unknown"}</div>
              <div className="result-fruit-sci">{result?.scientific ?? ""}</div>
            </div>
            <div className={`result-badge ${b.cls}`} style={{ alignSelf:"flex-start" }}>{b.label}</div>
          </div>

          {/* Star / Likert rating */}
          <StarRating rating={rating}/>

          {/* Suggestion */}
          <div className="res-suggestion">
            <div className="res-suggestion-label">Rekomendasyon</div>
            <div className="res-suggestion-text">
              {result?.recommendation ?? "—"}
            </div>
          </div>

          {/* Time + ID */}
          <div className="res-meta-row">
            <div className="res-meta-cell">
              <div className="res-meta-label">Oras ng Scan</div>
              <div className="res-meta-val">{now}</div>
            </div>
            <div className="res-meta-cell">
              <div className="res-meta-label">Scan ID</div>
              <div className="res-meta-val">#{String(result?.id ?? scanId).padStart(4,"0")}</div>
            </div>
            <div className="res-meta-cell">
              <div className="res-meta-label">Confidence</div>
              <div className="res-meta-val">{result?.confidence ?? "—"}%</div>
            </div>
          </div>

          {/* Footer buttons */}
          <div className="result-footer">
            <button className="scan-again-btn" onClick={onScanAgain}>+ I-scan Muli</button>
            <button 
              onClick={onDashboard} 
              style={{ 
                display: 'flex', alignItems: 'center', gap: '8px', 
                padding: '12px 20px', borderRadius: '12px', 
                border: '1px solid #d1e8ce', backgroundColor: '#f9f9f9', 
                color: '#555', fontSize: '16px', cursor: 'pointer', fontWeight: 'bold' 
              }}>
              📊 Dashboard
            </button>
            <button className="history-btn"    onClick={onHome}>🏠 Home</button>
          </div>

        </div>
      </div>
    </div>
  );
}
