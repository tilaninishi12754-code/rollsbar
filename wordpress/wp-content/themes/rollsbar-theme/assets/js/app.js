(function(){
	'use strict';
	function bindProductImages(root){root.querySelectorAll('[data-rollsbar-product-image]').forEach(function(image){
		function showFallback(){
			var media=image.closest('.rollsbar-product-media');
			if(!media)return;
			image.hidden=true;
			media.classList.add('image-missing');
		}
		image.addEventListener('error',showFallback,{once:true});
		if(image.complete&&!image.naturalWidth)showFallback();
	});}
	bindProductImages(document);

	var modal=document.getElementById('rollsbarProductDetails');
	var source=document.getElementById('rollsbarProductDetailsData');
	if(!modal||!source)return;
	var products;
	try{products=JSON.parse(source.textContent);}catch(error){return;}
	var panel=modal.querySelector('.rollsbar-product-details__panel');
	var media=modal.querySelector('.rollsbar-product-details__media');
	var action=modal.querySelector('.rollsbar-product-details__add');
	var close=modal.querySelector('.rollsbar-product-details__close');
	var opener=null,previousOverflow='',previousScrollBehavior='',scrollPosition=null,background=[];

	function closeDetail(){
		if(modal.hidden)return;
		modal.hidden=true;
		modal.classList.remove('open');
		delete modal.dataset.sourceId;
		document.body.style.overflow=previousOverflow;
		background.forEach(function(item){item.element.inert=item.inert;});
		background=[];
		if(opener&&opener.isConnected)opener.focus({preventScroll:true});
		window.scrollTo(scrollPosition.x,scrollPosition.y);
		document.documentElement.style.scrollBehavior=previousScrollBehavior;
		opener=null;
	}
	function openDetail(id,trigger){
		if(!Object.prototype.hasOwnProperty.call(products,id))return false;
		var product=products[id];
		if(modal.hidden){
			opener=trigger;
			previousOverflow=document.body.style.overflow;
			previousScrollBehavior=document.documentElement.style.scrollBehavior;
			scrollPosition={x:window.scrollX,y:window.scrollY};
			// Finish any in-flight smooth anchor/focus scrolling before locking the page.
			document.documentElement.style.scrollBehavior='auto';
			window.scrollTo(scrollPosition.x,scrollPosition.y);
			// Inert siblings along the ancestor chain; never inert the dialog itself.
			for(var branch=modal;branch.parentElement;branch=branch.parentElement){
				Array.from(branch.parentElement.children).forEach(function(element){
					if(element!==branch){background.push({element:element,inert:element.inert});element.inert=true;}
				});
				if(branch.parentElement===document.body)break;
			}
		}
		modal.dataset.sourceId=id;
		modal.querySelector('#rollsbarDetailTitle').textContent=product.name;
		modal.querySelector('.rollsbar-product-details__desc').textContent=product.description;
		modal.querySelector('.rollsbar-product-details__price').innerHTML=product.price;
		media.classList.remove('image-missing');
		media.innerHTML=product.media;
		bindProductImages(media);
		action.href=product.action_url;
		action.classList.toggle('add_to_cart_button',!product.variable);
		action.classList.toggle('ajax_add_to_cart',!product.variable);
		action.querySelector('span').textContent=product.variable?'Выбрать вариант':'Добавить в корзину';
		action.removeAttribute('data-product_id');
		action.removeAttribute('data-quantity');
		if(!product.variable){action.dataset.product_id=product.woo_id;action.dataset.quantity='1';}
		modal.hidden=false;
		modal.classList.add('open');
		document.body.style.overflow='hidden';
		panel.scrollTop=0;
		close.focus({preventScroll:true});
		window.scrollTo(scrollPosition.x,scrollPosition.y);
		return true;
	}
	modal.querySelectorAll('[data-rollsbar-detail-close]').forEach(function(button){button.addEventListener('click',closeDetail);});
	// Keep Woo's existing delegated add-to-cart handling and variable permalink.
	action.addEventListener('click',closeDetail);
	document.addEventListener('click',function(event){
		if(event.defaultPrevented||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
		var card=event.target.closest('.rollsbar-product-card[data-rollsbar-source-id]');
		if(!card)return;
		var link=event.target.closest('[data-rollsbar-detail-open]');
		if(!link&&event.target.closest('button,a,input,select,textarea,.qty,.client-action-wrap,.client-counter'))return;
		var trigger=link||card.querySelector('h3 [data-rollsbar-detail-open]');
		if(openDetail(card.dataset.rollsbarSourceId,trigger))event.preventDefault();
	});
	document.addEventListener('keydown',function(event){
		if(modal.hidden)return;
		if(event.key==='Escape'){event.preventDefault();closeDetail();}
		if(event.key==='Tab'){
			if(event.shiftKey&&document.activeElement===close){event.preventDefault();action.focus();}
			else if(!event.shiftKey&&document.activeElement===action){event.preventDefault();close.focus();}
		}
	});
})();

(function(){
	'use strict';

	var body=document.body;
	var search=document.getElementById('rollsbarProductSearch');
	var open=document.querySelector('[data-rollsbar-search-open]');

	function closeSearch(){
		if(!search||!open||!search.classList.contains('open'))return;
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

// Homepage category navigation and approved desktop "More" menu.
(function(){
	'use strict';
	var nav=document.querySelector('.rollsbar-category-nav');
	if(!nav)return;
	var toggle=nav.querySelector('[data-rollsbar-category-more]');
	var menu=document.getElementById('rollsbarCategoryMore');
	function closeMore(){
		if(!toggle||!menu)return;
		menu.classList.remove('open');
		menu.setAttribute('aria-hidden','true');
		toggle.setAttribute('aria-expanded','false');
	}
	if(toggle&&menu){
		toggle.addEventListener('click',function(event){
			event.stopPropagation();
			var opening=!menu.classList.contains('open');
			closeMore();
			if(opening){menu.classList.add('open');menu.setAttribute('aria-hidden','false');toggle.setAttribute('aria-expanded','true');}
		});
		menu.addEventListener('click',function(event){
			var link=event.target.closest('a');
			if(!link)return;
			closeMore();
			if(link.hasAttribute('data-rollsbar-category-contacts')){
				event.preventDefault();
				var contacts=document.querySelector('.rollsbar-footer');
				if(contacts)contacts.scrollIntoView();
			}
		});
		document.addEventListener('click',function(event){if(!menu.contains(event.target)&&!toggle.contains(event.target))closeMore();});
		document.addEventListener('keydown',function(event){if(event.key==='Escape')closeMore();});
	}
	var links=Array.from(nav.querySelectorAll('a[href^="#"]'));
	var sections=links.map(function(link){return document.getElementById(link.getAttribute('href').slice(1));}).filter(Boolean);
	if(!('IntersectionObserver' in window))return;
	var observer=new IntersectionObserver(function(entries){
		var visible=entries.filter(function(entry){return entry.isIntersecting;}).sort(function(a,b){return b.intersectionRatio-a.intersectionRatio;})[0];
		if(!visible)return;
		links.forEach(function(link){link.classList.toggle('active',link.getAttribute('href')==='#'+visible.target.id);});
	},{rootMargin:'-136px 0px -64% 0px',threshold:[0,.2,.55]});
	sections.forEach(function(section){observer.observe(section);});
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
