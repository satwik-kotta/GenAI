const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const STORAGE_KEY = 'planner_access_token';
const REQUEST_TIMEOUT_MS = 45000;

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
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const mergedHeaders = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (authToken) {
    mergedHeaders.Authorization = `Bearer ${authToken}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: mergedHeaders,
      ...options,
      signal: options.signal || controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      const timeoutError = new Error(`Request timed out after ${REQUEST_TIMEOUT_MS / 1000}s`);
      timeoutError.stage = 'network';
      timeoutError.statusCode = 408;
      throw timeoutError;
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }

  if (!response.ok) {
    const detail = data?.detail;
    const stage = detail && typeof detail === 'object' ? detail.stage : undefined;
    const message =
      (detail && typeof detail === 'object' ? detail.message : null)
      || (typeof detail === 'string' ? detail : null)
      || data?.message
      || `Request failed with status ${response.status}`;

    const requestError = new Error(message);
    requestError.statusCode = response.status;
    requestError.backendDetail = detail;
    if (stage) {
      requestError.stage = stage;
    }
    throw requestError;
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

export function revisePlan(payload) {
  return request('/plan/revise', {
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
