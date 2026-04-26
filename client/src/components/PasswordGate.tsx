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
        style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
      >
        <input
          type="password"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          autoFocus
          placeholder="Password"
          style={{
            padding: "0.5rem 0.75rem",
            fontSize: "1rem",
            border: error ? "1px solid #d33" : "1px solid #ccc",
            borderRadius: "4px",
            outline: "none",
          }}
        />
        {error && <span style={{ color: "#d33", fontSize: "0.85rem" }}>Incorrect</span>}
      </form>
    </div>
  );
}
