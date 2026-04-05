import { useEffect, useMemo, useState } from 'react';
import {
  createCalendarEvent,
  executePlan,
  getApiInfo,
  getAuthToken,
  getMe,
  getPlanHistory,
  getWeather,
  parseIntent,
  previewPlan,
  searchPlaces,
  setAuthToken,
  authWithGoogle,
} from './lib/api';
import LoginPage from './components/LoginPage';

const samplePrompt = 'I want to go hiking this weekend but only if it is not raining, otherwise suggest something indoors and block 10 to 2';
const googleClientId = import.meta.env.VITE_GOOGLE_WEB_CLIENT_ID || import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

function App() {
  const [userInput, setUserInput] = useState(samplePrompt);
  const [city, setCity] = useState('Mumbai');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [apiInfo, setApiInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busyAction, setBusyAction] = useState('');
  const [error, setError] = useState('');
  const [intent, setIntent] = useState(null);
  const [weather, setWeather] = useState(null);
  const [places, setPlaces] = useState([]);
  const [preview, setPreview] = useState(null);
  const [calendarLink, setCalendarLink] = useState('');
  const [directEventStatus, setDirectEventStatus] = useState('');
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [googleReady, setGoogleReady] = useState(false);

  const coordinates = useMemo(() => {
    const lat = latitude.trim() === '' ? undefined : Number(latitude);
    const lng = longitude.trim() === '' ? undefined : Number(longitude);
    return {
      latitude: Number.isFinite(lat) ? lat : undefined,
      longitude: Number.isFinite(lng) ? lng : undefined,
    };
  }, [latitude, longitude]);

  useEffect(() => {
    getApiInfo()
      .then(setApiInfo)
      .catch(() => setApiInfo(null));
  }, []);

  useEffect(() => {
    if (!googleClientId) {
      return;
    }

    const existingScript = document.getElementById('google-oauth-script');
    if (existingScript) {
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-oauth-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (!window.google || !window.google.accounts || !window.google.accounts.id) {
        return;
      }
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async ({ credential }) => {
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

    document.body.appendChild(script);
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
  }

  async function handleAction(action) {
    setError('');
    setBusyAction(action);
    try {
      if (action === 'intent') {
        const data = await parseIntent(userInput);
        setIntent(data);
      }

      if (action === 'weather') {
        const data = await getWeather(city);
        setWeather(data);
      }

      if (action === 'places') {
        const data = await searchPlaces(intent?.activity || 'Hiking', coordinates.latitude, coordinates.longitude);
        setPlaces(data.place_options);
      }

      if (action === 'preview') {
        const data = await previewPlan({
          user_input: userInput,
          city,
          latitude: coordinates.latitude,
          longitude: coordinates.longitude,
        });
        setPreview(data);
        setIntent(data.parsed_intent);
        setWeather({ city: data.city, weather: data.weather });
        setPlaces(data.place_options || []);
      }

      if (action === 'execute') {
        if (!user) {
          throw new Error('Please sign in with Google before executing a plan');
        }
        const data = await executePlan({
          user_input: userInput,
          city,
          latitude: coordinates.latitude,
          longitude: coordinates.longitude,
        });
        setPreview(data);
        setIntent(data.parsed_intent);
        setWeather({ city: data.city, weather: data.weather });
        setPlaces(data.place_options || []);
        setCalendarLink(data.calendar_link);
        const historyData = await getPlanHistory();
        setHistory(historyData.items || []);
      }

      if (action === 'calendar') {
        if (!user) {
          throw new Error('Please sign in with Google before creating calendar events');
        }
        const payload = {
          summary: preview?.decision || 'AI Day Plan',
          location: preview?.selected_place?.name || 'Unknown location',
          start_time: preview?.start_time || new Date().toISOString(),
          end_time: preview?.end_time || new Date(Date.now() + 1000 * 60 * 60 * 2).toISOString(),
          description: 'Created from the React planner frontend',
        };
        const data = await createCalendarEvent(payload);
        setCalendarLink(data.calendar_link);
        setDirectEventStatus('Calendar event created successfully');
      }
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setBusyAction('');
      setLoading(false);
    }
  }

  async function handlePreview() {
    setLoading(true);
    await handleAction('preview');
  }

  async function handleExecute() {
    setLoading(true);
    await handleAction('execute');
  }

  if (!user) {
    return (
      <LoginPage
        apiInfo={apiInfo}
        error={error}
        googleClientId={googleClientId}
      />
    );
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="hero">
        <div>
          <p className="eyebrow">FastAPI + Gemini + Weather + Places + Calendar</p>
          <h1>AI Day Planner</h1>
          <p className="hero-copy">
            A React-first interface for planning activities, checking live weather, finding nearby places,
            and creating calendar events in one flow.
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

      <main className="layout">
        <section className="panel composer">
          <div className="panel-header">
            <div>
              <p className="section-label">Planner Input</p>
              <h2>Describe your day</h2>
            </div>
            <button className="ghost-button" onClick={() => setUserInput(samplePrompt)} type="button">
              Load sample
            </button>
          </div>

          <label className="field">
            <span>Prompt</span>
            <textarea value={userInput} onChange={(event) => setUserInput(event.target.value)} rows={6} />
          </label>

          <div className="grid-two">
            <label className="field">
              <span>City</span>
              <input value={city} onChange={(event) => setCity(event.target.value)} placeholder="Mumbai" />
            </label>
            <label className="field">
              <span>Latitude</span>
              <input value={latitude} onChange={(event) => setLatitude(event.target.value)} placeholder="19.0330" />
            </label>
            <label className="field">
              <span>Longitude</span>
              <input value={longitude} onChange={(event) => setLongitude(event.target.value)} placeholder="73.0297" />
            </label>
            <div className="field info-block">
              <span>API Mode</span>
              <strong>{preview?.weather ? 'Previewed' : 'Ready'}</strong>
              <small>Use preview first, then execute to create a calendar event.</small>
            </div>
          </div>

          <div className="actions">
            <button type="button" onClick={() => handleAction('intent')} disabled={!!busyAction}>
              {busyAction === 'intent' ? 'Parsing...' : 'Parse Intent'}
            </button>
            <button type="button" onClick={() => handleAction('weather')} disabled={!!busyAction}>
              {busyAction === 'weather' ? 'Checking...' : 'Weather'}
            </button>
            <button type="button" onClick={() => handleAction('places')} disabled={!!busyAction}>
              {busyAction === 'places' ? 'Searching...' : 'Search Places'}
            </button>
            <button type="button" className="secondary" onClick={handlePreview} disabled={loading || !!busyAction}>
              {loading && busyAction === 'preview' ? 'Building...' : 'Preview Plan'}
            </button>
            <button type="button" className="primary" onClick={handleExecute} disabled={loading || !!busyAction}>
              {loading && busyAction === 'execute' ? 'Executing...' : 'Execute Plan'}
            </button>
            <button type="button" className="secondary" onClick={() => handleAction('calendar')} disabled={!!busyAction}>
              {busyAction === 'calendar' ? 'Creating...' : 'Create Calendar Event'}
            </button>
          </div>

          {error ? <div className="error-banner">{error}</div> : null}
        </section>

        <section className="sidebar">
          <article className="panel result-card">
            <p className="section-label">Intent</p>
            <pre>{intent ? formatJson(intent) : 'No intent parsed yet.'}</pre>
          </article>

          <article className="panel result-card">
            <p className="section-label">Weather</p>
            <pre>{weather ? formatJson(weather) : 'No weather data yet.'}</pre>
          </article>

          <article className="panel result-card">
            <p className="section-label">Plan Preview</p>
            <pre>{preview ? formatJson(preview) : 'No preview yet.'}</pre>
          </article>
        </section>
      </main>

      <section className="panel places-panel">
        <div className="panel-header">
          <div>
            <p className="section-label">Places</p>
            <h2>Top nearby options</h2>
          </div>
          <div className="calendar-summary">
            <span className="section-label">Calendar</span>
            <a href={calendarLink || '#'} target="_blank" rel="noreferrer">
              {calendarLink ? 'Open event link' : 'No event created'}
            </a>
            {directEventStatus ? <small>{directEventStatus}</small> : null}
          </div>
        </div>

        <div className="cards">
          {places.length > 0 ? (
            places.map((place) => (
              <article key={`${place.name}-${place.address}`} className="place-card">
                <div>
                  <h3>{place.name}</h3>
                  <p>{place.address || 'Address unavailable'}</p>
                </div>
                <div className="rating">{place.rating ?? 'n/a'}</div>
              </article>
            ))
          ) : (
            <div className="empty-state">Run Preview Plan or Search Places to populate this section.</div>
          )}
        </div>
      </section>

      <section className="panel history-panel">
        <div className="panel-header">
          <div>
            <p className="section-label">Database</p>
            <h2>Plan History</h2>
          </div>
          <strong className="history-count">{history.length} recent</strong>
        </div>
        {history.length === 0 ? (
          <div className="empty-state">No saved plans yet. Execute a plan after signing in.</div>
        ) : (
          <div className="history-list">
            {history.map((item) => (
              <article key={item.id} className="history-item">
                <div>
                  <strong>{item.decision}</strong>
                  <p>{item.city} · {item.weather}</p>
                  <p>{item.selected_place_name}</p>
                </div>
                <small>{new Date(item.created_at).toLocaleString()}</small>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer className="footer-note">
        {apiInfo ? (
          <span>{apiInfo.name} · {apiInfo.version}</span>
        ) : (
          <span>Waiting for backend info...</span>
        )}
      </footer>
    </div>
  );
}

export default App;
