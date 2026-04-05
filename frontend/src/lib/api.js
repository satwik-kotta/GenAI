const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const STORAGE_KEY = 'planner_access_token';

let authToken = localStorage.getItem(STORAGE_KEY) || '';

export function setAuthToken(token) {
  authToken = token || '';
  if (authToken) {
    localStorage.setItem(STORAGE_KEY, authToken);
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

export function getAuthToken() {
  return authToken;
}

async function request(path, options = {}) {
  const mergedHeaders = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (authToken) {
    mergedHeaders.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: mergedHeaders,
    ...options,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const message = data?.detail || data?.message || `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data;
}

export function getApiInfo() {
  return request('');
}

export function authWithGoogle(idToken) {
  return request('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ id_token: idToken }),
  });
}

export function getMe() {
  return request('/auth/me');
}

export function getPlanHistory(limit = 20) {
  return request(`/plans/history?limit=${limit}`);
}

export function parseIntent(userInput) {
  return request('/intent/parse', {
    method: 'POST',
    body: JSON.stringify({ user_input: userInput }),
  });
}

export function getWeather(city) {
  return request('/weather/current', {
    method: 'POST',
    body: JSON.stringify({ city }),
  });
}

export function searchPlaces(query, latitude, longitude) {
  return request('/places/search', {
    method: 'POST',
    body: JSON.stringify({ query, latitude, longitude }),
  });
}

export function previewPlan(payload) {
  return request('/plan/preview', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function executePlan(payload) {
  return request('/plan/execute', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function createCalendarEvent(payload) {
  return request('/calendar/events', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
