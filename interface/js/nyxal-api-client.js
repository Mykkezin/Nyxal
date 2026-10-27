/* Nyxal API client — ponto único para requisições POST da interface. */
(function () {
  'use strict';

  function getBase() {
    return String(window.NYXAL_API_BASE || 'http://127.0.0.1:8010').replace(/\/$/, '');
  }

  async function nyxalApiPost(path, options = {}) {
    const { body, headers = {}, parse = 'json', signal, throwOnError = true } = options;
    const response = await fetch(getBase() + path, {
      method: 'POST',
      headers,
      body,
      signal,
    });

    let data = null;
    if (parse === 'blob') data = await response.blob();
    else if (parse === 'text') data = await response.text();
    else {
      try { data = await response.json(); } catch (_) { data = null; }
    }

    if (!response.ok && throwOnError) {
      const detail = data?.motivo || data?.erro || data?.detail || ('HTTP ' + response.status);
      const error = new Error('Nyxal API POST ' + path + ': ' + detail);
      error.status = response.status;
      error.payload = data;
      throw error;
    }

    return { response, data };
  }

  window.nyxalApiPost = nyxalApiPost;
})();
