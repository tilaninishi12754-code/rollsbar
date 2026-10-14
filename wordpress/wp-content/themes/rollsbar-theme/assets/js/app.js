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

// Homepage header menu. Preserve the existing search/cart handlers and scroll state.
(function(){
	'use strict';
	var menu=document.getElementById('rollsbarSiteMenu');
	var toggle=document.querySelector('[data-rollsbar-menu-open]');
	if(!menu||!toggle)return;
	var previousOverflow='';
	function closeMenu(){
		if(!menu.classList.contains('open'))return;
		menu.classList.remove('open');
		menu.setAttribute('aria-hidden','true');
		toggle.setAttribute('aria-expanded','false');
		document.body.style.overflow=previousOverflow;
		toggle.focus();
	}
	toggle.addEventListener('click',function(){
		previousOverflow=document.body.style.overflow;
		menu.classList.add('open');
		menu.setAttribute('aria-hidden','false');
		toggle.setAttribute('aria-expanded','true');
		document.body.style.overflow='hidden';
		menu.querySelector('.rollsbar-site-menu__close').focus();
	});
	menu.querySelectorAll('[data-rollsbar-menu-close],.rollsbar-site-menu__links a,.rollsbar-site-menu__phone').forEach(function(link){
		link.addEventListener('click',function(event){
			closeMenu();
			// Contact details already live in the footer; do not change that component.
			if(link.hasAttribute('data-rollsbar-menu-contacts')){
				event.preventDefault();
				var contacts=document.querySelector('.rollsbar-footer');
				if(contacts)contacts.scrollIntoView();
			}
		});
	});
	document.addEventListener('keydown',function(event){
		if(!menu.classList.contains('open'))return;
		if(event.key==='Escape'){event.preventDefault();closeMenu();}
		if(event.key==='Tab'){
			var controls=menu.querySelectorAll('.rollsbar-site-menu__panel a,.rollsbar-site-menu__panel button');
			var first=controls[0],last=controls[controls.length-1];
			if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
			else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
		}
	});
})();

// Careers: fixed layout, editable vacancy content.
(function(){
	var tabs=document.querySelector('[data-rb-vacancy-tabs]');
	if(tabs){
		tabs.addEventListener('click',function(e){
			var button=e.target.closest('button[data-area]');
			if(!button)return;
			var area=button.getAttribute('data-area');
			tabs.querySelectorAll('button[data-area]').forEach(function(btn){
				btn.classList.toggle('active',btn===button);
			});
			document.querySelectorAll('[data-vacancy-area]').forEach(function(card){
				card.hidden=area!=='all'&&card.getAttribute('data-vacancy-area')!==area;
			});
		});
	}

	var modal=document.querySelector('[data-rb-career-chat-modal]');
	var open=document.querySelector('[data-rb-career-chat]');
	function openChat(){
		if(!modal)return;
		modal.classList.add('open');
		modal.setAttribute('aria-hidden','false');
		document.body.style.overflow='hidden';
	}
	function closeChat(){
		if(!modal)return;
		modal.classList.remove('open');
		modal.setAttribute('aria-hidden','true');
		document.body.style.overflow='';
	}
	if(open)open.addEventListener('click',openChat);
	if(modal){
		modal.querySelectorAll('[data-rb-career-chat-close]').forEach(function(btn){
			btn.addEventListener('click',closeChat);
		});
	}
	document.addEventListener('keydown',function(e){
		if(e.key==='Escape')closeChat();
	});
})();
