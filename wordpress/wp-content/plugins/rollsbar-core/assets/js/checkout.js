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

		input.addEventListener('focus',function(){
			if(!String(input.value||'').trim()){
				setNativeValue(input,prefix);
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
		panel.setAttribute('role','listbox');
		panel.setAttribute('aria-label','Подсказки адреса');
		panel.hidden=true;
		document.body.appendChild(panel);
		return panel;
	}

	function positionPanel(){
		if(!panel||panel.hidden||!activeInput)return;
		var rect=activeInput.getBoundingClientRect();
		panel.style.left=(window.scrollX+rect.left)+'px';
		panel.style.top=(window.scrollY+rect.bottom+4)+'px';
		panel.style.width=Math.max(rect.width,260)+'px';
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
		node.textContent=message||'';
		node.className='rollsbar-address-status'+(kind?' is-'+kind:'');
		node.hidden=!message;
	}

	function clearResolvedState(input){
		if(!input)return;
		delete input.dataset.rollsbarAddressResolved;
		delete input.dataset.rollsbarAddressQcGeo;
		delete input.dataset.rollsbarAddressLat;
		delete input.dataset.rollsbarAddressLon;
		delete input.dataset.rollsbarAddressAutoZone;
		setAddressStatus(input,'','');
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
			renderSuggestions(input,payload&&payload.suggestions?payload.suggestions:[]);
		}).catch(function(error){
			if(error&&error.name==='AbortError')return;
			activeRequest=null;
			hidePanel();
			setAddressStatus(input,'Подсказки адреса временно недоступны. Можно ввести адрес вручную.','warning');
		});
	}

	function resolveSuggestion(input,item){
		hidePanel();
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
			if(!result||typeof result.display!=='string')throw new Error('invalid resolve payload');

			input.dataset.rollsbarAddressProgrammatic='1';
			setNativeValue(input,result.display);
			delete input.dataset.rollsbarAddressProgrammatic;

			var precision=result.precision||{};
			var allowAuto=precision.allow_auto_zone===true;
			input.dataset.rollsbarAddressResolved='1';
			input.dataset.rollsbarAddressQcGeo=result.qc_geo===null||typeof result.qc_geo==='undefined'?'':String(result.qc_geo);
			input.dataset.rollsbarAddressLat=result.lat===null||typeof result.lat==='undefined'?'':String(result.lat);
			input.dataset.rollsbarAddressLon=result.lon===null||typeof result.lon==='undefined'?'':String(result.lon);
			input.dataset.rollsbarAddressAutoZone=allowAuto?'1':'0';

			if(allowAuto){
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

		input.addEventListener('focus',function(){
			activeInput=input;
			if(String(input.value||'').trim().length>=minChars){
				scheduleSuggestions(input);
			}
		});

		input.addEventListener('input',function(){
			if(input.dataset.rollsbarAddressProgrammatic==='1')return;
			activeInput=input;
			clearResolvedState(input);
			scheduleSuggestions(input);
		});

		input.addEventListener('keydown',function(event){
			if(event.key==='Escape')hidePanel();
		});
	}

	function scan(){
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
	window.addEventListener('scroll',positionPanel,true);

	scan();
	new MutationObserver(scan).observe(document.documentElement,{
		childList:true,
		subtree:true
	});
})();
