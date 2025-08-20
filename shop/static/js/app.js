// Basic app JS enhancements for cart and typeahead/autocomplete
document.addEventListener('DOMContentLoaded', function(){
	// Payment method toggle (keeps compatibility with inline scripts)
	const pm = document.getElementById('payment_method');
	if(pm){
		pm.addEventListener('change', function(){
			const isCash = pm.value==='cash';
			const isOnline = pm.value==='online';
			document.querySelectorAll('.cash-only').forEach(e=>e.classList.toggle('d-none', !isCash));
			document.querySelectorAll('.online-only').forEach(e=>e.classList.toggle('d-none', !isOnline));
		});
	}

	// Simple debounce helper
	function debounce(fn, wait){
		let t;
		return function(...args){ clearTimeout(t); t = setTimeout(()=>fn.apply(this,args), wait); };
	}

	// Typeahead for inputs with data-typeahead="/inventory/items"
	document.querySelectorAll('input[data-typeahead]').forEach(function(inp){
		const url = inp.getAttribute('data-typeahead');
		const listId = inp.getAttribute('list') || (inp.name + '_list');
		let datalist = document.getElementById(listId);
		if(!datalist){ datalist = document.createElement('datalist'); datalist.id = listId; document.body.appendChild(datalist); inp.setAttribute('list', listId); }

		const fetchSuggestions = debounce(function(){
			const q = inp.value.trim();
			if(!q) return;
			fetch(url + '?q=' + encodeURIComponent(q)).then(r=>r.json()).then(items=>{
				datalist.innerHTML = '';
				items.forEach(it=>{
					const opt = document.createElement('option');
                    // options to show supplier also
					opt.value = `${it.sku} | ${it.name} | ${it.supplier}`;
					opt.setAttribute('data-sku', it.sku);
					opt.setAttribute('data-price', it.sale_price);
					opt.setAttribute('data-tax', it.tax_rate);
					datalist.appendChild(opt);
				});
			}).catch(()=>{});
		}, 250);

		inp.addEventListener('input', fetchSuggestions);
	});

    // Select all/Deselect all
    const selectItemsButton = document.getElementById('select_items');
    if(selectItemsButton){
        selectItemsButton.addEventListener('click', function(){
            document.querySelectorAll('.item-checkbox').forEach(function(checkbox){
                checkbox.checked = !checkbox.checked;
            });
        });
    }

    // Toggle-all checkbox (new)
    const toggleAllBox = document.getElementById('toggle_all');
    if(toggleAllBox){
        toggleAllBox.addEventListener('change', function(){
            const checked = toggleAllBox.checked;
            document.querySelectorAll('.item-checkbox').forEach(cb => cb.checked = checked );
        });
    }


    // Delete selected
    const deleteSelectedButton = document.getElementById('delete_selected');
    if(deleteSelectedButton){
        deleteSelectedButton.addEventListener('click', function(){
            const selected = [];
            document.querySelectorAll('.item-checkbox:checked').forEach(function(checkbox){
                selected.push(checkbox.value);
            });
            if(selected.length){
                if(confirm("Are you sure you want to delete the selected items?")){
                    fetch('/inventory/items/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ids: selected })
                    }).then(response => {
                        if(response.ok){
                            location.reload();
                        }else{
                            alert("Error deleting items");
                        }
                    });
                }
            }else{
                alert("No items selected");
            }
        });
    }


	// Cart helpers for the sales cart page
	const cartTable = document.getElementById('dynamic-cart-table');
	if(cartTable){
			const addRowFromInput = function(sku, name, price, tax, qty){
				// prevent duplicate SKU rows; if exists, increment qty
				var existing = cartTable.querySelector('[name="qty_' + sku + '"]');
				if(!existing){
					var matches = document.getElementsByName('qty_' + sku);
					if(matches && matches.length) existing = matches[0];
				}
				if(existing){
					try{
						existing.value = (parseFloat(existing.value || 0) + parseFloat(qty || 1)).toString();
						computeTotals();
					}catch(e){ }
					return;
				}
				const tbody = cartTable.querySelector('tbody');
				const tr = document.createElement('tr');
				tr.innerHTML = `
					<td><input type="hidden" name="sku_${sku}" value="on"><strong>${sku}</strong></td>
					<td>${name}</td>
					<td class="line-price">${price.toFixed(2)}</td>
					<td class="line-tax">${tax.toFixed(2)}</td>
					<td style="width:140px"><input class="form-control line-qty" type="number" step="0.01" min="0" name="qty_${sku}" value="${qty}"></td>
					<td><button type="button" class="btn btn-sm btn-danger btn-remove">Remove</button></td>
				`;
				tbody.appendChild(tr);
				tr.querySelector('.btn-remove').addEventListener('click', function(){ tr.remove(); computeTotals(); });
				tr.querySelector('.line-qty').addEventListener('input', debounce(function(){ computeTotals(); }, 100));
				computeTotals();
			};

		// If there's an add-item input, wire it
		const addInput = document.getElementById('add_item_input');
			if(addInput){
				// handle selection from datalist; listen to blur to allow selection via click
				addInput.addEventListener('change', function(e){
					handleAddInputSelection();
				});
				addInput.addEventListener('keydown', function(e){
					if(e.key === 'Enter'){
						e.preventDefault();
						handleAddInputSelection();
					}
				});
				const handleAddInputSelection = debounce(function(){
					const val = addInput.value.trim();
					if(!val) return;
					const parts = val.split('|').map(s=>s.trim());
					const sku = parts[0];
					fetch('/inventory/items?q=' + encodeURIComponent(sku)).then(r=>r.json()).then(items=>{
						const it = items.find(x => x.sku === sku || (`${x.sku} | ${x.name}` === val));
						if(it){ addRowFromInput(it.sku, it.name, it.sale_price, it.tax_rate, 1); addInput.value = ''; }
					}).catch(()=>{});
				}, 150);
			}

			// compute totals
			function parseNum(v){ return parseFloat(v||0)||0; }
			function computeTotals(){
				var subtotal = 0, tax = 0;
				var rows = cartTable.querySelectorAll('tbody tr');
				for(var i=0;i<rows.length;i++){
					var tr = rows[i];
					var priceEl = tr.querySelector('.line-price');
					var taxEl = tr.querySelector('.line-tax');
					var qtyEl = tr.querySelector('.line-qty');
					var price = parseNum(priceEl ? priceEl.textContent : 0);
					var taxrate = parseNum(taxEl ? taxEl.textContent : 0);
					var qty = parseNum(qtyEl ? qtyEl.value : 0);
					subtotal += price * qty;
					tax += (price * qty) * (taxrate/100);
				}
				var discount = parseNum((document.getElementById('discount_input') && document.getElementById('discount_input').value) || 0);
				var total = subtotal + tax - discount;
				var outSubtotal = document.getElementById('cart_subtotal'); if(outSubtotal) outSubtotal.textContent = subtotal.toFixed(2);
				var outTax = document.getElementById('cart_tax'); if(outTax) outTax.textContent = tax.toFixed(2);
				var outDisc = document.getElementById('cart_discount'); if(outDisc) outDisc.textContent = discount.toFixed(2);
				var outTotal = document.getElementById('cart_total'); if(outTotal) outTotal.textContent = total.toFixed(2);
				// if payment is cash, auto-fill paid amount
				var pm = document.getElementById('payment_method');
				var paidInput = document.getElementById('paid_amount');
				if(pm && pm.value === 'cash' && paidInput){ paidInput.value = total.toFixed(2); }
			}
			// watch discount and payment method
			document.getElementById('discount_input')?.addEventListener('input', debounce(()=>computeTotals(), 80));
			document.getElementById('payment_method')?.addEventListener('change', () => computeTotals());
			// initial compute
			computeTotals();
	}
});
