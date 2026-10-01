(function(){
	'use strict';

	var body=document.body;
	var search=document.getElementById('rollsbarProductSearch');
	var open=document.querySelector('[data-rollsbar-search-open]');

	function closeSearch(){
		if(!search||!open)return;
		search.classList.remove('open');
		search.setAttribute('aria-hidden','true');
		open.setAttribute('aria-expanded','false');
		body.style.overflow='';
	}

	function openSearch(){
		if(!search||!open)return;
		search.classList.add('open');
		search.setAttribute('aria-hidden','false');
		open.setAttribute('aria-expanded','true');
		body.style.overflow='hidden';
		var input=document.getElementById('rollsbarSearchInput');
		if(input)setTimeout(function(){input.focus();},50);
	}

	if(open)open.addEventListener('click',openSearch);
	document.querySelectorAll('[data-rollsbar-search-close]').forEach(function(el){
		el.addEventListener('click',closeSearch);
	});
	document.addEventListener('keydown',function(e){
		if(e.key==='Escape')closeSearch();
	});

	function syncMobileCart(){
		var mobile=document.querySelector('[data-rollsbar-mobile-cart]');
		var count=document.querySelector('.rollsbar-cart-count');
		if(!mobile||!count)return;
		var n=parseInt(count.textContent||'0',10)||0;
		mobile.hidden=n<1;
	}

	document.body.addEventListener('added_to_cart',syncMobileCart);
	document.body.addEventListener('removed_from_cart',syncMobileCart);
	document.body.addEventListener('wc_fragments_refreshed',syncMobileCart);
	syncMobileCart();
})();