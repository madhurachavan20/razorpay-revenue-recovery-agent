import { useState } from "react";
import { login } from "./services/api";
import "./Login.css";

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      const data = await login(email, password);

      localStorage.setItem(
        "revenueos_token",
        data.access_token
      );

      localStorage.setItem(
        "revenueos_user",
        JSON.stringify(data.user)
      );

      onLogin(data.user);
    } catch (err) {
      setError(err.message || "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="loginPage">
      <div className="loginCard">

        <div className="loginLogo">
          R
        </div>

        <h1>RevenueOS</h1>

        <p className="loginSubtitle">
          AI-Powered Revenue Recovery
        </p>

        <form onSubmit={handleSubmit}>

          <label>Email</label>

          <input
            type="email"
            placeholder="admin@revenueos.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <label>Password</label>

          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {error && (
            <div className="loginError">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="loginButton"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>

        </form>

        <div className="loginFooter">
          Secure Revenue Recovery Platform
        </div>

      </div>
    </div>
  );
}

export default Login;