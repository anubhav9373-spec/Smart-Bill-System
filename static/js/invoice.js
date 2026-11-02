whenSmartBillReady(function () {
  var invoiceId = sessionStorage.getItem('smartbill_current_invoice_id');
  if (!invoiceId) return;
  SmartBillAPI.get('/api/invoices/' + invoiceId).then(function (data) {
    var invoice = data.invoice;
    var settings = window.SmartBillSession.settings;
    document.getElementById('storeName').textContent = settings.storeName;
    document.getElementById('storeAddress').textContent = settings.address;
    document.getElementById('storePhone').textContent = settings.phone;
    document.getElementById('invNo').textContent = invoice.id;
    document.getElementById('invDate').textContent = new Date(invoice.date).toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata'
    });
    document.getElementById('invCust').textContent = invoice.customerName;
    document.getElementById('invItems').innerHTML = invoice.items.map(function (item) {
      return '<div class="pos-item-row"><span class="col-name">' + escapeHtml(item.name) + '</span><span class="col-qty">' + item.qty + '</span><span class="col-rate">' + item.price.toLocaleString('en-IN') + '</span><span class="col-amt">' + item.total.toLocaleString('en-IN') + '</span></div>';
    }).join('');
    document.getElementById('invSubtotal').textContent = '₹' + invoice.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 });
    document.getElementById('invDiscount').textContent = '₹' + invoice.discount.toLocaleString('en-IN', { minimumFractionDigits: 2 });
    document.getElementById('invTotal').textContent = '₹' + invoice.total.toLocaleString('en-IN', { minimumFractionDigits: 2 });
    var shareUrl = '';
    document.getElementById('shareQrBtn').addEventListener('click', function () {
      SmartBillAPI.post('/api/invoices/' + invoice.internalId + '/share', {}).then(function (data) {
      shareUrl = data.url;
      if (typeof QRious === 'undefined') throw new Error('QR generator is unavailable. Please refresh the page and try again.');
      new QRious({ element: document.getElementById('shareQrCanvas'), value: shareUrl, size: 240, level: 'H' });
      document.getElementById('shareQrHint').textContent = 'Secure link active until ' + new Date(data.expiresAt).toLocaleString('en-IN');
      document.getElementById('shareQrModal').classList.remove('hidden');
      }).catch(function (error) { alert(error.message); });
    });
    document.getElementById('copyShareLinkBtn').addEventListener('click', function () {
      if (!shareUrl) return alert('Generate the QR link first.');
      navigator.clipboard.writeText(shareUrl).then(function () { alert('Link copied.'); }).catch(function () { alert('Unable to copy link.'); });
    });
  }).catch(function (error) { alert(error.message); });
  ['closeShareQrBtn', 'closeShareQrBtn2'].forEach(function (id) { document.getElementById(id).addEventListener('click', function () { document.getElementById('shareQrModal').classList.add('hidden'); }); });
});
