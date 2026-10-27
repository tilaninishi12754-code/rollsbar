(function(){
	'use strict';

	var config=window.rollsBarCheckoutConfig||{};
	var prefix=typeof config.phonePrefix==='string'&&config.phonePrefix?config.phonePrefix:'+7 ';
	var addressConfig=config.addressSuggestions||{};
	var addressEnabled=addressConfig.enabled===true&&typeof addressConfig.suggestUrl==='string'&&typeof addressConfig.resolveUrl==='string';
	var minChars=Number(addressConfig.minChars)||3;
	var debounceMs=Number(addressConfig.debounceMs)||300;
	var panel=null;
	var activeInput=null;
	var activeRequest=null;
	var debounceTimer=null;
	var resolveRequests=new WeakMap();
	var nativeContextPrepared=false;
	var summaryObserver=null;
	var deliveryAddress=null;
	var deliverySubscription=false;
	var deliveryError='';
	var deliveryProof='';
	function syncDelivery(){
		if(!window.wp||!wp.data)return;
		var checkout=wp.data.select('wc/store/checkout'),cart=wp.data.select('wc/store/cart');
		if(!checkout||!cart||!checkout.prefersCollection)return;
		var pickup=checkout.prefersCollection();
		document.body.classList.toggle('rollsbar-checkout-pickup',pickup);
		var customer=cart.getCustomerData(),address=pickup?'':String((customer.shippingAddress||{}).address_1||(customer.billingAddress||{}).address_1||'');
		var totals=cart.getCartTotals(),minor=Number(totals.currency_minor_unit)||0;
		var amount=(Number(totals.total_items)-Number(totals.total_discount))/Math.pow(10,minor);
		var valid=deliveryAddress&&address===deliveryAddress.display;
		var rule=valid?deliveryAddress.delivery:null;
		var message=pickup?'':!rule?'Выберите адрес с домом из подсказок, чтобы определить условия доставки.':rule.message;
		if(!pickup&&rule&&rule.status==='resolved'){
			message=amount<rule.minimum?'Минимальный заказ для доставки — '+rule.minimum.toLocaleString('ru-RU')+' ₽. Добавьте товары на '+(rule.minimum-amount).toLocaleString('ru-RU')+' ₽.':'';
		}
		if(message!==deliveryError){
			deliveryError=message;
			var validation=wp.data.dispatch('wc/store/validation');
			if(message)validation.setValidationErrors({'rollsbar-delivery-minimum':{message:message,hidden:false}});
			else validation.clearValidationError('rollsbar-delivery-minimum');
		}
		var proof=valid?deliveryAddress.address_proof:'';
		if(proof!==deliveryProof){deliveryProof=proof;wp.data.dispatch('wc/store/checkout').setExtensionData('rollsbar-delivery',{address_proof:proof});}
		var input=document.querySelector(pickup?'#billing-address_1':'#shipping-address_1')||document.querySelector('#billing-address_1');
		if(input&&!pickup){
			input.setAttribute('aria-required','true');
			setAddressStatus(input,message||(rule&&rule.message)||'',message?'warning':'success');
		}
		if(!deliverySubscription){deliverySubscription=true;wp.data.subscribe(syncDelivery);}
	}
	function prepareOrderNote(){
		var sameAddress=document.querySelector('.wc-block-checkout__use-address-for-billing input');
		if(sameAddress&&!sameAddress.checked)sameAddress.click();
		var box=document.querySelector('.wc-block-checkout__add-note input[type="checkbox"]');
		if(box&&!box.checked)box.click();
		var text=document.querySelector('.wc-block-checkout__add-note textarea');
		if(text){text.placeholder='Комментарий к заказу';text.setAttribute('aria-label','Комментарий к заказу');}
	}
	function positionNativeAction(){
		var layout=document.querySelector('.wc-block-components-sidebar-layout');
		var summary=document.querySelector('.wc-block-checkout__sidebar .wp-block-woocommerce-checkout-order-summary-block');
		var sidebar=document.querySelector('.wc-block-checkout__sidebar');
		if(!layout||!summary||!sidebar)return;
		var base=layout.getBoundingClientRect(),card=summary.getBoundingClientRect(),lane=sidebar.getBoundingClientRect();
		layout.style.setProperty('--rb-action-top',(card.bottom-base.top+16)+'px');
		layout.style.setProperty('--rb-action-left',(lane.left-base.left+17)+'px');
		layout.style.setProperty('--rb-action-width',(lane.width-34)+'px');
		if(!summaryObserver&&window.ResizeObserver){
			summaryObserver=new ResizeObserver(positionNativeAction);
			summaryObserver.observe(summary);summaryObserver.observe(layout);
		}
	}
	function prepareNativeSummary(){
		var title=document.querySelector('.wc-block-checkout__sidebar .wc-block-components-checkout-order-summary__title');
		if(!title||title.getAttribute('role')!=='button'||title.dataset.rollsbarExpanded==='1')return;
		title.dataset.rollsbarExpanded='1';
		// Use Woo's own presentation toggle; source summary is initially expanded.
		if(title.getAttribute('aria-expanded')==='false')title.click();
	}

	function prepareNativeContext(){
		if(nativeContextPrepared||!window.wp||!wp.data||!document.querySelector('.wp-block-woocommerce-checkout'))return;
		var store=wp.data.select('wc/store/cart');
		if(!store||!store.getCustomerData)return;
		nativeContextPrepared=true;
		var updating=false;
		function sync(){
			if(updating)return;
			var customer=store.getCustomerData(),billing=customer.billingAddress,shipping=customer.shippingAddress;
			if(!billing||!shipping)return;
			updating=true;
			try{
				var patch={};
				if(billing.country!=='RU')patch.country='RU';
				if(config.internalEmail&&billing.email!==config.internalEmail)patch.email=config.internalEmail;
				if(Object.keys(patch).length)wp.data.dispatch('wc/store/cart').setBillingAddress(patch);
				if(shipping.country!=='RU')wp.data.dispatch('wc/store/cart').setShippingAddress({country:'RU'});
			}finally{updating=false;}
		}
		sync();
		wp.data.subscribe(sync,'wc/store/cart');
	}

	function looksLikePhone(input){
		if(!input||input.tagName!=='INPUT')return false;
		var type=(input.getAttribute('type')||'').toLowerCase();
		var name=(input.getAttribute('name')||'').toLowerCase();
		var id=(input.id||'').toLowerCase();
		var autocomplete=(input.getAttribute('autocomplete')||'').toLowerCase();

		return type==='tel'||autocomplete==='tel'||name.indexOf('phone')!==-1||id.indexOf('phone')!==-1;
	}

	function looksLikeAddress(input){
		if(!addressEnabled||!input||input.tagName!=='INPUT')return false;
		var name=(input.getAttribute('name')||'').toLowerCase();
		var id=(input.id||'').toLowerCase();
		var autocomplete=(input.getAttribute('autocomplete')||'').toLowerCase();
		return /address_1$/.test(name)||id.indexOf('address_1')!==-1||autocomplete==='address-line1';
	}

	function setNativeValue(input,value){
		var descriptor=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value');
		if(descriptor&&descriptor.set){
			descriptor.set.call(input,value);
		}else{
			input.value=value;
		}
		input.dispatchEvent(new Event('input',{bubbles:true}));
		input.dispatchEvent(new Event('change',{bubbles:true}));
	}

	function preparePhone(input){
		if(!looksLikePhone(input))return;
		if(input.dataset.rollsbarPhonePrepared==='1')return;
		input.dataset.rollsbarPhonePrepared='1';

		if(!String(input.value||'').trim()){
			setNativeValue(input,prefix);
		}

		input.addEventListener('blur',function(){
			var raw=String(input.value||'').trim();
			if(/^8[\s(\-]?\d/.test(raw)){
				setNativeValue(input,'+7 '+raw.replace(/^8\s*/,''));
			}
		});
	}

	function ensurePanel(){
		if(panel)return panel;
		panel=document.createElement('div');
		panel.className='rollsbar-address-suggestions';
		panel.id='rollsbarAddressSuggestions';
		panel.setAttribute('role','listbox');
		panel.setAttribute('aria-label','Подсказки адреса');
		panel.hidden=true;
		document.body.appendChild(panel);
		var dialog=document.querySelector('[data-rollsbar-modal="1"]');
		if(dialog)dialog.setAttribute('aria-owns',panel.id);
		return panel;
	}

	function positionPanel(){
		if(!panel||panel.hidden||!activeInput)return;
		var rect=activeInput.getBoundingClientRect();
		var width=Math.min(Math.max(rect.width,260),document.documentElement.clientWidth-24);
		var left=Math.max(12,Math.min(rect.left,document.documentElement.clientWidth-width-12));
		panel.style.left=(window.scrollX+left)+'px';
		panel.style.top=(window.scrollY+rect.bottom+4)+'px';
		panel.style.width=width+'px';
	}

	// Display only: Woo owns the inputs; DaData alone supplies an exact point.
	// This decoration never updates the cart, rates, native fields or order state.
	function addressMap(input,result){
		return; // Owner deferred the map; retain provider precision for delivery rules.
		var step=input.closest('.wc-block-components-checkout-step__content');
		if(!step)return;
		var card=step.querySelector('.rollsbar-checkout-map');
		if(!card){
			card=document.createElement('section');
			card.className='rollsbar-checkout-map';
			card.setAttribute('aria-label','Карта адреса');
			var frame=document.createElement('iframe');
			frame.title='Карта Rolls Bar';
			frame.loading='lazy';
			frame.referrerPolicy='no-referrer';
			card.appendChild(frame);
			var note=document.createElement('p');
			note.className='rollsbar-checkout-map__note';
			note.setAttribute('aria-live','polite');
			card.appendChild(note);
			step.appendChild(card);
		}
		var exact=result&&(result.qc_geo===0||result.qc_geo==='0')&&result.precision&&result.precision.allow_auto_zone===true;
		var lat=result&&result.lat,lon=result&&result.lon;
		exact=exact&&(typeof lat==='number'||typeof lat==='string')&&(typeof lon==='number'||typeof lon==='string')&&String(lat).trim()!==''&&String(lon).trim()!==''&&Number.isFinite(Number(lat))&&Number.isFinite(Number(lon))&&Math.abs(Number(lat))<=90&&Math.abs(Number(lon))<=180;
		// Initial/approximate state shows the existing public business listing,
		// never an invented customer coordinate or delivery polygon.
		var src='https://yandex.ru/map-widget/v1/?mode=search&oid=229692973623&ol=biz&z=13&lang=ru_RU';
		if(exact){
			var point=Number(lon)+','+Number(lat);
			src='https://yandex.ru/map-widget/v1/?ll='+encodeURIComponent(point)+'&pt='+encodeURIComponent(point+',pm2rdm')+'&z=17&lang=ru_RU';
		}
		var iframe=card.querySelector('iframe');
		if(iframe.getAttribute('src')!==src)iframe.src=src;
		iframe.title=exact?'Карта точно определённого адреса':'Карта Rolls Bar';
		card.dataset.exact=exact?'1':'0';
		card.querySelector('p').textContent=exact?'Адрес определён точно. Карта показывает адрес, условия получения подтверждает оператор.':result?'Уточните адрес до дома. На карте — Rolls Bar, точка вашего адреса пока не определена.':'На карте — Rolls Bar. Выберите адрес из подсказок, чтобы увидеть его точку. Условия получения подтверждает оператор.';
	}

	function decorateCheckout(){
		var checkout=document.querySelector('.wp-block-woocommerce-checkout');
		if(!checkout||document.body.classList.contains('woocommerce-order-received'))return;
		if(!document.querySelector('.rollsbar-checkout-title')){
			var title=document.createElement('h1');
			title.className='rollsbar-checkout-title';
			title.textContent='Оформление заказа';
			checkout.before(title);
		}
		var shell=checkout.closest('.rollsbar-shell');
		if(!shell||shell.dataset.rollsbarModal==='1')return;
		shell.dataset.rollsbarModal='1';
		shell.setAttribute('role','dialog');
		shell.setAttribute('aria-modal','true');
		shell.setAttribute('aria-labelledby','rollsbarCheckoutHeading');
		shell.setAttribute('tabindex','-1');
		document.querySelector('.rollsbar-checkout-title').id='rollsbarCheckoutHeading';
		var close=shell.querySelector('.rollsbar-legal-page__back');
		close.setAttribute('aria-label','Закрыть оформление и вернуться в меню');
		var heading=document.querySelector('.rollsbar-checkout-title');
		var head=document.createElement('div');
		head.className='rollsbar-checkout-head';
		heading.before(head);
		head.appendChild(heading);
		head.appendChild(close);
		var backdrop=document.createElement('button');
		backdrop.type='button';
		backdrop.className='rollsbar-checkout-backdrop';
		backdrop.setAttribute('aria-label','Закрыть оформление и вернуться в меню');
		backdrop.tabIndex=-1;
		shell.before(backdrop);
		backdrop.addEventListener('click',function(){close.click();});
		document.querySelectorAll('body > header,body > footer,body > .rollsbar-mobile-cart').forEach(function(node){node.inert=true;});
		shell.focus({preventScroll:true});
		document.addEventListener('keydown',function(event){
			if(event.key==='Escape'){
				if(panel&&!panel.hidden){hidePanel();event.preventDefault();return;}
				event.preventDefault();close.click();return;
			}
			if(event.key!=='Tab')return;
			var candidates=Array.from(shell.querySelectorAll('a[href],button,input,select,textarea,[tabindex="0"]'));
			if(panel&&!panel.hidden)candidates=candidates.concat(Array.from(panel.querySelectorAll('button,a[href]')));
			var targets=candidates.filter(function(n){return !n.disabled&&n.getClientRects().length;});
			if(!targets.length){event.preventDefault();shell.focus();return;}
			var first=targets[0],last=targets[targets.length-1];
			if(event.shiftKey&&(document.activeElement===first||document.activeElement===shell)){event.preventDefault();last.focus();}
			else if(!event.shiftKey&&(document.activeElement===last||document.activeElement===shell)){event.preventDefault();first.focus();}
		});
	}

	function hidePanel(){
		if(panel)panel.hidden=true;
		if(activeRequest){
			activeRequest.abort();
			activeRequest=null;
		}
	}

	function statusNode(input){
		if(!input)return null;
		var holder=input.parentNode;
		if(!holder)return null;
		var existing=holder.querySelector('.rollsbar-address-status');
		if(existing)return existing;
		var node=document.createElement('div');
		node.className='rollsbar-address-status';
		node.setAttribute('aria-live','polite');
		holder.appendChild(node);
		return node;
	}

	function setAddressStatus(input,message,kind){
		var node=statusNode(input);
		if(!node)return;
		if(node.textContent!==(message||''))node.textContent=message||'';
		var className='rollsbar-address-status'+(kind?' is-'+kind:'');
		if(node.className!==className)node.className=className;
		node.hidden=!message;
	}

	function clearResolvedState(input){
		if(!input)return;
		resolveRequests.delete(input);
		deliveryAddress=null;
		// Let Woo's React onChange consume this input before validation dispatches
		// can re-render the controlled field with its previous address.
		setTimeout(syncDelivery,0);
		delete input.dataset.rollsbarAddressResolved;
		delete input.dataset.rollsbarAddressQcGeo;
		delete input.dataset.rollsbarAddressLat;
		delete input.dataset.rollsbarAddressLon;
		delete input.dataset.rollsbarAddressAutoZone;
		setAddressStatus(input,'','');
		addressMap(input,null);
	}

	function providerFooter(container){
		var footer=document.createElement('div');
		footer.className='rollsbar-address-suggestions__provider';
		var link=document.createElement('a');
		link.href='https://dadata.ru/';
		link.target='_blank';
		link.rel='noopener noreferrer';
		link.textContent='Подсказки: DaData';
		footer.appendChild(link);
		container.appendChild(footer);
	}

	function renderSuggestions(input,items){
		var box=ensurePanel();
		box.innerHTML='';
		activeInput=input;

		if(!Array.isArray(items)||!items.length){
			var empty=document.createElement('div');
			empty.className='rollsbar-address-suggestions__empty';
			empty.textContent='Адрес не найден';
			box.appendChild(empty);
			providerFooter(box);
			box.hidden=false;
			positionPanel();
			return;
		}

		items.forEach(function(item){
			if(!item||typeof item.display!=='string'||typeof item.token!=='string')return;
			var button=document.createElement('button');
			button.type='button';
			button.className='rollsbar-address-suggestions__item';
			button.setAttribute('role','option');
			button.textContent=item.display;
			button.addEventListener('mousedown',function(event){
				event.preventDefault();
			});
			button.addEventListener('click',function(){
				resolveSuggestion(input,item);
			});
			box.appendChild(button);
		});

		providerFooter(box);
		box.hidden=false;
		positionPanel();
	}

	function requestSuggestions(input){
		var query=String(input.value||'').trim();
		if(query.length<minChars){
			hidePanel();
			return;
		}

		if(activeRequest)activeRequest.abort();
		activeRequest=new AbortController();
		var url=addressConfig.suggestUrl+(addressConfig.suggestUrl.indexOf('?')===-1?'?':'&')+'query='+encodeURIComponent(query);

		fetch(url,{
			method:'GET',
			credentials:'same-origin',
			headers:{'Accept':'application/json'},
			signal:activeRequest.signal
		}).then(function(response){
			if(!response.ok)throw new Error('suggestions '+response.status);
			return response.json();
		}).then(function(payload){
			activeRequest=null;
			if(activeInput&&activeInput!==input)return;
			if(String(input.value||'').trim()!==query)return;
			renderSuggestions(input,payload&&payload.suggestions?payload.suggestions:[]);
		}).catch(function(error){
			if(error&&error.name==='AbortError')return;
			activeRequest=null;
			hidePanel();
			setAddressStatus(input,'Подсказки адреса временно недоступны. Попробуйте позже или позвоните: +7 978 688-22-88.','warning');
		});
	}

	function resolveSuggestion(input,item){
		hidePanel();
		var requestIdentity={};
		resolveRequests.set(input,requestIdentity);
		setAddressStatus(input,'Проверяем адрес…','loading');

		fetch(addressConfig.resolveUrl,{
			method:'POST',
			credentials:'same-origin',
			headers:{
				'Accept':'application/json',
				'Content-Type':'application/json'
			},
			body:JSON.stringify({token:item.token})
		}).then(function(response){
			if(!response.ok)throw new Error('resolve '+response.status);
			return response.json();
		}).then(function(result){
			if(resolveRequests.get(input)!==requestIdentity||!input.isConnected)return;
			if(!result||typeof result.display!=='string')throw new Error('invalid resolve payload');

			input.dataset.rollsbarAddressProgrammatic='1';
			setNativeValue(input,result.display);
			delete input.dataset.rollsbarAddressProgrammatic;
			deliveryAddress=result;
			syncDelivery();

			var precision=result.precision||{};
			var allowAuto=precision.allow_auto_zone===true;
			input.dataset.rollsbarAddressResolved='1';
			input.dataset.rollsbarAddressQcGeo=result.qc_geo===null||typeof result.qc_geo==='undefined'?'':String(result.qc_geo);
			input.dataset.rollsbarAddressLat=result.lat===null||typeof result.lat==='undefined'?'':String(result.lat);
			input.dataset.rollsbarAddressLon=result.lon===null||typeof result.lon==='undefined'?'':String(result.lon);
			input.dataset.rollsbarAddressAutoZone=allowAuto?'1':'0';
			addressMap(input,result);

			if(result.delivery){
				syncDelivery();
			}else if(allowAuto){
				setAddressStatus(input,'Адрес определён точно.','success');
			}else if(Number(result.qc_geo)===1){
				setAddressStatus(input,'Проверьте дом: координаты соответствуют ближайшему известному дому.','warning');
			}else{
				setAddressStatus(input,'Уточните адрес до дома: координаты пока определены приблизительно.','warning');
			}

			input.dispatchEvent(new CustomEvent('rollsbar:address-resolved',{
				bubbles:true,
				detail:result
			}));
		}).catch(function(){
			if(resolveRequests.get(input)!==requestIdentity||!input.isConnected)return;
			setAddressStatus(input,'Не удалось уточнить адрес. Введите его вручную или попробуйте другой вариант.','error');
		});
	}

	function scheduleSuggestions(input){
		clearTimeout(debounceTimer);
		debounceTimer=setTimeout(function(){requestSuggestions(input);},debounceMs);
	}

	function prepareAddress(input){
		if(!looksLikeAddress(input))return;
		if(input.dataset.rollsbarAddressPrepared==='1')return;
		input.dataset.rollsbarAddressPrepared='1';
		input.setAttribute('autocomplete','off');
		addressMap(input,null);

		input.addEventListener('focus',function(){
			activeInput=input;
			if(String(input.value||'').trim().length>=minChars){
				scheduleSuggestions(input);
			}
		});

		input.addEventListener('input',function(){
			if(input.dataset.rollsbarAddressProgrammatic==='1')return;
			activeInput=input;
			hidePanel();
			clearResolvedState(input);
			scheduleSuggestions(input);
		});

		input.addEventListener('keydown',function(event){
			if(event.key==='Escape'&&panel&&!panel.hidden){hidePanel();event.preventDefault();event.stopPropagation();}
		});
	}

	function scan(){
		prepareNativeContext();
		if(!deliverySubscription)syncDelivery();
		prepareOrderNote();
		decorateCheckout();
		prepareNativeSummary();
		positionNativeAction();
		document.querySelectorAll('input').forEach(function(input){
			preparePhone(input);
			prepareAddress(input);
		});
	}

	document.addEventListener('click',function(event){
		if(!panel||panel.hidden)return;
		if(event.target===activeInput||panel.contains(event.target))return;
		hidePanel();
	});

	window.addEventListener('resize',positionPanel);
	window.addEventListener('resize',positionNativeAction);
	window.addEventListener('scroll',positionPanel,true);

	scan();
	new MutationObserver(scan).observe(document.documentElement,{
		childList:true,
		subtree:true
	});
})();
