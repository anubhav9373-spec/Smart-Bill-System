whenSmartBillReady(function () {
  var products = [];
  var cart = [];
  var selected = null;
  var search = document.getElementById('searchProduct');
  var qty = document.getElementById('productQty');
  var nameBox = document.getElementById('selectedProductName');
  var priceBox = document.getElementById('selectedProductPrice');
  var stockBox = document.getElementById('selectedProductStock');
  function money(value) { return '₹' + Number(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 }); }
  function totals() {
    var subtotal = cart.reduce(function (sum, item) { return sum + item.price * item.qty; }, 0);
    var discount = Math.min(Math.max(parseFloat(document.getElementById('discountInput').value) || 0, 0), subtotal);
    document.getElementById('discountInput').value = discount;
    document.getElementById('subtotalDisplay').textContent = money(subtotal);
    document.getElementById('grandTotalDisplay').textContent = money(subtotal - discount);
  }
  function render() {
    document.getElementById('emptyCartMessage').style.display = cart.length ? 'none' : 'flex';
    document.getElementById('itemCountText').textContent = cart.length ? cart.length + ' item(s) in bill.' : 'No items added.';
    document.getElementById('cartTableBody').innerHTML = cart.map(function (item, index) {
      return '<tr><td><strong>' + escapeHtml(item.name) + '</strong></td><td class="text-center">' + item.qty + '</td><td class="text-right">' + money(item.price) + '</td><td class="text-right"><strong>' + money(item.price * item.qty) + '</strong></td><td><button class="btn-icon btn-icon-danger remove-btn" data-index="' + index + '">X</button></td></tr>';
    }).join('');
    totals();
  }
  function normalizeQuantity(value) { return Math.round(Number(value) * 1000) / 1000; }
  function resetSelection() { selected = null; search.value = ''; nameBox.textContent = 'No product selected'; priceBox.textContent = 'Select a product to see its price'; stockBox.textContent = '-'; qty.value = 1; qty.removeAttribute('max'); }
  SmartBillAPI.get('/api/products').then(function (data) { products = data.products; document.getElementById('productList').innerHTML = products.filter(function (p) { return p.stock > 0; }).map(function (p) { return '<option value="' + escapeHtml(p.name) + '">'; }).join(''); render(); });
  search.addEventListener('input', function () {
    selected = products.find(function (p) { return p.name.toLowerCase() === search.value.trim().toLowerCase() && p.stock > 0; });
    nameBox.textContent = selected ? selected.name : 'No product selected';
    priceBox.textContent = selected ? money(selected.price) + ' / unit' : 'Select a product to see its price';
    stockBox.textContent = selected ? 'In Stock (' + selected.stock + ')' : '-';
    if (selected) { qty.max = selected.stock; qty.value = 1; }
  });
  document.getElementById('decreaseQtyBtn').addEventListener('click', function () {
    qty.value = Math.max(Number(qty.min) || 1, normalizeQuantity((Number(qty.value) || 1) -1));
  });
  document.getElementById('increaseQtyBtn').addEventListener('click', function () {
    var max = selected ? selected.stock : Number.POSITIVE_INFINITY;
    qty.value = Math.min(max, normalizeQuantity((Number(qty.value) || 0) +1));
  });
  document.getElementById('addToBillBtn').addEventListener('click', function () {
    var amount = normalizeQuantity(qty.value);
    if (!selected || !Number.isFinite(amount) || amount <= 0 || amount > Number(selected.stock)) return alert('Select a valid product and quantity.');
    var existing = cart.find(function (item) { return item.id === selected.id; });
    if (existing) {
      if (normalizeQuantity(existing.qty + amount) > Number(selected.stock)) return alert('Quantity exceeds available stock.');
      existing.qty = normalizeQuantity(existing.qty + amount);
    } else cart.push({ productId: selected.id, name: selected.name, price: selected.price, qty: amount, isExtra: false });
    resetSelection(); render();
  });
  document.getElementById('addExtraBtn').addEventListener('click', function () {
    var name = document.getElementById('extraName').value.trim(), price = parseFloat(document.getElementById('extraPrice').value), amount = normalizeQuantity(document.getElementById('extraQty').value);
    if (!name || !Number.isFinite(price) || price < 0 || !Number.isFinite(amount) || amount <= 0) return alert('Enter valid extra item details.');
    cart.push({ name: name, price: price, qty: amount, isExtra: true }); render();
  });
  document.getElementById('cartTableBody').addEventListener('click', function (event) { if (event.target.classList.contains('remove-btn')) { cart.splice(Number(event.target.dataset.index), 1); render(); } });
  document.getElementById('clearCartBtn').addEventListener('click', function () { if (cart.length && confirm('Clear all items?')) { cart = []; render(); } });
  document.getElementById('discountInput').addEventListener('input', totals);
  document.getElementById('generateInvoiceBtn').addEventListener('click', function () {
    if (!cart.length) return alert('Cart is empty.');
    SmartBillAPI.post('/api/invoices', { customerName: document.getElementById('custName').value.trim() || 'User', discount: parseFloat(document.getElementById('discountInput').value) || 0, items: cart }).then(function (data) {
      sessionStorage.setItem('smartbill_current_invoice_id', String(data.invoice.internalId));
      window.location.href = '/invoice';
    }).catch(function (error) { alert(error.message); });
  });
});
