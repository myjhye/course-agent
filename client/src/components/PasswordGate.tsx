import { useState, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

export function PasswordGate({ children }: Props) {
  const [passed, setPassed] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const expected = import.meta.env.VITE_GATE_PASSWORD;
    if (input === expected) {
      setPassed(true);
      setError(false);
    } else {
      setError(true);
      setInput("");
    }
  };

  if (passed) return <>{children}</>;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        background: "#fafafa",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{ display: "flex", flexDirection: "column", gap: "0.5rem", width: "100%", maxWidth: "320px", padding: "1.5rem" }}
      >
        <div style={{ textAlign: "center", marginBottom: "0.5rem" }}>
          <p style={{ margin: 0, fontSize: "1.1rem", fontWeight: "600", color: "#333" }}>접속 패스워드를 입력해주세요.</p>
          <p style={{ margin: "0.25rem 0 0.75rem 0", fontSize: "0.85rem", color: "#666", lineHeight: "1.4" }}>
            패스워드는 포트폴리오에 명시되어 있습니다.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", width: "100%", justifyContent: "center" }}>
          <input
            type="password"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            autoFocus
            placeholder="Password"
            style={{
              flex: 1,
              width: "100%",
              padding: "0.5rem 0.75rem",
              fontSize: "1rem",
              border: error ? "1px solid #d33" : "1px solid #ccc",
              borderRadius: "4px",
              outline: "none",
              boxSizing: "border-box",
              height: "38px",
            }}
          />
          <button
            type="submit"
            style={{
              padding: "0.5rem 1.8rem",
              fontSize: "1rem",
              fontWeight: "600",
              color: "#fff",
              background: "#3b82f6",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              transition: "background 0.2s",
              whiteSpace: "nowrap",
              height: "38px",
              boxSizing: "border-box",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "#2563eb")}
            onMouseOut={(e) => (e.currentTarget.style.background = "#3b82f6")}
          >
            확인
          </button>
        </div>
        {error && <span style={{ color: "#d33", fontSize: "0.85rem", textAlign: "center", display: "block", marginTop: "0.25rem" }}>Incorrect</span>}
      </form>
    </div>
  );
}
