whenSmartBillReady(function () {
  var products = [];
  var tableBody = document.getElementById('productsTableBody');
  var mobileList = document.getElementById('productsMobileList');
  var searchInput = document.getElementById('searchInput');
  var categoryFilter = document.getElementById('categoryFilter');
  var categoryPills = document.getElementById('categoryPills');
  var emptyState = document.getElementById('emptyState');
  var errorBox = document.getElementById('productsError');
  var addModal = document.getElementById('addProductModal');
  var editModal = document.getElementById('editProductModal');
  var deleteModal = document.getElementById('deleteModal');
  var deleteTargetId = null;

  function money(value) { return '₹' + Number(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function stockStatus(product) {
    if (product.stock === 0) return { label: 'Out of stock', className: 'status-out' };
    if (product.stock <= product.minStock) return { label: 'Low stock', className: 'status-low' };
    return { label: 'In stock', className: 'status-in' };
  }
  function load() {
    errorBox.classList.add('hidden');
    return SmartBillAPI.get('/api/products').then(function (data) { products = Array.isArray(data.products) ? data.products : []; render(); });
  }
  function updateSummary() {
    var totalStock = products.reduce(function (sum, product) { return sum + Number(product.stock || 0); }, 0);
    var lowStock = products.filter(function (product) { return Number(product.stock || 0) > 0 && product.stock <= product.minStock; }).length;
    var outOfStock = products.filter(function (product) { return Number(product.stock || 0) === 0; }).length;
    var inStock = Math.max(products.length - lowStock, 0);
    var totalProducts = products.length;
    function percentage(value) {
      return totalProducts ? Math.round((value / totalProducts) * 100) : 0;
    }
    document.getElementById('totalProductsCount').textContent = products.length.toLocaleString('en-IN');
    document.getElementById('totalStockCount').textContent = totalStock.toLocaleString('en-IN');
    document.getElementById('lowStockCount').textContent = lowStock.toLocaleString('en-IN');
    document.getElementById('outStockCount').textContent = outOfStock.toLocaleString('en-IN');
    document.getElementById('totalProductsPercent').textContent = '100% of catalogue';
    document.getElementById('inStockPercent').textContent = percentage(inStock) + '% of catalogue';
    document.getElementById('lowStockPercent').textContent = percentage(lowStock) + '% of catalogue';
    document.getElementById('outStockPercent').textContent = percentage(outOfStock) + '% of catalogue';
  }
  function setCategories(categories, selected) {
    categoryFilter.replaceChildren(new Option('All Categories', 'all'));
    categories.forEach(function (category) { categoryFilter.add(new Option(category, category)); });
    categoryFilter.value = categories.indexOf(selected) !== -1 ? selected : 'all';
    categoryPills.replaceChildren();
    [{ label: 'All', value: 'all' }].concat(categories.map(function (category) { return { label: category, value: category }; })).forEach(function (item) {
      var button = document.createElement('button');
      button.type = 'button'; button.className = 'category-pill' + (item.value === categoryFilter.value ? ' active' : '');
      button.textContent = item.label; button.dataset.category = item.value;
      categoryPills.appendChild(button);
    });
    var categorySuggestions = document.getElementById('categorySuggestions');
    var productNameSuggestions = document.getElementById('productNameSuggestions');
    categorySuggestions.replaceChildren(); productNameSuggestions.replaceChildren();
    categories.forEach(function (category) { categorySuggestions.appendChild(new Option(category)); });
    products.forEach(function (product) { productNameSuggestions.appendChild(new Option(product.name)); });
  }
  function actionButton(label, className, id, name) {
    var button = document.createElement('button');
    button.type = 'button'; button.className = 'product-action ' + className; button.dataset.id = id;
    if (name !== undefined) button.dataset.name = name;
    button.textContent = label; return button;
  }
  function productCell(product) {
    var cell = document.createElement('td');
    var name = document.createElement('strong'); name.textContent = product.name;
    cell.appendChild(name); return cell;
  }
  function textCell(value, className) {
    var cell = document.createElement('td'); if (className) cell.className = className; cell.textContent = value; return cell;
  }
  function renderTable(filtered) {
    tableBody.replaceChildren();
    filtered.forEach(function (product, index) {
      var status = stockStatus(product); var row = document.createElement('tr');
      row.appendChild(textCell(index + 1, 'products-index'));
      row.appendChild(productCell(product)); row.appendChild(textCell(product.category));
      row.appendChild(textCell(money(product.price), 'products-price'));
      row.appendChild(textCell(product.stock + ' ' + product.unit));
      var statusCell = document.createElement('td'); var badge = document.createElement('span'); badge.className = 'product-status ' + status.className; badge.textContent = status.label; statusCell.appendChild(badge); row.appendChild(statusCell);
      var actionCell = document.createElement('td'); actionCell.className = 'text-right product-actions'; actionCell.append(actionButton('Edit', 'edit-btn', product.id), actionButton('Delete', 'delete-btn', product.id, product.name)); row.appendChild(actionCell);
      tableBody.appendChild(row);
    });
  }
  function renderMobileCards(filtered) {
    mobileList.replaceChildren();
    filtered.forEach(function (product) {
      var status = stockStatus(product); var card = document.createElement('article'); card.className = 'product-mobile-card';
      var top = document.createElement('div'); top.className = 'product-mobile-top'; var info = document.createElement('div');
      var name = document.createElement('h3'); name.textContent = product.name; var category = document.createElement('p'); category.textContent = product.category;
      info.append(name, category); var badge = document.createElement('span'); badge.className = 'product-status ' + status.className; badge.textContent = status.label; top.append(info, badge);
      var meta = document.createElement('div'); meta.className = 'product-mobile-meta'; meta.textContent = money(product.price) + '  ·  ' + product.stock + ' ' + product.unit;
      var actions = document.createElement('div'); actions.className = 'product-mobile-actions'; actions.append(actionButton('Edit', 'edit-btn', product.id), actionButton('Delete', 'delete-btn', product.id, product.name));
      card.append(top, meta, actions); mobileList.appendChild(card);
    });
  }
  function render() {
    var query = (searchInput.value || '').trim().toLowerCase();
    var category = categoryFilter.value;
    var filtered = products.filter(function (p) {
      return (!query || p.name.toLowerCase().indexOf(query) !== -1 || p.category.toLowerCase().indexOf(query) !== -1) &&
        (category === 'all' || p.category === category);
    });
    var categories = products.map(function (p) { return p.category; }).filter(function (v, i, a) { return a.indexOf(v) === i; }).sort();
    setCategories(categories, category);
    updateSummary();
    document.getElementById('productsResultCount').textContent = filtered.length + (filtered.length === 1 ? ' product' : ' products');
    if (!filtered.length) {
      tableBody.replaceChildren(); mobileList.replaceChildren();
      emptyState.classList.remove('hidden');
      return;
    }
    emptyState.classList.add('hidden');
    renderTable(filtered); renderMobileCards(filtered);
  }
  function formData(prefix) {
    return { name: document.getElementById(prefix + 'Name').value.trim(), category: document.getElementById(prefix + 'Category').value.trim(),
      unit: document.getElementById(prefix + 'Unit').value, price: parseFloat(document.getElementById(prefix + 'Price').value),
      stock: parseFloat(document.getElementById(prefix + 'Stock').value), minStock: parseFloat(document.getElementById(prefix + 'MinStock').value) };
  }
  searchInput.addEventListener('input', render);
  categoryFilter.addEventListener('change', render);
  categoryPills.addEventListener('click', function (event) { var pill = event.target.closest('.category-pill'); if (!pill) return; categoryFilter.value = pill.dataset.category; render(); });
  function openAddModal() { document.getElementById('addProductForm').reset(); addModal.classList.remove('hidden'); }
  document.getElementById('addProductBtn').addEventListener('click', openAddModal);
  document.getElementById('emptyAddProductBtn').addEventListener('click', openAddModal);
  document.getElementById('addProductForm').addEventListener('submit', function (event) {
    event.preventDefault();
    SmartBillAPI.post('/api/products', formData('add')).then(function () { addModal.classList.add('hidden'); return load(); }).catch(function (error) { alert(error.message); });
  });
  document.getElementById('editProductForm').addEventListener('submit', function (event) {
    event.preventDefault();
    var id = document.getElementById('editId').value;
    SmartBillAPI.put('/api/products/' + id, formData('edit')).then(function () { editModal.classList.add('hidden'); return load(); }).catch(function (error) { alert(error.message); });
  });
  function handleProductAction(event) {
    var edit = event.target.closest('.edit-btn');
    var del = event.target.closest('.delete-btn');
    if (edit) {
      var p = products.find(function (item) { return item.id === Number(edit.dataset.id); });
      if (!p) return;
      ['Name', 'Category', 'Unit', 'Price', 'Stock', 'MinStock'].forEach(function (key) { document.getElementById('edit' + key).value = p[key.charAt(0).toLowerCase() + key.slice(1)] ?? p[key]; });
      document.getElementById('editId').value = p.id;
      editModal.classList.remove('hidden');
    }
    if (del) { deleteTargetId = del.dataset.id; document.getElementById('deleteProductName').textContent = del.dataset.name; deleteModal.classList.remove('hidden'); }
  }
  tableBody.addEventListener('click', handleProductAction);
  mobileList.addEventListener('click', handleProductAction);
  document.getElementById('confirmDeleteBtn').addEventListener('click', function () {
    SmartBillAPI.remove('/api/products/' + deleteTargetId).then(function () { deleteModal.classList.add('hidden'); return load(); }).catch(function (error) { alert(error.message); });
  });
  document.querySelectorAll('[data-close]').forEach(function (button) { button.addEventListener('click', function () { document.getElementById(button.dataset.close).classList.add('hidden'); }); });
  load().catch(function (error) { errorBox.textContent = error.message || 'Products could not be loaded. Please try again.'; errorBox.classList.remove('hidden'); });
});
