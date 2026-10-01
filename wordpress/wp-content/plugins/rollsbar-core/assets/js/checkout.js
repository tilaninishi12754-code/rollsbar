(function(){
	'use strict';

	var config=window.rollsBarCheckoutConfig||{};
	var prefix=typeof config.phonePrefix==='string'&&config.phonePrefix?config.phonePrefix:'+7 ';

	function looksLikePhone(input){
		if(!input||input.tagName!=='INPUT')return false;
		var type=(input.getAttribute('type')||'').toLowerCase();
		var name=(input.getAttribute('name')||'').toLowerCase();
		var id=(input.id||'').toLowerCase();
		var autocomplete=(input.getAttribute('autocomplete')||'').toLowerCase();

		return type==='tel'||autocomplete==='tel'||name.indexOf('phone')!==-1||id.indexOf('phone')!==-1;
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
			if(/^8[s(\-]?\d/.test(raw)){
				setNativeValue(input,'+7 '+raw.replace(/^8\s*/,''));
			}
		});
	}

	function scan(){
		document.querySelectorAll('input').forEach(preparePhone);
	}

	scan();

	new MutationObserver(scan).observe(document.documentElement,{
		childList:true,
		subtree:true
	});
})();
