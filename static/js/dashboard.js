whenSmartBillReady(function () {
  var chart;
  var dashboardData;
  var currency = function (value) {
    return '₹' + Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  };
  var localDate = function (value) {
    return new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
  };
  var startOfDay = function (date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  };
  function renderChart() {
    var days = Number(document.getElementById('salesRangeFilter').value);
    var today = startOfDay(new Date());
    var points = [];
    for (var index = days - 1; index >= 0; index -= 1) {
      var date = new Date(today);
      date.setDate(today.getDate() - index);
      points.push({ date: date, value: 0 });
    }
    (dashboardData.salesHistory || []).forEach(function (invoice) {
      var invoiceDate = new Date(invoice.date);
      var matching = points.find(function (point) { return point.date.getTime() === startOfDay(invoiceDate).getTime(); });
      if (matching) matching.value += Number(invoice.total || 0);
    });
    var empty = points.every(function (point) { return point.value === 0; });
    document.getElementById('salesChartEmpty').classList.toggle('hidden', !empty);
    if (chart) chart.destroy();
    if (typeof Chart === 'undefined') return;
    chart = new Chart(document.getElementById('dashSalesChart'), {
      type: 'line',
      data: {
        labels: points.map(function (point) { return localDate(point.date); }),
        datasets: [{ data: points.map(function (point) { return point.value; }), borderColor: '#07864f', backgroundColor: 'rgba(7,134,79,.12)', fill: true, tension: .35, pointRadius: days > 30 ? 0 : 3, pointBackgroundColor: '#07864f' }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 7, color: '#81909d' } }, y: { beginAtZero: true, grid: { color: '#e8f0eb' }, ticks: { color: '#81909d', callback: function (value) { return '₹' + Number(value).toLocaleString('en-IN'); } } } } }
    });
  }
  function renderLists() {
    var products = dashboardData.topProducts || [];
    document.getElementById('dashTopProductsBody').innerHTML = products.length ? products.map(function (product, index) {
      return '<tr><td><span class="dash-rank">' + (index + 1) + '</span><strong class="dash-prod-name">' + escapeHtml(product.name) + '</strong></td><td class="text-center">' + product.qty + '</td><td class="text-right"><strong>' + currency(product.amount) + '</strong></td></tr>';
    }).join('') : '<tr><td colspan="3" class="dashboard-table-empty">No product sales yet.</td></tr>';
    var invoices = dashboardData.invoices || [];
    document.getElementById('dashRecentBody').innerHTML = invoices.length ? invoices.map(function (invoice) {
      return '<tr><td><a class="dash-invoice-link" href="/invoice" data-invoice-id="' + invoice.internalId + '"><strong>' + escapeHtml(invoice.id) + '</strong></a></td><td>' + localDate(invoice.date) + '</td><td class="text-right"><strong>' + currency(invoice.total) + '</strong></td></tr>';
    }).join('') : '<tr><td colspan="3" class="dashboard-table-empty">No bills created yet.</td></tr>';
    document.querySelectorAll('.dash-invoice-link').forEach(function (link) {
      link.addEventListener('click', function () {
        sessionStorage.setItem('smartbill_current_invoice_id', link.getAttribute('data-invoice-id'));
      });
    });
    document.getElementById('dashboardEmpty').classList.toggle('hidden', Boolean(products.length || invoices.length));
  }
  SmartBillAPI.get('/api/dashboard').then(function (data) {
    dashboardData = data;
    document.getElementById('dashTodaySales').textContent = currency(data.todaySales);
    document.getElementById('dashTotalSales').textContent = currency(data.totalSales);
    document.getElementById('dashTotalBills').textContent = Number(data.totalBills || 0).toLocaleString('en-IN');
    document.getElementById('dashLowStock').textContent = Number(data.lowStock || 0).toLocaleString('en-IN');
    document.getElementById('dashLowStockAlert').textContent = Number(data.lowStock || 0).toLocaleString('en-IN');
    document.getElementById('dashOutStock').textContent = Number(data.outOfStock || 0).toLocaleString('en-IN');
    renderLists();
    renderChart();
  }).catch(function (error) {
    document.getElementById('dashboardError').textContent = error.message || 'Unable to load dashboard data.';
    document.getElementById('dashboardError').classList.remove('hidden');
  });
  document.getElementById('salesRangeFilter').addEventListener('change', function () { if (dashboardData) renderChart(); });
});
