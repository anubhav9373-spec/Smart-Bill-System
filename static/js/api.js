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
    if (window.SmartBillSession) callback();
    else document.addEventListener('smartbill:ready', callback, { once: true });
  };

  fetch('/api/me').then(function (response) {
    if (!response.ok) return null;
    return response.json();
  }).then(function (data) {
    if (!data) return;
    csrfToken = data.csrfToken || '';
    window.SmartBillSession = data;
    var name = document.getElementById('sidebarOwnerName');
    var avatar = document.getElementById('sidebarAvatar');
    var mobileAvatar = document.getElementById('mobileAvatar');
    if (name) name.textContent = data.user.name;
    if (avatar) avatar.textContent = data.user.name.charAt(0).toUpperCase();
    if (mobileAvatar) mobileAvatar.textContent = data.user.name.charAt(0).toUpperCase();
    window.applySmartBillTheme(data.settings.theme);
    document.dispatchEvent(new CustomEvent('smartbill:ready'));
  }).catch(function () {});
})();
