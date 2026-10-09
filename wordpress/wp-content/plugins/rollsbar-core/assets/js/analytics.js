(function($){
	'use strict';

	var config=window.rollsBarAnalyticsConfig||{};
	var counterId=parseInt(config.counterId||0,10);
	var goals=config.goals||{};
	var context=config.context||{};
	var consentKey=config.consentKey||'rollsbar_analytics_consent_v1';
	var initialized=false;

	if(!counterId)return;

	function readConsent(){
		try{return window.localStorage.getItem(consentKey)||'';}catch(e){return '';}
	}

	function saveConsent(value){
		try{window.localStorage.setItem(consentKey,value);}catch(e){}
	}

	function hideBanner(){
		var banner=document.querySelector('[data-rollsbar-cookie-consent]');
		if(banner)banner.hidden=true;
	}

	function showBanner(){
		var banner=document.querySelector('[data-rollsbar-cookie-consent]');
		if(banner)banner.hidden=false;
	}

	function ensureMetrika(){
		if(initialized)return true;
		if(readConsent()!=='allow')return false;

		(function(m,e,t,r,i,k,a){
			m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments);};
			m[i].l=1*new Date();
			k=e.createElement(t);a=e.getElementsByTagName(t)[0];
			k.async=1;k.src=r;a.parentNode.insertBefore(k,a);
		})(window,document,'script','https://mc.yandex.ru/metrika/tag.js','ym');

		window.ym(counterId,'init',config.init||{
			clickmap:false,
			trackLinks:false,
			accurateTrackBounce:true,
			webvisor:false,
			sendTitle:false
		});
		initialized=true;
		return true;
	}

	function reach(goalKey,params){
		var target=goals[goalKey]||goalKey;
		if(!target||!ensureMetrika()||typeof window.ym!=='function')return false;
		window.ym(counterId,'reachGoal',target,params||{});
		return true;
	}

	window.rollsBarReachGoal=reach;

	function bindConsent(){
		var state=readConsent();
		if(state==='allow'){
			hideBanner();
			ensureMetrika();
			return;
		}
		if(state==='deny'){
			hideBanner();
			return;
		}

		showBanner();
		var allow=document.querySelector('[data-rollsbar-analytics-allow]');
		var deny=document.querySelector('[data-rollsbar-analytics-deny]');
		if(allow)allow.addEventListener('click',function(){
			saveConsent('allow');
			hideBanner();
			ensureMetrika();
			firePageGoals();
		});
		if(deny)deny.addEventListener('click',function(){
			saveConsent('deny');
			hideBanner();
		});
	}

	function firePageGoals(){
		if(readConsent()!=='allow')return;
		if(context.isOrderReceived){
			reach('purchase',context.purchase||{});
			return;
		}
		if(context.isCart)reach('open_cart');
		if(context.isCheckout)reach('begin_checkout');
	}

	// WooCommerce's classic AJAX add-to-cart flow emits this jQuery event.
	if($&&$.fn){
		$(document.body).on('added_to_cart',function(){reach('add_to_cart');});
	}

	// Product pages can use a regular form submit instead of AJAX.
	document.addEventListener('submit',function(event){
		var form=event.target;
		if(form&&form.matches&&form.matches('form.cart'))reach('add_to_cart');
	},true);

	document.addEventListener('click',function(event){
		var target=event.target&&event.target.closest?event.target.closest('a,button,input'):null;
		if(!target)return;

		if(target.matches('a[href^="tel:"]')){
			reach('phone_click');
			return;
		}

		if(target.matches('.wc-block-components-checkout-place-order-button,#place_order')){
			reach('submit_order');
		}
	},true);

	document.addEventListener('change',function(event){
		var target=event.target;
		if(!target||!target.matches)return;
		if(
			target.matches('input[name^="shipping_method"],input[name*="shipping-option"],input[value*="local_pickup"],input[value*="flat_rate"]')
		){
			reach('shipping_method_select');
		}
	},true);

	function boot(){
		bindConsent();
		if(readConsent()==='allow')firePageGoals();
	}

	if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);
	else boot();
})(window.jQuery);
