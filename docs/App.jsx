import { useState, useEffect, useRef } from "react";

const CATEGORIES = [
  { id: "Technology", icon: "◆", accent: "#0ea5e9" },
  { id: "Politics", icon: "◆", accent: "#8b5cf6" },
  { id: "Business", icon: "◆", accent: "#10b981" },
  { id: "Science", icon: "◆", accent: "#f59e0b" },
  { id: "Sports", icon: "◆", accent: "#ef4444" },
  { id: "Health", icon: "◆", accent: "#ec4899" },
  { id: "Entertainment", icon: "◆", accent: "#6366f1" },
  { id: "World News", icon: "◆", accent: "#14b8a6" },
];

// IMPORTANT: Update this URL after deploying your Flask API to Render
const API_BASE = "https://ai-news-summarisation-tool.onrender.com";

export default function App() {
  const [selected, setSelected] = useState(null);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [time, setTime] = useState(new Date());
  const contentRef = useRef(null);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  const fetchArticles = async (category) => {
    setSelected(category);
    setLoading(true);
    setError(null);
    setArticles([]);

    try {
      const res = await fetch(`${API_BASE}/api/articles?category=${encodeURIComponent(category)}&limit=5`);
      if (!res.ok) throw new Error("Failed to fetch articles");
      const data = await res.json();
      setArticles(data.articles || []);
      if ((data.articles || []).length === 0) {
        setError("No articles found for this category yet.");
      }
    } catch (err) {
      setError("Could not connect to the API. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
    } catch {
      return dateStr;
    }
  };

  const greeting = () => {
    const h = time.getHours();
    if (h < 12) return "Good morning";
    if (h < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a0c",
      color: "#e4e4e7",
      fontFamily: "'Syne', sans-serif",
      position: "relative",
      overflow: "hidden",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Source+Serif+4:ital,wght@0,300;0,400;1,300;1,400&display=swap');

        * { margin: 0; padding: 0; box-sizing: border-box; }

        .grain {
          position: fixed; top: 0; left: 0; width: 100%; height: 100%;
          opacity: 0.03; pointer-events: none; z-index: 100;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        }

        .glow-orb {
          position: fixed; width: 600px; height: 600px; border-radius: 50%;
          filter: blur(120px); opacity: 0.07; pointer-events: none; z-index: 0;
        }

        .cat-btn {
          padding: 10px 20px; border: 1px solid rgba(255,255,255,0.08);
          background: rgba(255,255,255,0.03); border-radius: 100px;
          color: #a1a1aa; font-family: 'Syne', sans-serif; font-size: 14px;
          font-weight: 500; cursor: pointer; transition: all 0.3s ease;
          backdrop-filter: blur(10px); letter-spacing: 0.02em;
        }
        .cat-btn:hover {
          border-color: rgba(255,255,255,0.2); color: #e4e4e7;
          background: rgba(255,255,255,0.06); transform: translateY(-1px);
        }
        .cat-btn.active {
          color: #fff; border-color: var(--accent);
          background: color-mix(in srgb, var(--accent) 15%, transparent);
          box-shadow: 0 0 20px color-mix(in srgb, var(--accent) 20%, transparent);
        }

        .article-card {
          padding: 28px 32px; border-bottom: 1px solid rgba(255,255,255,0.05);
          transition: all 0.3s ease; position: relative;
        }
        .article-card:hover {
          background: rgba(255,255,255,0.02);
        }
        .article-card:last-child { border-bottom: none; }

        .article-num {
          font-family: 'Syne', sans-serif; font-size: 48px; font-weight: 800;
          color: rgba(255,255,255,0.04); position: absolute; right: 32px; top: 20px;
          line-height: 1;
        }

        .article-source {
          font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em;
          color: #71717a; font-weight: 600; margin-bottom: 8px;
        }

        .article-title {
          font-family: 'Source Serif 4', serif; font-size: 20px; font-weight: 400;
          color: #fafafa; line-height: 1.4; margin-bottom: 12px;
          max-width: 85%;
        }

        .article-summary {
          font-size: 14px; line-height: 1.7; color: #a1a1aa;
          max-width: 80%; margin-bottom: 16px;
        }

        .article-link {
          font-size: 12px; color: #71717a; text-decoration: none;
          font-weight: 500; letter-spacing: 0.05em; transition: color 0.2s;
          display: inline-flex; align-items: center; gap: 6px;
        }
        .article-link:hover { color: #e4e4e7; }

        .loader {
          width: 24px; height: 24px; border: 2px solid rgba(255,255,255,0.1);
          border-top-color: rgba(255,255,255,0.5); border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .fade-up {
          animation: fadeUp 0.5s ease forwards;
          opacity: 0;
        }

        .date-pill {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 6px 14px; border-radius: 100px; font-size: 12px;
          background: rgba(255,255,255,0.04); color: #71717a;
          border: 1px solid rgba(255,255,255,0.06);
          font-weight: 500; letter-spacing: 0.03em;
        }

        .header-rule {
          height: 1px; background: linear-gradient(90deg, 
            transparent, rgba(255,255,255,0.08) 20%, rgba(255,255,255,0.08) 80%, transparent);
          margin: 0;
        }
      `}</style>

      <div className="grain" />
      <div className="glow-orb" style={{
        background: selected ? CATEGORIES.find(c => c.id === selected)?.accent : "#6366f1",
        top: "-200px", left: "-200px",
        transition: "background 1s ease",
      }} />
      <div className="glow-orb" style={{
        background: selected ? CATEGORIES.find(c => c.id === selected)?.accent : "#0ea5e9",
        bottom: "-300px", right: "-200px",
        transition: "background 1s ease",
      }} />

      <div style={{ position: "relative", zIndex: 1, maxWidth: 900, margin: "0 auto", padding: "0 24px" }}>

        {/* Header */}
        <header style={{ paddingTop: 64, paddingBottom: 40 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 }}>
            <div>
              <p style={{ fontSize: 13, color: "#52525b", fontWeight: 600, letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 8 }}>
                AI News Summariser
              </p>
              <h1 style={{ fontSize: 42, fontWeight: 800, letterSpacing: "-0.03em", lineHeight: 1.1, color: "#fafafa" }}>
                {greeting()}.
              </h1>
              <p style={{ fontSize: 16, color: "#71717a", marginTop: 8, fontWeight: 400 }}>
                Select a topic to read today's summarised headlines.
              </p>
            </div>
            <div className="date-pill">
              {time.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" })}
            </div>
          </div>

          {/* Category buttons */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                className={`cat-btn ${selected === cat.id ? "active" : ""}`}
                style={{ "--accent": cat.accent }}
                onClick={() => fetchArticles(cat.id)}
              >
                {cat.id}
              </button>
            ))}
          </div>
        </header>

        <div className="header-rule" />

        {/* Content */}
        <div ref={contentRef} style={{ paddingBottom: 80 }}>

          {/* Empty state */}
          {!selected && !loading && (
            <div style={{ textAlign: "center", padding: "80px 20px" }}>
              <p style={{ fontSize: 14, color: "#3f3f46" }}>
                ↑ Choose a category to get started
              </p>
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div style={{ display: "flex", justifyContent: "center", padding: "80px 20px" }}>
              <div className="loader" />
            </div>
          )}

          {/* Error */}
          {error && !loading && (
            <div style={{ textAlign: "center", padding: "60px 20px" }}>
              <p style={{ fontSize: 14, color: "#71717a" }}>{error}</p>
            </div>
          )}

          {/* Articles */}
          {!loading && articles.length > 0 && (
            <div>
              <div style={{
                padding: "20px 32px", display: "flex", justifyContent: "space-between",
                alignItems: "center",
              }}>
                <p style={{ fontSize: 12, color: "#52525b", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase" }}>
                  {selected} — Top {articles.length} articles
                </p>
              </div>
              {articles.map((article, i) => (
                <div
                  key={i}
                  className="article-card fade-up"
                  style={{ animationDelay: `${i * 0.08}s` }}
                >
                  <div className="article-num">{String(i + 1).padStart(2, "0")}</div>
                  <div className="article-source">
                    {article.source || "Unknown source"} · {formatDate(article.published_at)}
                  </div>
                  <h2 className="article-title">{article.title}</h2>
                  {article.summary && (
                    <p className="article-summary">{article.summary}</p>
                  )}
                  {article.url && (
                    <a
                      className="article-link"
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Read original article →
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          borderTop: "1px solid rgba(255,255,255,0.05)", padding: "24px 0",
          textAlign: "center", fontSize: 11, color: "#3f3f46", letterSpacing: "0.05em",
        }}>
          Built with Python · MongoDB · Gemini Flash · Sentence Transformers
        </div>
      </div>
    </div>
  );
}
