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
	var deliveryAddress=config.deliverySelection||null;
	var previousDeliveryAddress=deliveryAddress;
	var deliverySubscription=false;
	var deliveryError='';
	var deliveryProof='';
	var contactPhoneError='';
	var deliveryMinimumError='';
	var deliveryTerms='Уточнит менеджер';
	var addressServiceError='';
	var consentAttempted=false;
	window.addEventListener('message',function(event){
		if(event.origin!==location.origin||!event.data||!['rollsbar-map-escape','rollsbar-map-ready'].includes(event.data.type))return;
		var frame=document.querySelector('.rollsbar-checkout-map iframe');
		if(!frame||event.source!==frame.contentWindow)return;
		if(event.data.type==='rollsbar-map-ready'){delete frame.dataset.rollsbarMapState;addressMap(document.querySelector('#shipping-address_1'),deliveryAddress);return;}
		var close=document.querySelector('[data-rollsbar-modal="1"] .rollsbar-legal-page__back');
		if(frame&&event.source===frame.contentWindow&&close)close.click();
	});
	function nativeAddressIdle(){
		return new Promise(function(resolve,reject){
			var stop=function(){};
			var timer=setTimeout(function(){stop();reject(new Error('native customer update timeout'));},10000);
			function ready(){
				var cart=wp.data.select('wc/store/cart'),checkout=wp.data.select('wc/store/checkout');
				if(!cart.isCustomerDataUpdating()&&!checkout.isCalculating()){clearTimeout(timer);stop();resolve();}
			}
			stop=wp.data.subscribe(ready);ready();
		});
	}
	function syncDelivery(){
		if(!window.wp||!wp.data)return;
		var checkout=wp.data.select('wc/store/checkout'),cart=wp.data.select('wc/store/cart');
		if(!checkout||!cart||!checkout.prefersCollection)return;
		var pickup=checkout.prefersCollection();
		if(pickup){clearTimeout(debounceTimer);hidePanel();activeInput=null;}
		document.body.classList.toggle('rollsbar-checkout-pickup',pickup);
		var customer=cart.getCustomerData(),contact=pickup?customer.billingAddress:customer.shippingAddress;
		var phone=String((contact||{}).phone||''),digits=phone.replace(/\D/g,'');
		var phoneError=phone.trim()&&(digits.length<10||digits.length>15)?'Укажите номер телефона полностью.':'';
		if(phoneError!==contactPhoneError){
			contactPhoneError=phoneError;
			var phoneValidation=wp.data.dispatch('wc/store/validation');
			if(phoneError)phoneValidation.setValidationErrors({'rollsbar-contact-phone':{message:phoneError,hidden:false}});
			else phoneValidation.clearValidationError('rollsbar-contact-phone');
		}
		setAddressStatus(document.querySelector(pickup?'#billing-phone':'#shipping-phone'),phoneError,phoneError?'warning':'');
		var address=pickup?'':String((customer.shippingAddress||{}).address_1||'');
		if(!deliveryAddress&&previousDeliveryAddress&&previousDeliveryAddress.display===address)deliveryAddress=previousDeliveryAddress;
		var totals=cart.getCartTotals(),minor=Number(totals.currency_minor_unit)||0;
		var amount=(Number(totals.total_items)-Number(totals.total_discount))/Math.pow(10,minor);
		var valid=deliveryAddress&&address===deliveryAddress.display;
		var rule=valid?deliveryAddress.delivery:null;
		var unknownMessage=addressServiceError||(!address?'Укажите улицу и дом и выберите адрес из подсказок. Если адрес не находится, отправьте заявку — менеджер поможет.':!valid?'Выберите адрес с номером дома из подсказок. Если его нет в списке, отправьте заявку — менеджер поможет.':'Условия доставки по этому адресу пока не определены. Отправьте заявку — менеджер свяжется с вами и уточнит условия.');
		var message=pickup?'':unknownMessage;
		var minimumError='';
		deliveryTerms='Уточнит менеджер';
		if(!pickup&&rule&&rule.status==='resolved'){
			var minimum=Number(rule.minimum),missing=Math.max(0,Math.round((minimum-amount)*100)/100);
			minimumError=missing>0?'Минимальный заказ для доставки — '+minimum.toLocaleString('ru-RU')+' ₽. Добавьте товаров ещё на '+missing.toLocaleString('ru-RU')+' ₽.':'';
			message=minimumError||'Минимум '+minimum.toLocaleString('ru-RU')+' ₽ набран — доставка бесплатная.';
			deliveryTerms=minimumError?'От '+minimum.toLocaleString('ru-RU')+' ₽':'Бесплатно';
		}
		if(minimumError!==deliveryMinimumError){
			deliveryMinimumError=minimumError;
			var nativeValidation=wp.data.dispatch('wc/store/validation');
			if(minimumError)nativeValidation.setValidationErrors({'rollsbar-delivery-minimum':{message:minimumError,hidden:false}});
			else nativeValidation.clearValidationError('rollsbar-delivery-minimum');
		}
		if(message!==deliveryError){
			deliveryError=message;
		}
		prepareShippingTerms(pickup);
		var proof=valid?deliveryAddress.address_proof:'';
		if(proof!==deliveryProof){deliveryProof=proof;wp.data.dispatch('wc/store/checkout').setExtensionData('rollsbar-delivery',{address_proof:proof});}
		var input=document.querySelector(pickup?'#billing-address_1':'#shipping-address_1')||document.querySelector('#billing-address_1');
		if(input&&!pickup){
			input.setAttribute('aria-required','false');
			setAddressStatus(input,message||(rule&&rule.message)||'',message?'warning':'success');
			addressMap(input,valid?deliveryAddress:null);
		}
		if(!deliverySubscription){deliverySubscription=true;wp.data.subscribe(syncDelivery);}
	}
	function prepareShippingTerms(pickup){
		document.querySelectorAll('.wc-block-components-totals-shipping .wc-block-components-totals-item__value:not(.rollsbar-delivery-terms)').forEach(function(value){
			var own=value.parentNode.querySelector('.rollsbar-delivery-terms');
			value.hidden=!pickup;
			if(pickup){if(own)own.remove();return;}
			if(!own){own=document.createElement('span');own.className='rollsbar-delivery-terms wc-block-components-totals-item__value';own.setAttribute('aria-live','polite');value.after(own);}
			if(own.textContent!==deliveryTerms)own.textContent=deliveryTerms;
		});
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
		var action=document.querySelector('.wc-block-checkout__actions');
		if(action)sidebar.style.paddingBottom=(action.getBoundingClientRect().height+44)+'px';
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

		input.placeholder=prefix+'999 999-99-99';
		if(String(input.value||'').trim()===prefix.trim())setNativeValue(input,'');
		input.addEventListener('input',function(){
			var raw=String(input.value||''),cursor=input.selectionStart;
			if(/^[78]/.test(raw)){
				setNativeValue(input,'+7'+raw.slice(1));
				if(cursor!==null)input.setSelectionRange(cursor+1,cursor+1);
			}
		});

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
		if(!input||!config.mapUrl||input.id!=='shipping-address_1')return;
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
			frame.src=config.mapUrl;
			frame.addEventListener('load',function(){addressMap(input,deliveryAddress);});
			card.appendChild(frame);
			var note=document.createElement('p');
			note.className='rollsbar-checkout-map__note';
			note.setAttribute('aria-live','polite');
			card.appendChild(note);
			var form=input.closest('.wc-block-components-address-form');
			if(form)form.after(card);else step.appendChild(card);
		}
		var exact=result&&(result.qc_geo===0||result.qc_geo==='0')&&result.precision&&result.precision.allow_auto_zone===true;
		var lat=result&&result.lat,lon=result&&result.lon;
		exact=exact&&(typeof lat==='number'||typeof lat==='string')&&(typeof lon==='number'||typeof lon==='string')&&String(lat).trim()!==''&&String(lon).trim()!==''&&Number.isFinite(Number(lat))&&Number.isFinite(Number(lon))&&Math.abs(Number(lat))<=90&&Math.abs(Number(lon))<=180;
		// Initial/approximate state shows the existing public business listing,
		// never an invented customer coordinate or delivery polygon.
		var iframe=card.querySelector('iframe');
		iframe.title='Карта адреса и зон доставки Rolls Bar';
		var state=JSON.stringify({type:'rollsbar-map-address',exact:!!exact,lat:exact?Number(lat):null,lon:exact?Number(lon):null});
		if(iframe.contentWindow&&iframe.dataset.rollsbarMapState!==state){iframe.contentWindow.postMessage(JSON.parse(state),location.origin);iframe.dataset.rollsbarMapState=state;}
		card.dataset.exact=exact?'1':'0';
		card.querySelector('p').textContent=exact?'Ваш адрес отмечен на карте. Цвет зоны показывает минимальный заказ для бесплатной доставки. Точные условия подтвердит менеджер.':result?'Точка адреса пока определена приблизительно. Уточните дом или оставьте номер — менеджер поможет.':'Выберите адрес из подсказок — покажем его на карте. Цветные зоны обозначают минимальный заказ для бесплатной доставки.';
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
			empty.textContent='Адрес не найден в наших подсказках. Проверьте улицу и дом или отправьте заявку — менеджер поможет.';
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
		if(!input.getClientRects().length||document.body.classList.contains('rollsbar-checkout-pickup'))return;
		var query=String(input.value||'').trim();
		addressServiceError='';
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
			if(!input.getClientRects().length||document.body.classList.contains('rollsbar-checkout-pickup'))return;
			if(activeInput&&activeInput!==input)return;
			if(String(input.value||'').trim()!==query)return;
			renderSuggestions(input,payload&&payload.suggestions?payload.suggestions:[]);
		}).catch(function(error){
			if(error&&error.name==='AbortError')return;
			activeRequest=null;
			hidePanel();
			addressServiceError='Подсказки временно недоступны. Адрес можно написать вручную и отправить заявку — менеджер уточнит условия доставки.';
			setAddressStatus(input,addressServiceError,'warning');
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
		}).then(async function(result){
			if(resolveRequests.get(input)!==requestIdentity||!input.isConnected)return;
			if(!result||typeof result.display!=='string')throw new Error('invalid resolve payload');

			var nativeCart=window.wp&&wp.data&&wp.data.dispatch('wc/store/cart');
			if(nativeCart&&nativeCart.setShippingAddress&&nativeCart.setBillingAddress&&nativeCart.updateCustomerData){
				// Commit the confirmed value through Woo's public address state. DOM
				// input events alone can leave a debounced raw query in the session.
				if((input.id||'').indexOf('shipping-')===0){
					nativeCart.setShippingAddress({address_1:result.display});
					var nativeCheckout=wp.data.select('wc/store/checkout');
					if(nativeCheckout&&nativeCheckout.getUseShippingAsBilling())nativeCart.setBillingAddress({address_1:result.display});
				}else nativeCart.setBillingAddress({address_1:result.display});
				await nativeAddressIdle();
				if(resolveRequests.get(input)!==requestIdentity||!input.isConnected)return;
				var customer=wp.data.select('wc/store/cart').getCustomerData();
				var patch=(input.id||'').indexOf('shipping-')===0?{shipping_address:Object.assign({},customer.shippingAddress,{address_1:result.display})}:{billing_address:Object.assign({},customer.billingAddress,{address_1:result.display})};
				if(patch.shipping_address&&nativeCheckout&&nativeCheckout.getUseShippingAsBilling())patch.billing_address=Object.assign({},customer.billingAddress,{address_1:result.display});
				await nativeCart.updateCustomerData(patch);
			}else throw new Error('Native Woo customer data unavailable');
			if(resolveRequests.get(input)!==requestIdentity||!input.isConnected)return;
			deliveryAddress=result;
			previousDeliveryAddress=result;
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
			addressServiceError='Не удалось уточнить адрес. Выберите вариант с номером дома или отправьте заявку — менеджер свяжется с вами и поможет.';
			setAddressStatus(input,addressServiceError,'warning');
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
			if(input.dataset.rollsbarAddressResolved==='1')return;
			if(String(input.value||'').trim().length>=minChars){
				scheduleSuggestions(input);
			}
		});

		input.addEventListener('input',function(){
			if(input.dataset.rollsbarAddressProgrammatic==='1')return;
			addressServiceError='';
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
		prepareSubmissionFeedback();
		prepareShippingTerms(document.body.classList.contains('rollsbar-checkout-pickup'));
		document.querySelectorAll('input').forEach(function(input){
			preparePhone(input);
			prepareAddress(input);
		});
	}

	// Custom native validation keys have no Woo field to scroll to automatically.
	function prepareSubmissionFeedback(){
		var actions=document.querySelector('.wc-block-checkout__actions');
		if(!actions)return;
		var feedback=actions.querySelector('.rollsbar-submit-feedback');
		if(!feedback){
			feedback=document.createElement('div');feedback.className='rollsbar-submit-feedback';
			feedback.setAttribute('role','status');feedback.setAttribute('aria-live','polite');
			actions.prepend(feedback);
		}
		var consent=document.querySelector('#order-rollsbar-privacy-consent');
		var missingConsent=consent&&!consent.checked;
		var consentBlock=consent&&(consent.closest('.wc-block-components-address-form__rollsbar-privacy-consent')||consent.closest('.wc-block-components-checkbox'));
		if(consentBlock)consentBlock.classList.toggle('rollsbar-consent-missing',!!(consentAttempted&&missingConsent));
		if(consent&&consent.dataset.rollsbarConsentPrepared!=='1'){
			consent.dataset.rollsbarConsentPrepared='1';consent.addEventListener('change',prepareSubmissionFeedback);
		}
		var message=contactPhoneError||deliveryMinimumError||(consentAttempted&&missingConsent?'Подтвердите согласие на обработку персональных данных.':'Оставьте телефон и отметьте согласие — менеджер перезвонит и уточнит детали заявки.');
		if(feedback.textContent!==message)feedback.textContent=message;
		feedback.hidden=!message;
		var button=actions.querySelector('.wc-block-components-checkout-place-order-button');
		if(!button||button.dataset.rollsbarFeedback==='1')return;
		button.dataset.rollsbarFeedback='1';
		button.addEventListener('click',function(){
			consentAttempted=true;prepareSubmissionFeedback();
			var currentConsent=document.querySelector('#order-rollsbar-privacy-consent');
			var currentPhone=Array.from(document.querySelectorAll('input[id$="-phone"]')).find(function(n){return n.getClientRects().length;});
			var selector=contactPhoneError||(currentPhone&&!currentPhone.value.trim())?'input[id$="-phone"]':currentConsent&&!currentConsent.checked?'#order-rollsbar-privacy-consent':deliveryMinimumError?'#shipping-address_1':null;
			if(!selector)return;
			window.setTimeout(function(){
				var field=Array.from(document.querySelectorAll(selector)).find(function(n){return n.getClientRects().length;});
				if(field){field.focus({preventScroll:true});(field.closest('.rollsbar-consent-missing')||field).scrollIntoView({block:'center',behavior:'instant'});}
			},0);
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
