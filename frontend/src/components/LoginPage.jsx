function LoginPage({ apiInfo, error, googleClientId }) {
  return (
    <div className="login-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <main className="login-layout">
        <section className="login-hero panel">
          <p className="eyebrow">AI Day Planner</p>
          <h1>Plan Smarter Days With One Prompt</h1>
          <p className="hero-copy">
            This app uses live weather, place discovery, and Google Calendar execution. Sign in with your Google account
            to save your personal planning history and create events instantly.
          </p>

          <div className="feature-grid">
            <article>
              <h3>Intent to Structure</h3>
              <p>Gemini interprets your natural language and extracts actionable fields.</p>
            </article>
            <article>
              <h3>Context Aware</h3>
              <p>Weather and place APIs shape better activity recommendations.</p>
            </article>
            <article>
              <h3>Real Execution</h3>
              <p>Confirmed plans become calendar events and are stored in your history.</p>
            </article>
          </div>
        </section>

        <section className="login-card panel">
          <p className="section-label">Account Login</p>
          <h2>Continue With Google</h2>
          <p>Only Google OAuth is supported. Your account is required for plan execution and history tracking.</p>

          {!googleClientId ? (
            <div className="error-banner">Set VITE_GOOGLE_WEB_CLIENT_ID in frontend/.env and restart the frontend.</div>
          ) : (
            <div id="google-signin-button" className="google-button-wrap" />
          )}

          <p className="login-hint">
            Use a Google OAuth Web client (not Desktop) and add http://127.0.0.1:5173 in Authorized JavaScript origins.
          </p>

          {error ? <div className="error-banner">{error}</div> : null}

          <div className="login-footer">
            <span className="status-pill">{apiInfo ? 'Backend Connected' : 'Checking Backend...'}</span>
          </div>
        </section>
      </main>
    </div>
  );
}

export default LoginPage;
