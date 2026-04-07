import { useState } from 'react';

function LoginPage({ apiInfo, error, googleClientId, googleReady }) {
  const [theme, setTheme] = useState('dark');
  const isDarkTheme = theme === 'dark';

  return (
    <div className={`login-shell ${isDarkTheme ? 'login-theme-dark' : 'login-theme-light'}`}>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <main className="login-layout">
        <div className="login-topbar">
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme(isDarkTheme ? 'light' : 'dark')}
          >
            {isDarkTheme ? 'Switch to Light' : 'Switch to Dark'}
          </button>
        </div>

        <section className="login-card panel">
          <div className="login-logo" aria-hidden="true">
            <span>G</span>
          </div>
          <p className="login-brand">AI Day Planner</p>
          <h1 className="login-title">Sign in</h1>
          <p className="hero-copy">
            Sign in with Google to use the planner, save your history, and create calendar events.
          </p>

          <div className="auth-form">
            {!googleClientId ? (
              <div className="error-banner">Set VITE_GOOGLE_WEB_CLIENT_ID in frontend/.env and restart the frontend.</div>
            ) : (
              <>
                <div id="google-signin-button" className="google-button-wrap" />
                {!googleReady ? <p className="login-hint">Loading Google sign-in...</p> : null}
              </>
            )}

            {error ? <div className="error-banner">{error}</div> : null}

            <div className="login-footer">
              <span className="status-pill">{apiInfo ? 'Backend Connected' : 'Checking Backend...'}</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default LoginPage;
