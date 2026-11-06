(function () {
  var csrfToken = '';

  function request(path, options) {
    var config = options || {};
    config.headers = Object.assign({}, config.headers || {});
    if (config.body && typeof config.body !== 'string') {
      config.headers['Content-Type'] = 'application/json';
      config.body = JSON.stringify(config.body);
    }
    if (csrfToken) config.headers['X-CSRF-Token'] = csrfToken;
    return fetch(path, config).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          var error = new Error(data.error || 'Request failed');
          error.status = response.status;
          throw error;
        }
        return data;
      });
    });
  }

  window.SmartBillAPI = {
    request: request,
    get: function (path) { return request(path); },
    post: function (path, body) { return request(path, { method: 'POST', body: body }); },
    put: function (path, body) { return request(path, { method: 'PUT', body: body }); },
    remove: function (path) { return request(path, { method: 'DELETE' }); }
  };

  window.applySmartBillTheme = function (theme) {
    var isDark = theme === 'dark';
    localStorage.setItem('smartbill-theme', isDark ? 'dark' : 'light');
    document.documentElement.classList.add('theme-switching');
    document.body.classList.toggle('dark-theme', isDark);
    document.documentElement.classList.toggle('dark-theme', isDark);
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        document.documentElement.classList.remove('theme-switching');
      });
    });
  };

  window.whenSmartBillReady = function (callback) {
    if (window.SmartBillSession) {
      callback();
    } else {
      document.addEventListener('smartbill:ready', callback, { once: true });
    }
  };

  function applySessionData(data) {
    if (!data) return;
    csrfToken = data.csrfToken || '';
    window.SmartBillSession = data;
    var name = document.getElementById('sidebarOwnerName');
    var avatar = document.getElementById('sidebarAvatar');
    var mobileAvatar = document.getElementById('mobileAvatar');
    if (name && data.user && data.user.name) name.textContent = data.user.name;
    if (avatar && data.user && data.user.name) avatar.textContent = data.user.name.charAt(0).toUpperCase();
    if (mobileAvatar && data.user && data.user.name) mobileAvatar.textContent = data.user.name.charAt(0).toUpperCase();
    if (data.settings && data.settings.theme) window.applySmartBillTheme(data.settings.theme);
  }

  // Fast-path: Hydrate instantly from sessionStorage if available
  var isReadyDispatched = false;
  var cachedRaw = sessionStorage.getItem('smartbill_cached_session');
  if (cachedRaw) {
    try {
      var cached = JSON.parse(cachedRaw);
      applySessionData(cached);
      isReadyDispatched = true;
      setTimeout(function () {
        document.dispatchEvent(new CustomEvent('smartbill:ready'));
      }, 0);
    } catch (e) {
      // Ignore JSON parse error and fallback to network
    }
  }

  // Always refresh session in background to keep CSRF token & user settings fresh
  fetch('/api/me').then(function (response) {
    if (!response.ok) {
      if (response.status === 401) {
        sessionStorage.removeItem('smartbill_cached_session');
      }
      return null;
    }
    return response.json();
  }).then(function (data) {
    if (!data) return;
    sessionStorage.setItem('smartbill_cached_session', JSON.stringify(data));
    applySessionData(data);
    if (!isReadyDispatched) {
      isReadyDispatched = true;
      document.dispatchEvent(new CustomEvent('smartbill:ready'));
    }
  }).catch(function () {});
})();
