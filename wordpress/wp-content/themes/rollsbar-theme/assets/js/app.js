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
	var selector=modal.querySelector('.rollsbar-product-options');
	var groups=selector.querySelector('.rollsbar-product-options__groups');
	var selection=null;
	var cartCounts={},cartBusy=false;
	var cartConfig=window.rollsbarCart;
	var cartStatus=document.createElement('div');
	cartStatus.className='rollsbar-cart-status';cartStatus.setAttribute('role','status');cartStatus.setAttribute('aria-live','polite');
	document.body.appendChild(cartStatus);
	function renderCartControls(){
		document.querySelectorAll('.rollsbar-product-card[data-rollsbar-source-id]').forEach(function(card){
			var id=card.dataset.rollsbarSourceId,product=products[id];
			if(!product)return;
			if(product.selection.required){card.querySelector('.rollsbar-product-action').classList.add('rollsbar-product-action--variable');return;}
			var old=card.querySelector('.rollsbar-product-control,.rollsbar-product-counter,.rollsbar-product-action');
			if(!old)return;
			var active=old.contains(document.activeElement),delta=active?document.activeElement.dataset.rollsbarCartDelta:null;
			var control=document.createElement('div'),qty=cartCounts[id]||0;
			control.className=qty?'rollsbar-product-counter':'rollsbar-product-control';
			function button(value,label,text){var b=document.createElement('button');b.type='button';b.dataset.rollsbarCartDelta=value;b.setAttribute('aria-label',label+': '+product.name);b.textContent=text;b.disabled=cartBusy||!cartConfig;return b;}
			if(qty){control.appendChild(button('-1','Уменьшить количество','−'));var count=document.createElement('span');count.textContent=qty;control.appendChild(count);control.appendChild(button('1','Добавить в корзину','+'));}
			else{var add=button('1','Добавить в корзину','');add.className='rollsbar-product-action rollsbar-product-action--variable';control.appendChild(add);}
			old.replaceWith(control);
			if(active){var next=control.querySelector('[data-rollsbar-cart-delta="'+delta+'"]')||control.querySelector('button');next.focus({preventScroll:true});}
		});
	}
	function applyCart(data){
		if(!data||!data.counts)throw Error('Не удалось получить состояние корзины.');
		cartCounts=data.counts;renderCartControls();
		if(window.jQuery&&data.fragments){
			Object.keys(data.fragments).forEach(function(key){window.jQuery(key).replaceWith(data.fragments[key]);});
			window.jQuery(document.body).trigger('wc_fragments_refreshed');
		}
	}
	async function cartRequest(request){
		if(!cartConfig)throw Error('Корзина временно недоступна.');
		var response=await fetch(cartConfig.url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({nonce:cartConfig.nonce,request:JSON.stringify(request)})});
		if(!response.ok)throw Error('Не удалось обновить корзину. Повторите попытку.');
		var result=await response.json();
		applyCart(result.data);
		if(!result.success)throw Error(result.data.message||'Не удалось обновить корзину.');
		return result.data;
	}
	function setCartBusy(value){
		cartBusy=value;
		document.querySelectorAll('[data-rollsbar-cart-delta]').forEach(function(button){button.disabled=value||!cartConfig;});
		if(selection)selector.querySelector('.rollsbar-product-options__add').disabled=value||!selection.valid||!cartConfig;
	}
	async function mutateCart(id,delta,chosen){
		if(cartBusy||!products[id])return false;
		var focused=document.activeElement,focusedCard=focused.hasAttribute('data-rollsbar-cart-delta')?focused.closest('[data-rollsbar-source-id]'):null;
		setCartBusy(true);cartStatus.textContent='';
		document.querySelectorAll('.rollsbar-cart-error').forEach(function(node){node.remove();});
		try{
			await cartRequest({operation:delta<0?'minus':'add',source_id:id,product_id:products[id].woo_id,variation_id:chosen?chosen.variation_id:0,options:chosen?chosen.options.map(function(option){return option.value;}):[]});
			cartStatus.textContent='Корзина обновлена.';return true;
		}catch(error){
			// A lost response may follow a successful server mutation. Reconcile without retrying the add.
			try{await cartRequest({operation:'read'});}catch(ignored){}
			var target=!modal.hidden?selector.hidden?modal.querySelector('.rollsbar-product-details__content'):selector:document.querySelector('[data-rollsbar-source-id="'+id+'"] .rollsbar-product-card__body');
			var note=document.createElement('div');note.className='rollsbar-cart-error';note.setAttribute('role','alert');note.textContent=error.message;target.appendChild(note);
			return false;
		}finally{
			setCartBusy(false);
			if(focusedCard&&(document.activeElement===document.body||document.activeElement===focused)){
				var next=focusedCard.querySelector('[data-rollsbar-cart-delta="'+focused.dataset.rollsbarCartDelta+'"]')||focusedCard.querySelector('[data-rollsbar-cart-delta]');
				if(next)next.focus({preventScroll:true});
			}
		}
	}
	renderCartControls();
	if(cartConfig){setCartBusy(true);cartRequest({operation:'read'}).catch(function(){cartStatus.textContent='Не удалось получить состояние корзины.';}).finally(function(){setCartBusy(false);});}
	document.addEventListener('click',function(event){
		var button=event.target.closest('[data-rollsbar-cart-delta]');
		if(!button)return;
		event.preventDefault();mutateCart(button.closest('[data-rollsbar-source-id]').dataset.rollsbarSourceId,Number(button.dataset.rollsbarCartDelta),null);
	});
	var opener=null,previousOverflow='',previousScrollBehavior='',scrollPosition=null,background=[];

	function publishSelection(product){
		var contract=product.selection;
		var select=groups.querySelector('[data-variation]');
		var variation=select?contract.variations.find(function(row){return String(row.id)===select.value&&row.available;}):null;
		var valid=!contract.blocked&&(!product.variable||!!variation);
		var options=contract.options.map(function(group,index){
			var control=groups.querySelector('[data-option="'+index+'"]');
			var value=control?control.value:null;
			if(group.pending||!group.choices.includes(value))valid=false;
			return {label:group.label,value:value};
		});
		selection={source_id:modal.dataset.sourceId,variation_id:variation?variation.id:null,attributes:variation?variation.attributes:{},options:options,price_html:variation?variation.price_html:product.price,valid:valid};
		modal.dataset.selection=JSON.stringify(selection);
		modal.dispatchEvent(new CustomEvent('rollsbar:selectionchange',{bubbles:true,detail:JSON.parse(modal.dataset.selection)}));
		var submit=selector.querySelector('.rollsbar-product-options__add');
		submit.disabled=!valid||cartBusy||!cartConfig;
		submit.textContent=contract.blocked||contract.options.some(function(group){return group.pending;})?'Ожидаем список вариантов':(valid?'Добавить в корзину':'Нет доступных вариантов');
	}
	function showSelector(product){
		modal.classList.add('selecting');
		selector.hidden=false;
		panel.setAttribute('aria-labelledby','rollsbarSelectionTitle');
		selector.querySelector('h3').textContent=product.name;
		groups.replaceChildren();
		function row(labelText,id){
			var wrap=document.createElement('div');wrap.className='rollsbar-product-options__group';
			var label=document.createElement('label');label.textContent=labelText;
			if(id)label.htmlFor=id;
			wrap.appendChild(label);groups.appendChild(wrap);return wrap;
		}
		if(product.variable){
			var wrap=row(product.selection.label,'rollsbarVariation');
			var select=document.createElement('select');select.id='rollsbarVariation';select.dataset.variation='';
			product.selection.variations.forEach(function(variation){
				var option=document.createElement('option');option.value=String(variation.id);
				option.textContent=variation.label+' — '+variation.price_label;
				option.disabled=!variation.available;select.appendChild(option);
			});
			var first=product.selection.variations.find(function(variation){return variation.available;});
			if(first)select.value=String(first.id);
			else{var empty=document.createElement('option');empty.value='';empty.textContent='Нет доступных вариантов';select.prepend(empty);select.value='';select.disabled=true;}
			wrap.appendChild(select);
		}
		product.selection.options.forEach(function(group,index){
			var id='rollsbarOption'+index,wrap=row(group.label,group.pending?null:id);
			if(group.pending){
				var note=document.createElement('div');note.className='rollsbar-product-options__note';
				note.textContent='Выбор должен быть в этой карточке, как просил заказчик, но точный список вариантов в переданной таблице не указан. Не подставляем соусы наугад.';
				wrap.appendChild(note);return;
			}
			var select=document.createElement('select');select.id=id;select.dataset.option=String(index);
			group.choices.forEach(function(choice){var option=document.createElement('option');option.value=choice;option.textContent=choice;select.appendChild(option);});
			wrap.appendChild(select);
		});
		if(product.selection.blocked){
			var note=document.createElement('p');note.className='rollsbar-product-options__note';note.textContent='Список вариантов пока недоступен.';groups.appendChild(note);
		}
		publishSelection(product);
		panel.scrollTop=0;
		selector.querySelector('[data-rollsbar-detail-close]').focus({preventScroll:true});
	}
	groups.addEventListener('change',function(){if(!modal.hidden&&modal.classList.contains('selecting'))publishSelection(products[modal.dataset.sourceId]);});
	selector.querySelector('.rollsbar-product-options__add').addEventListener('click',async function(){
		if(!selection||!selection.valid||this.disabled)return;
		var chosen=JSON.parse(JSON.stringify(selection));
		if(await mutateCart(chosen.source_id,1,chosen)){
			if(modal.dataset.sourceId===chosen.source_id)closeDetail();
		}
	});

	function closeDetail(){
		if(modal.hidden)return;
		modal.hidden=true;
		modal.classList.remove('open');
		delete modal.dataset.sourceId;
		delete modal.dataset.selection;
		selection=null;
		groups.replaceChildren();
		modal.querySelectorAll('.rollsbar-cart-error').forEach(function(node){node.remove();});
		document.body.style.overflow=previousOverflow;
		background.forEach(function(item){item.element.inert=item.inert;});
		background=[];
		if(opener&&opener.isConnected)opener.focus({preventScroll:true});
		window.scrollTo(scrollPosition.x,scrollPosition.y);
		document.documentElement.style.scrollBehavior=previousScrollBehavior;
		opener=null;
	}
	function openDetail(id,trigger,selecting){
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
		modal.classList.remove('selecting');
		selector.hidden=true;
		selection=null;
		delete modal.dataset.selection;
		panel.setAttribute('aria-labelledby','rollsbarDetailTitle');
		modal.querySelector('#rollsbarDetailTitle').textContent=product.name;
		modal.querySelector('.rollsbar-product-details__desc').textContent=product.description;
		modal.querySelector('.rollsbar-product-details__price').innerHTML=product.price;
		media.classList.remove('image-missing');
		media.innerHTML=product.media;
		bindProductImages(media);
		action.href=product.action_url;
		action.classList.remove('add_to_cart_button','ajax_add_to_cart');
		action.querySelector('span').textContent=product.selection.required?'Выбрать и добавить':'Добавить в корзину';
		action.removeAttribute('data-product_id');
		action.removeAttribute('data-quantity');
		if(!product.selection.required){action.dataset.product_id=product.woo_id;action.dataset.quantity='1';}
		modal.hidden=false;
		modal.classList.add('open');
		document.body.style.overflow='hidden';
		panel.scrollTop=0;
		close.focus({preventScroll:true});
		if(selecting&&product.selection.required)showSelector(product);
		window.scrollTo(scrollPosition.x,scrollPosition.y);
		return true;
	}
	modal.querySelectorAll('[data-rollsbar-detail-close]').forEach(function(button){button.addEventListener('click',closeDetail);});
	action.addEventListener('click',function(event){
		event.preventDefault();
		var product=products[modal.dataset.sourceId];
		if(product.selection.required){event.preventDefault();showSelector(product);return;}
		var id=modal.dataset.sourceId;
		mutateCart(id,1,null).then(function(success){if(success&&modal.dataset.sourceId===id)closeDetail();});
	});
	document.addEventListener('click',function(event){
		if(event.defaultPrevented||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
		var card=event.target.closest('.rollsbar-product-card[data-rollsbar-source-id]');
		if(!card)return;
		var choose=event.target.closest('[data-rollsbar-selection-open]');
		if(choose){if(openDetail(card.dataset.rollsbarSourceId,choose,true))event.preventDefault();return;}
		var link=event.target.closest('[data-rollsbar-detail-open]');
		if(!link&&event.target.closest('button,a,input,select,textarea,.qty,.client-action-wrap,.client-counter'))return;
		var trigger=link||card.querySelector('h3 [data-rollsbar-detail-open]');
		if(openDetail(card.dataset.rollsbarSourceId,trigger))event.preventDefault();
	});
	document.addEventListener('keydown',function(event){
		if(modal.hidden)return;
		if(event.key==='Escape'){event.preventDefault();closeDetail();}
		if(event.key==='Tab'){
			var focusable=Array.from(panel.querySelectorAll('button:not([disabled]),a[href],select:not([disabled]),[tabindex="0"]')).filter(function(element){return element.tabIndex>=0&&element.getClientRects().length;});
			var first=focusable[0],last=focusable[focusable.length-1];
			if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
			else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
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
