  import { useEffect, useMemo, useState } from 'react';
  import {
    authWithGoogle,
    executePlan,
    getApiInfo,
    getAuthToken,
    getMe,
    getPlanHistory,
    previewPlan,
    revisePlan,
    setAuthToken,
  } from './lib/api';
  import LoginPage from './components/LoginPage';

  const samplePrompt = 'I want to go hiking this weekend but only if it is not raining, otherwise suggest something indoors and block 10 to 2';
  const googleClientId = import.meta.env.VITE_GOOGLE_WEB_CLIENT_ID || import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

  const flowTemplate = [
    { key: 'intent', label: 'Understanding your request' },
    { key: 'weather', label: 'Checking weather context' },
    { key: 'decision', label: 'Building recommendation' },
    { key: 'places', label: 'Finding nearby options' },
  ];

  function withIdleFlowState() {
    return flowTemplate.map((step) => ({ ...step, status: 'idle', durationMs: null }));
  }

  function buildTechnicalErrorDetails(errorValue) {
    if (!errorValue) {
      return '';
    }

    const payload = {
      message: errorValue.message || 'Unknown error',
      stage: errorValue.stage || null,
      statusCode: errorValue.statusCode || null,
      backendDetail: errorValue.backendDetail ?? null,
    };

    return JSON.stringify(payload, null, 2);
  }

  function formatPlaceType(place) {
    if (!place) return 'Venue';

    if (place.place_type) {
      const type = place.place_type;
      return type
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    }

    return 'Venue';
  }

  function App() {
    const [userInput, setUserInput] = useState(samplePrompt);
    const [city, setCity] = useState('Mumbai');
    const [cityEdited, setCityEdited] = useState(false);
    const [latitude, setLatitude] = useState('');
    const [longitude, setLongitude] = useState('');
    const [apiInfo, setApiInfo] = useState(null);
    const [error, setError] = useState('');
    const [user, setUser] = useState(null);
    const [history, setHistory] = useState([]);
    const [googleReady, setGoogleReady] = useState(false);
    const [preview, setPreview] = useState(null);
    const [calendarLink, setCalendarLink] = useState('');
    const [confirmStatus, setConfirmStatus] = useState('');
    const [planSuggestion, setPlanSuggestion] = useState('');
    const [processing, setProcessing] = useState(false);
    const [errorDetails, setErrorDetails] = useState('');
    const [flowSteps, setFlowSteps] = useState(withIdleFlowState);
    const [flowMessage, setFlowMessage] = useState('Describe your need, then generate a plan.');
    const [activePlanInput, setActivePlanInput] = useState('');
    const [selectedPlaceIndex, setSelectedPlaceIndex] = useState(0);
    const [showInputSection, setShowInputSection] = useState(true);
    const [showFlowDetails, setShowFlowDetails] = useState(false);
    const [activeView, setActiveView] = useState('planner');

    const coordinates = useMemo(() => {
      const lat = latitude.trim() === '' ? undefined : Number(latitude);
      const lng = longitude.trim() === '' ? undefined : Number(longitude);
      return {
        latitude: Number.isFinite(lat) ? lat : undefined,
        longitude: Number.isFinite(lng) ? lng : undefined,
      };
    }, [latitude, longitude]);

    const totalFlowDurationMs = useMemo(
      () => flowSteps.reduce((sum, step) => sum + (typeof step.durationMs === 'number' ? step.durationMs : 0), 0),
      [flowSteps]
    );

    useEffect(() => {
      getApiInfo()
        .then(setApiInfo)
        .catch(() => setApiInfo(null));
    }, []);

    useEffect(() => {
      if (!googleClientId) {
        return;
      }

      const initializeGoogle = () => {
        if (!window.google?.accounts?.id) {
          return;
        }

        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: async ({ credential }) => {
            console.log("GOOGLE ID TOKEN:", credential);
            try {
              const authData = await authWithGoogle(credential);
              setAuthToken(authData.access_token);
              setUser(authData.user);
              setError('');
              const historyData = await getPlanHistory();
              setHistory(historyData.items || []);
            } catch (errorValue) {
              setError(errorValue.message || 'Google login failed');
            }
          },
        });

        setGoogleReady(true);
      };

      if (window.google?.accounts?.id) {
        initializeGoogle();
        return;
      }

      const existingScript = document.getElementById('google-oauth-script');
      if (existingScript) {
        existingScript.addEventListener('load', initializeGoogle);
        return () => existingScript.removeEventListener('load', initializeGoogle);
      }

      const script = document.createElement('script');
      script.id = 'google-oauth-script';
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = initializeGoogle;

      document.body.appendChild(script);
      return undefined;
    }, []);

    useEffect(() => {
      if (!googleReady || user || !window.google?.accounts?.id) {
        return;
      }

      const buttonNode = document.getElementById('google-signin-button');
      if (!buttonNode) {
        return;
      }

      buttonNode.innerHTML = '';
      window.google.accounts.id.renderButton(buttonNode, {
        theme: 'filled_black',
        size: 'large',
        shape: 'pill',
        text: 'continue_with',
        width: 320,
      });
    }, [googleReady, user]);

    useEffect(() => {
      const token = getAuthToken();
      if (!token) {
        return;
      }

      getMe()
        .then(setUser)
        .then(() => getPlanHistory())
        .then((data) => setHistory(data.items || []))
        .catch(() => {
          setAuthToken('');
          setUser(null);
          setHistory([]);
        });
    }, []);

    function signOut() {
      setAuthToken('');
      setUser(null);
      setHistory([]);
      setError('');
      setErrorDetails('');
      setPreview(null);
      setCalendarLink('');
      setConfirmStatus('');
      setPlanSuggestion('');
      setActivePlanInput('');
      setActiveView('planner');
      setShowInputSection(true);
      setShowFlowDetails(false);
      setSelectedPlaceIndex(0);
      setFlowSteps(withIdleFlowState());
      setFlowMessage('Describe your need, then generate a plan.');
      setCityEdited(false);
    }

    function startFlowProcessing() {
      setShowFlowDetails(false);
      setFlowSteps(flowTemplate.map((step, index) => ({ ...step, status: index === 0 ? 'active' : 'idle', durationMs: null })));
    }

    function applyTraceSteps(traceSteps) {
      setFlowSteps(
        flowTemplate.map((step) => {
          const match = traceSteps?.find((traceStep) => traceStep.key === step.key);
          return {
            ...step,
            status: match ? 'done' : 'idle',
            durationMs: match ? match.duration_ms : null,
          };
        })
      );
    }

    function failFlowProcessing(failedStage) {
      setShowFlowDetails(true);
      setFlowSteps((previous) => {
        if (failedStage) {
          const failedIndex = previous.findIndex((step) => step.key === failedStage);
          if (failedIndex !== -1) {
            return previous.map((step, index) => {
              if (index < failedIndex) {
                return { ...step, status: 'done' };
              }
              if (index === failedIndex) {
                return { ...step, status: 'failed' };
              }
              return { ...step, status: 'idle' };
            });
          }
        }

        const activeIndex = previous.findIndex((step) => step.status === 'active');
        if (activeIndex === -1) {
          return previous.map((step, index) => ({ ...step, status: index === 0 ? 'failed' : step.status }));
        }
        return previous.map((step, index) => {
          if (index === activeIndex) {
            return { ...step, status: 'failed' };
          }
          return step;
        });
      });
    }

    async function runPlan(mode) {
      if (!userInput.trim()) {
        setError('Please describe what you want to do.');
        return;
      }

      if (mode === 'revise' && !planSuggestion.trim()) {
        setError('Add a suggestion before asking for a revised plan.');
        return;
      }

      setProcessing(true);
      setError('');
      setErrorDetails('');
      setConfirmStatus('');
      setCalendarLink('');
      setFlowMessage(mode === 'revise' ? 'Reworking plan with your suggestion...' : 'Generating your plan...');
      startFlowProcessing();

      try {
        const payload = {
          user_input: userInput.trim(),
          city: cityEdited ? (city.trim() || undefined) : undefined,
          latitude: coordinates.latitude,
          longitude: coordinates.longitude,
        };

        let data;
        if (mode === 'revise') {
          data = await revisePlan({
            ...payload,
            suggestion: planSuggestion.trim(),
          });
          setActivePlanInput(`${payload.user_input}\nUser feedback: ${planSuggestion.trim()}`);
        } else {
          data = await previewPlan(payload);
          setActivePlanInput(payload.user_input);
        }

        applyTraceSteps(data.trace_steps || []);
        setPreview(data);
        setSelectedPlaceIndex(data.selected_place_index ?? 0);
        setShowInputSection(false);
        const totalDuration = (data.trace_steps || []).reduce((sum, step) => sum + (step.duration_ms || 0), 0);
        setFlowMessage(`Plan ready in ${totalDuration} ms. Confirm it or suggest a change.`);
        setPlanSuggestion('');
      } catch (errorValue) {
        const failedStage = errorValue?.stage;
        failFlowProcessing(failedStage);
        setError(errorValue.message || 'Unable to generate a plan right now');
        setErrorDetails(buildTechnicalErrorDetails(errorValue));
        setFlowMessage(
          failedStage
            ? `Plan generation failed at ${failedStage}. Update your input and try again.`
            : 'Plan generation failed. Update your input and try again.'
        );
      } finally {
        setProcessing(false);
      }
    }

    async function confirmPlan() {
      if (!preview) {
        setError('Generate a plan before confirming.');
        return;
      }

      if (!user) {
        setError('Please sign in with Google before confirming a plan.');
        return;
      }

      setProcessing(true);
      setError('');
      setErrorDetails('');
      setConfirmStatus('Creating calendar event...');

      try {
        const payload = {
          user_input: activePlanInput || userInput.trim(),
          city: cityEdited ? (city.trim() || undefined) : preview.city || undefined,
          latitude: coordinates.latitude,
          longitude: coordinates.longitude,
          selected_place_index: selectedPlaceIndex,
        };

        const data = await executePlan(payload);
        setPreview(data);
        setSelectedPlaceIndex(data.selected_place_index ?? selectedPlaceIndex);
        applyTraceSteps(data.trace_steps || []);
        setCalendarLink(data.calendar_link || '');
        setConfirmStatus('Plan confirmed and saved to your calendar.');

        const historyData = await getPlanHistory();
        setHistory(historyData.items || []);
      } catch (errorValue) {
        if (errorValue?.stage === 'calendar') {
          setError(`Calendar step failed: ${errorValue.message || 'Could not confirm this plan'}`);
        } else {
          setError(errorValue.message || 'Could not confirm this plan');
        }
        setErrorDetails(buildTechnicalErrorDetails(errorValue));
        setConfirmStatus('');
      } finally {
        setProcessing(false);
      }
    }

    if (!user) {
      return (
        <LoginPage
          apiInfo={apiInfo}
          error={error}
          googleClientId={googleClientId}
          googleReady={googleReady}
        />
      );
    }

    return (
      <div className="app-shell">
        <div className="ambient ambient-one" />
        <div className="ambient ambient-two" />

        <header className="hero">
          <div>
            <p className="eyebrow">Guided AI Planner</p>
            <h1>Plan your day in one flow</h1>
            <p className="hero-copy">
              Tell us what you need, watch the processing flow, then confirm the plan or suggest changes.
            </p>
          </div>
          <div className="top-right">
            <div className="status-card">
              <span className="status-dot" />
              <div>
                <p>Backend</p>
                <strong>{apiInfo ? 'Connected' : 'Checking...'}</strong>
              </div>
            </div>
            <div className="user-chip">
              {user.picture_url ? <img src={user.picture_url} alt={user.name} className="avatar" /> : null}
              <div>
                <strong>{user.name}</strong>
                <p>{user.email}</p>
              </div>
              <button type="button" className="ghost-button" onClick={signOut}>
                Sign out
              </button>
            </div>
          </div>
        </header>

        <div className="workspace-shell">
          <aside className="panel side-panel">
            <p className="section-label">Navigation</p>
            <div className="side-nav-actions">
              <button
                type="button"
                className={`side-nav-button ${activeView === 'planner' ? 'side-nav-button-active' : ''}`}
                onClick={() => setActiveView('planner')}
              >
                Planner
              </button>
              <button
                type="button"
                className={`side-nav-button ${activeView === 'history' ? 'side-nav-button-active' : ''}`}
                onClick={() => setActiveView('history')}
              >
                History
              </button>
            </div>
          </aside>

          <div className="workspace-main">
            {activeView === 'planner' ? (
              <main className="layout single-panel-layout">
                <section className="panel composer unified-panel">
            {/* SECTION 1: Input Form (collapsible after generate) */}
            {showInputSection && (
              <div className="panel-section input-section">
                <div className="panel-header">
                  <div>
                    <p className="section-label">STEP 1</p>
                    <h2>Describe your need</h2>
                  </div>
                  <button className="ghost-button" onClick={() => setUserInput(samplePrompt)} type="button" disabled={processing}>
                    Use sample
                  </button>
                </div>

                <label className="field">
                  <span>Your request</span>
                  <textarea
                    value={userInput}
                    onChange={(event) => setUserInput(event.target.value)}
                    rows={5}
                    placeholder="I want an outdoor activity this Saturday, but switch to indoor if it rains"
                  />
                </label>

                <div className="grid-two">
                  <label className="field">
                    <span>City</span>
                    <input
                      value={city}
                      onChange={(event) => {
                        setCity(event.target.value);
                        setCityEdited(true);
                      }}
                      placeholder="Mumbai"
                    />
                  </label>
                  <label className="field">
                    <span>Latitude (optional)</span>
                    <input value={latitude} onChange={(event) => setLatitude(event.target.value)} placeholder="19.0330" />
                  </label>
                  <label className="field">
                    <span>Longitude (optional)</span>
                    <input value={longitude} onChange={(event) => setLongitude(event.target.value)} placeholder="73.0297" />
                  </label>
                </div>

                <div className="actions">
                  <button type="button" className="primary" onClick={() => runPlan('generate')} disabled={processing}>
                    {processing ? 'Generating...' : 'Generate Plan'}
                  </button>
                </div>
              </div>
            )}

            {/* SECTION 2: Processing Flow Timeline */}
            {!showInputSection && (
              <div className="panel-section flow-section">
                <div className="flow-header">
                  <h3>Processing flow</h3>
                  <button
                    type="button"
                    className="flow-toggle"
                    onClick={() => setShowFlowDetails((value) => !value)}
                  >
                    {showFlowDetails ? 'Hide details' : 'Show details'}
                  </button>
                </div>
                <div className="flow-summary">
                  <span>{processing ? 'Processing your request...' : 'Total processing time'}</span>
                  <strong>{processing ? 'Running' : `${totalFlowDurationMs} ms`}</strong>
                </div>
                {showFlowDetails ? (
                  <ul className="flow-list compact">
                    {flowSteps.map((step) => (
                      <li key={step.key} className={`flow-item flow-${step.status}`}>
                        <span className="flow-dot" />
                        <span>{step.label}</span>
                        {typeof step.durationMs === 'number' ? <small className="flow-time">{step.durationMs} ms</small> : null}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            )}

            {/* SECTION 3: Plan Decision with Place Selection */}
            {!showInputSection && preview && (
              <div className="panel-section decision-section">
                <div className="decision-header">
                  <p className="section-label">STEP 2</p>
                  <h3>Your plan</h3>
                </div>

                <div className="plan-summary">
                  <div className="summary-row">
                    <span className="label">Activity</span>
                    <strong className="value">{preview.decision}</strong>
                  </div>
                  <div className="summary-row">
                    <span className="label">City</span>
                    <strong className="value">{preview.city}</strong>
                  </div>
                  <div className="summary-row">
                    <span className="label">Weather</span>
                    <strong className="value">{preview.weather}</strong>
                  </div>
                  <div className="summary-row">
                    <span className="label">Time window</span>
                    <strong className="value">
                      {new Date(preview.start_time).toLocaleString()} - {new Date(preview.end_time).toLocaleTimeString()}
                    </strong>
                  </div>
                </div>

                <div className="place-selection">
                  <label className="place-section-label">Top place options (choose one)</label>
                  <div className="places-list">
                    {(preview.place_options || []).map((place, index) => (
                      <label
                        key={`${place.name}-${place.address || 'na'}`}
                        className={`place-option ${selectedPlaceIndex === index ? 'place-option-selected' : ''}`}
                      >
                        <input
                          type="radio"
                          name="place-selection"
                          checked={selectedPlaceIndex === index}
                          onChange={() => setSelectedPlaceIndex(index)}
                        />
                        <div className="place-content">
                          <div className="place-header">
                            <strong className="place-name">{place.name}</strong>
                            <span className="place-type">{selectedPlaceIndex === index ? 'Selected' : formatPlaceType(place)}</span>
                          </div>
                          <p className="place-address">{place.address || 'Address unavailable'}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {calendarLink ? (
                  <a className="calendar-link" href={calendarLink} target="_blank" rel="noreferrer">
                    Open calendar event
                  </a>
                ) : null}
              </div>
            )}

            {/* SECTION 4: Actions and Suggestion */}
            {!showInputSection && preview && (
              <div className="panel-section actions-section">
                <div className="actions">
                  <button type="button" className="primary" onClick={confirmPlan} disabled={processing}>
                    {processing ? 'Confirming...' : 'Confirm & Save'}
                  </button>
                  <button type="button" className="secondary" onClick={() => setShowInputSection(true)} disabled={processing}>
                    Back to input
                  </button>
                </div>

                <label className="field suggestion-field">
                  <span>Or suggest a change</span>
                  <textarea
                    value={planSuggestion}
                    onChange={(event) => setPlanSuggestion(event.target.value)}
                    rows={2}
                    placeholder="Make it lower budget, prefer indoor, avoid crowds..."
                  />
                </label>

                <div className="actions">
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => runPlan('revise')}
                    disabled={processing || !planSuggestion.trim()}
                  >
                    Get alternative suggestion
                  </button>
                </div>
              </div>
            )}

            {/* ERROR & STATUS MESSAGES */}
            {error ? <div className="error-banner">{error}</div> : null}
            {errorDetails ? (
              <details className="error-details">
                <summary>Technical error details</summary>
                <pre>{errorDetails}</pre>
              </details>
            ) : null}
            {confirmStatus ? <div className="success-banner">{confirmStatus}</div> : null}
              </section>
            </main>
          ) : null}

          {activeView === 'history' ? (
            <section className="panel history-panel history-page">
              <div className="panel-header">
                <div>
                  <p className="section-label">History</p>
                  <h2>Recent confirmed plans</h2>
                </div>
                <strong className="history-count">{history.length} recent</strong>
              </div>
              {history.length === 0 ? (
                <div className="empty-state">No saved plans yet. Confirm a plan to store it here.</div>
              ) : (
                <div className="history-list">
                  {history.map((item) => (
                    <article key={item.id} className="history-item">
                      <div>
                        <strong>{item.decision}</strong>
                        <p>{item.city} - {item.weather}</p>
                        <p>{item.selected_place_name}</p>
                      </div>
                      <small>{new Date(item.created_at).toLocaleString()}</small>
                    </article>
                  ))}
                </div>
              )}
            </section>
          ) : null}
        </div>
      </div>

        <footer className="footer-note">
          {apiInfo ? (
            <span>{apiInfo.name}  {apiInfo.version}</span>
          ) : (
            <span>Waiting for backend info...</span>
          )}
        </footer>
      </div>
    );
  }

  export default App;
