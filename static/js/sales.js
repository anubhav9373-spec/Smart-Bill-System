whenSmartBillReady(function () {
  var sales = [];
  var tableBody = document.getElementById('salesTableBody');
  var searchInput = document.getElementById('salesSearch');
  var dateInput = document.getElementById('salesDateFilter');

  function money(value) {
    return '₹' + Number(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function localDate(value) {
    var date = new Date(value);
    return isNaN(date.getTime()) ? '—' : date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
  }

  function render() {
    var query = searchInput.value.trim().toLowerCase();
    var date = dateInput.value;
    var filtered = sales.filter(function (invoice) {
      var invoiceId = String(invoice.id || '').toLowerCase();
      var customer = String(invoice.customerName || '').toLowerCase();
      return (!query || invoiceId.indexOf(query) !== -1 || customer.indexOf(query) !== -1) &&
        (!date || String(invoice.date || '').slice(0, 10) === date);
    });

    document.getElementById('totalBillsCount').textContent = filtered.length;
    document.getElementById('totalSalesAmount').textContent = money(filtered.reduce(function (sum, item) { return sum + Number(item.total || 0); }, 0));
    document.getElementById('totalDiscountAmount').textContent = money(filtered.reduce(function (sum, item) { return sum + Number(item.discount || 0); }, 0));
    document.getElementById('emptySalesState').classList.toggle('hidden', filtered.length > 0);
    tableBody.innerHTML = filtered.map(function (invoice) {
      return '<tr><td><strong>' + escapeHtml(String(invoice.id || '—')) + '</strong></td><td>' + escapeHtml(String(invoice.customerName || 'Walk-in customer')) + '</td><td>' + localDate(invoice.date) + '</td><td class="text-center">' + (invoice.items || []).length + '</td><td class="text-right"><strong>' + money(invoice.total) + '</strong></td><td class="text-center"><button class="btn btn-primary view-btn" data-id="' + escapeHtml(String(invoice.internalId || '')) + '">View</button></td></tr>';
    }).join('');
  }

  SmartBillAPI.get('/api/invoices').then(function (data) {
    sales = Array.isArray(data.invoices) ? data.invoices : [];
    render();
  });
  searchInput.addEventListener('input', render);
  dateInput.addEventListener('change', render);
  document.getElementById('clearFiltersBtn').addEventListener('click', function () {
    searchInput.value = '';
    dateInput.value = '';
    render();
  });
  tableBody.addEventListener('click', function (event) {
    var button = event.target.closest('.view-btn');
    if (!button) return;
    sessionStorage.setItem('smartbill_current_invoice_id', String(button.dataset.id));
    window.location.href = '/invoice';
  });
});
