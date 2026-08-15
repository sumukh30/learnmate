import { useState, useRef, useEffect } from "react";

const API_URL = "http://localhost:8000";
const MAX_ID_LEN = 15;
const ID_PATTERN = /^[A-Za-z0-9_@#*]*$/;

const QUOTES = [
  "The expert in anything was once a beginner.",
  "Small, steady questions beat one big cram session.",
  "Understanding beats memorizing, every time.",
];

function Logo({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 5.5C4 4.67 4.67 4 5.5 4H11V19H5.5C4.67 19 4 18.33 4 17.5V5.5Z"
        stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"
      />
      <path
        d="M20 5.5C20 4.67 19.33 4 18.5 4H13V19H18.5C19.33 19 20 18.33 20 17.5V5.5Z"
        stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"
      />
      <circle cx="12" cy="10" r="1.4" fill="currentColor" />
    </svg>
  );
}

function parseQuizQuestions(text) {
  const matches = [...text.matchAll(/Q(\d+):\s*(.+?)\s*Answer:\s*(.+?)(?=Q\d+:|\(note:|\(source:|$)/gs)];
  if (matches.length < 2) return null;
  return matches.map((m) => ({
    number: m[1],
    question: m[2].trim(),
    answer: m[3].trim(),
  }));
}

function extractTag(text, tag) {
  const re = new RegExp(`\\(${tag}:(.+)\\)\\s*$`, "s");
  const m = text.match(re);
  return m ? m[1].trim() : null;
}

function QuizWorksheet({ questions, note, source }) {
  const [revealed, setRevealed] = useState({});
  const toggle = (n) => setRevealed((r) => ({ ...r, [n]: !r[n] }));

  return (
    <div className="worksheet">
      <div className="worksheet-head">
        <span className="worksheet-tag">quiz</span>
        {source && <span className="worksheet-source">source: {source}</span>}
      </div>
      {questions.map((q) => (
        <div className="worksheet-item" key={q.number}>
          <div className="worksheet-q">
            <span className="worksheet-num">{q.number}</span>
            <span>{q.question}</span>
          </div>
          <button
            className={`reveal-btn ${revealed[q.number] ? "is-revealed" : ""}`}
            onClick={() => toggle(q.number)}
          >
            <span className="reveal-swipe" />
            <span className="reveal-text">
              {revealed[q.number] ? q.answer : "swipe to reveal"}
            </span>
          </button>
        </div>
      ))}
      {note && <div className="worksheet-note">⚑ you've been weak on: {note.replace(/^you've been weak on:\s*/i, "")}</div>}
    </div>
  );
}

function QACard({ question, answerText }) {
  let body = answerText;

  const noteMatch = body.match(/\(note:(.+?)\)\s*$/s);
  if (noteMatch) body = body.replace(noteMatch[0], "").trim();

  const source = extractTag(body, "source");
  if (source) body = body.replace(/\(source:.+\)\s*$/s, "").trim();

  const quiz = parseQuizQuestions(body);

  return (
    <div className="qa-card">
      <div className="qa-question">
        <span className="qa-q-mark">Q</span>
        {question}
      </div>
      <div className="qa-answer">
        {quiz ? (
          <QuizWorksheet
            questions={quiz}
            note={noteMatch ? noteMatch[1].trim() : null}
            source={source}
          />
        ) : (
          <>
            <div className="qa-answer-text">{body}</div>
            {source && <div className="qa-source">📄 {source}</div>}
          </>
        )}
      </div>
    </div>
  );
}

function StickyNote({ topic, onClick }) {
  const rotations = ["-3deg", "2deg", "-1.5deg", "3deg", "-2deg"];
  const rot = rotations[Math.abs(topic.length * 7) % rotations.length];
  return (
    <div className="sticky-note" style={{ "--rot": rot }} onClick={onClick}>
      {topic}
    </div>
  );
}

function validateId(value) {
  if (!value) return "Enter a student ID to continue.";
  if (value.length > MAX_ID_LEN) return `Keep it under ${MAX_ID_LEN} characters.`;
  if (!ID_PATTERN.test(value)) return "Only letters, numbers, _ @ # * are allowed.";
  return "";
}

export default function App() {
  const [studentId, setStudentId] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [pairs, setPairs] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [weakTopics, setWeakTopics] = useState([]);
  const [sampleTopics, setSampleTopics] = useState([]);
  const scrollRef = useRef(null);
  const quote = useRef(QUOTES[Math.floor(Math.random() * QUOTES.length)]).current;

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [pairs, loading]);

  useEffect(() => {
    if (!loggedIn) return;
    fetch(`${API_URL}/topics`)
      .then((r) => (r.ok ? r.json() : { topics: [] }))
      .then((d) => setSampleTopics(d.topics || []))
      .catch(() => setSampleTopics([]));
    refreshWeakTopics();
  }, [loggedIn]);

  async function callAsk(query) {
    const res = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, student_id: studentId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return (await res.json()).response;
  }

  async function refreshWeakTopics() {
    try {
      const text = await callAsk("what are my weak topics?");
      const match = text.match(/weakest on:\s*(.+?)\.?$/i);
      setWeakTopics(match ? match[1].split(",").map((t) => t.trim()).filter(Boolean) : []);
    } catch {
      // silent
    }
  }

  async function handleSend(e) {
    e.preventDefault();
    const query = input.trim();
    if (!query || loading) return;

    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await callAsk(query);
      setPairs((p) => [...p, { question: query, answer: response }]);
      refreshWeakTopics();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleLogin(e) {
    e.preventDefault();
    const trimmed = studentId.trim();
    const err = validateId(trimmed);
    if (err) {
      setLoginError(err);
      return;
    }
    setStudentId(trimmed);
    setLoggedIn(true);
  }

  function handleLogout() {
    setLoggedIn(false);
    setStudentId("");
    setPairs([]);
    setWeakTopics([]);
    setError(null);
    setInput("");
  }

  function handleIdChange(e) {
    const v = e.target.value;
    if (v.length > MAX_ID_LEN) return;
    setStudentId(v);
    if (v && !ID_PATTERN.test(v)) {
      setLoginError("Only letters, numbers, _ @ # * are allowed.");
    } else {
      setLoginError("");
    }
  }

  if (!loggedIn) {
    return (
      <div className="login-screen">
        <div className="grid-glow" aria-hidden="true" />
        <div className="login-card">
          <div className="login-mark"><Logo size={32} /></div>
          <h1>LearnMate</h1>
          <p className="login-sub">Ask doubts on your own notes. Get quizzed. Track what needs work.</p>
          <form onSubmit={handleLogin} noValidate>
            <label htmlFor="sid">student id</label>
            <input
              id="sid"
              autoFocus
              value={studentId}
              onChange={handleIdChange}
              placeholder="e.g. smith_23"
              maxLength={MAX_ID_LEN}
              aria-invalid={!!loginError}
              aria-describedby={loginError ? "sid-error" : undefined}
            />
            <div className="input-meta">
              <span>{loginError ? <span id="sid-error" className="login-error">{loginError}</span> :""}</span>
              <span className={`char-count ${studentId.length === MAX_ID_LEN ? "char-count-full" : ""}`}>{studentId.length}/{MAX_ID_LEN}</span>
            </div>
            <button type="submit">Start studying →</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark"><Logo /></span> LearnMate
        </div>
        <div className="header-right">
          <div className="student-chip">{studentId}</div>
          <button className="logout-btn" onClick={handleLogout} title="Log out" aria-label="Log out">⏻</button>
        </div>
      </header>

      <div className="app-body">
        <main className="chat-pane" ref={scrollRef}>
          {pairs.length === 0 && (
            <div className="landing">
              <p className="landing-quote">"{quote}"</p>
              <p className="landing-eyebrow">start here</p>

              <div className="tile-grid">
                <button className="tile tile-primary" onClick={() => setInput(sampleTopics[0] ? `what is ${sampleTopics[0]}?` : "what is overfitting?")}>
                  <span className="tile-icon">◆</span>
                  <span className="tile-label">Ask a doubt</span>
                  <span className="tile-hint">{sampleTopics[0] ? `e.g. "what is ${sampleTopics[0]}?"` : 'e.g. "what is overfitting?"'}</span>
                </button>
                <button className="tile" onClick={() => setInput(sampleTopics[1] ? `quiz me on ${sampleTopics[1]}` : "quiz me on generalization")}>
                  <span className="tile-icon">✎</span>
                  <span className="tile-label">Take a quiz</span>
                  <span className="tile-hint">{sampleTopics[1] ? `e.g. "quiz me on ${sampleTopics[1]}"` : 'e.g. "quiz me on generalization"'}</span>
                </button>
                <button className="tile" onClick={() => setInput(sampleTopics[2] ? `I'm not strong in ${sampleTopics[2]}` : "I'm not strong in backpropagation")}>
                  <span className="tile-icon">⚑</span>
                  <span className="tile-label">Flag a weak spot</span>
                  <span className="tile-hint">{sampleTopics[2] ? `e.g. "I'm not strong in ${sampleTopics[2]}"` : 'e.g. "I\'m not strong in backpropagation"'}</span>
                </button>
                <button className="tile" onClick={() => setInput("what are my weak topics?")}>
                  <span className="tile-icon">▤</span>
                  <span className="tile-label">Review progress</span>
                  <span className="tile-hint">"what are my weak topics?"</span>
                </button>
              </div>
            </div>
          )}

          {pairs.map((p, i) => (
            <QACard key={i} question={p.question} answerText={p.answer} />
          ))}

          {loading && (
            <div className="qa-card qa-card-loading">
              <div className="thinking">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          {error && <div className="error-banner">⚠ {error}</div>}
        </main>

        <aside className="margin-pane">
          <div className="margin-title">weak topics</div>
          {weakTopics.length === 0 ? (
            <div className="margin-empty">nothing pinned yet</div>
          ) : (
            <div className="sticky-board">
              {weakTopics.map((t) => (
                <StickyNote key={t} topic={t} onClick={() => setInput(`quiz me on ${t}`)} />
              ))}
            </div>
          )}
        </aside>
      </div>

      <form className="composer" onSubmit={handleSend}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a doubt, request a quiz, or report an answer…"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>Send</button>
      </form>
    </div>
  );
}