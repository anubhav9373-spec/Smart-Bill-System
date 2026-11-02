whenSmartBillReady(function () {
  var data = window.SmartBillSession;
  var settings = data.settings;
  document.getElementById('ownerName').value = data.user.name;
  document.getElementById('ownerEmail').value = data.user.email;
  document.getElementById('storeName').value = settings.storeName;
  document.getElementById('storePhone').value = settings.phone;
  document.getElementById('storeAddress').value = settings.address;
  document.getElementById('invoicePrefix').value = settings.invoicePrefix;
  document.getElementById('lowStockThreshold').value = settings.lowStockThreshold;
  document.getElementById('profileOwnerTitle').textContent = data.user.name;
  document.getElementById('sessionStoreName').textContent = settings.storeName;
  document.getElementById('profileAvatar').textContent = data.user.name.charAt(0).toUpperCase();
  document.getElementById('theme' + (settings.theme === 'dark' ? 'Dark' : 'Light')).checked = true;
  var activeShop = document.getElementById('activeShop');
  var activeShopStatus = document.getElementById('activeShopStatus');
  if (activeShop && data.memberships) {
    data.memberships.forEach(function (membership) {
      var option = document.createElement('option');
      option.value = membership.shopId;
      option.textContent = membership.shopName + ' (' + membership.role + ')';
      option.selected = membership.shopId === data.shop.id;
      activeShop.appendChild(option);
    });
    activeShop.disabled = data.memberships.length < 2;
    activeShop.addEventListener('change', function () {
      SmartBillAPI.post('/api/shop/switch', { shopId: this.value }).then(function () {
        if (activeShopStatus) activeShopStatus.textContent = 'Shop switched. Reloading workspace...';
        window.location.reload();
      }).catch(function (error) {
        if (activeShopStatus) activeShopStatus.textContent = error.message;
      });
    });
  }
  var teamCard = document.getElementById('teamAccessCard');
  var staffStatus = document.getElementById('staffStatus');
  function loadStaff() {
    if (!teamCard || (data.user.role !== 'owner' && data.user.role !== 'manager')) return;
    teamCard.hidden = false;
    SmartBillAPI.get('/api/staff').then(function (result) {
      var html = '<table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Action</th></tr></thead><tbody>';
      result.staff.forEach(function (member) {
        var action = member.role === 'owner' ? '<span class="text-muted">Owner</span>' :
          '<button type="button" class="btn btn-secondary staff-remove" data-id="' + member.id + '">Remove</button>';
        html += '<tr><td>' + escapeHtml(member.name) + '</td><td>' + escapeHtml(member.email) + '</td><td>' + escapeHtml(member.role) + '</td><td>' + action + '</td></tr>';
      });
      document.getElementById('staffList').innerHTML = html + '</tbody></table>';
    }).catch(function (error) { if (staffStatus) staffStatus.textContent = error.message; });
  }
  loadStaff();
  function save() {
    var selectedTheme = document.querySelector('input[name="theme"]:checked').value;
    window.applySmartBillTheme(selectedTheme);
    SmartBillAPI.put('/api/settings', { storeName: document.getElementById('storeName').value, phone: document.getElementById('storePhone').value,
      address: document.getElementById('storeAddress').value, invoicePrefix: document.getElementById('invoicePrefix').value,
      lowStockThreshold: document.getElementById('lowStockThreshold').value, theme: selectedTheme
    }).then(function () { document.getElementById('saveMsg').classList.remove('hidden'); }).catch(function (error) { alert(error.message); });
  }
  function bind(id, event, handler) {
    var element = document.getElementById(id);
    if (element) element.addEventListener(event, handler);
  }
  bind('saveAllBtn', 'click', save);
  bind('themeLight', 'change', save);
  bind('themeDark', 'change', save);
  bind('addStaffBtn', 'click', function () {
    SmartBillAPI.post('/api/staff', {
      name: document.getElementById('staffName').value,
      email: document.getElementById('staffEmail').value,
      password: document.getElementById('staffPassword').value,
      role: document.getElementById('staffRole').value
    }).then(function () {
      document.getElementById('staffName').value = '';
      document.getElementById('staffEmail').value = '';
      document.getElementById('staffPassword').value = '';
      if (staffStatus) staffStatus.textContent = 'Team member added.';
      loadStaff();
    }).catch(function (error) { if (staffStatus) staffStatus.textContent = error.message; });
  });
  bind('staffList', 'click', function (event) {
    var button = event.target.closest('.staff-remove');
    if (!button || !window.confirm('Remove this team member from the shop?')) return;
    SmartBillAPI.remove('/api/staff/' + button.getAttribute('data-id')).then(loadStaff)
      .catch(function (error) { if (staffStatus) staffStatus.textContent = error.message; });
  });
  bind('changePasswordBtn', 'click', function () {
    SmartBillAPI.put('/api/profile/password', {
      currentPassword: document.getElementById('currentPassword').value,
      newPassword: document.getElementById('newPassword').value
    }).then(function () {
      document.getElementById('currentPassword').value = '';
      document.getElementById('newPassword').value = '';
      alert('Password changed successfully. Please sign in again.');
      window.location.href = '/login';
    }).catch(function (error) { alert(error.message); });
  });
  bind('exportBackupBtn', 'click', function () {
    SmartBillAPI.get('/api/backup').then(function (backup) {
      var blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
      var link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'smartbill-backup-' + new Date().toISOString().slice(0, 10) + '.json';
      link.click();
      URL.revokeObjectURL(link.href);
    }).catch(function (error) { alert(error.message); });
  });
  bind('importLegacyBtn', 'click', function () {
    var input = document.getElementById('legacyDataFile');
    if (input) input.click();
  });
  bind('legacyDataFile', 'change', function () {
    var file = this.files[0];
    if (!file) return;
    var status = document.getElementById('migrationStatus');
    var reader = new FileReader();
    reader.onload = function () {
      try {
        var data = JSON.parse(reader.result);
        SmartBillAPI.post('/api/migrate/local', data).then(function (result) {
          status.textContent = result.importedProducts + ' products and ' + result.importedInvoices + ' invoices imported.';
        }).catch(function (error) { status.textContent = error.message; });
      } catch (error) {
        status.textContent = 'Selected file is not valid JSON.';
      }
    };
    reader.readAsText(file);
  });
  bind('logoutBtn', 'click', function () {
    SmartBillAPI.post('/logout', {}).then(function () { window.location.href = '/login'; });
  });
});
