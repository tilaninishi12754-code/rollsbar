// Independent oracle: drive the immutable approved UI itself, not a copy of scoring.
export function exerciseSearch(body, queries) {
 const d=body.ownerDocument,input=d.querySelector('.product-search__input');
 return queries.map(query=>{
  input.value=query;input.dispatchEvent(new Event('input',{bubbles:true}));
  return {query,meta:d.querySelector('.product-search__meta').textContent,
   results:[...d.querySelectorAll('[data-search-product]')].map(b=>({id:b.dataset.searchProduct,name:b.querySelector('b').textContent,copy:b.querySelector('.search-result__copy span').textContent,price:b.querySelector('.search-result__price').textContent.replace(/\s+/g,' ').trim()}))};
 });
}
export function searchGeometry(body) {
 const d=body.ownerDocument,w=d.defaultView;
 const excess=n=>n&&n.getClientRects().length?Math.max(0,n.scrollWidth-n.clientWidth,n.getBoundingClientRect().right-w.innerWidth,-n.getBoundingClientRect().left):0;
 const rect=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
 return {page:Math.max(0,d.documentElement.scrollWidth-w.innerWidth),header:excess(d.querySelector('.topbar,.rollsbar-header')),
  search:excess(d.querySelector('.product-search')),panel:excess(d.querySelector('.product-search__panel')),results:excess(d.querySelector('.product-search__results')),
  box:rect(d.querySelector('.product-search__panel')),head:rect(d.querySelector('.product-search__head')),rows:[...d.querySelectorAll('.search-result')].map(rect)};
}
export function searchFallbackGeometry(body) {
 const d=body.ownerDocument;
 const dimensions=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
 return {media:dimensions(d.querySelector('.search-result__media')),fallback:dimensions(d.querySelector('.search-result__media .product-fallback,.search-result__media .rollsbar-product-fallback'))};
}
