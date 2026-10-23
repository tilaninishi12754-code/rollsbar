// B6B: measure the real approved/current DOM; all positions are component-local.
export function cardGeometry(body) {
 const d=body.ownerDocument,w=d.defaultView,a=!!d.querySelector('.product-card');
 const round=x=>Math.round(x*100)/100;
 return [...d.querySelectorAll(a?'.product-card':'.rollsbar-product-card')].map(c=>{
  const footer=c.querySelector(a?'.product-card__footer':'.rollsbar-product-card__footer');
  const price=footer.querySelector(a?'.price':'.rollsbar-price');
  const control=footer.lastElementChild;
  const action=control.matches('a,button,.rollsbar-product-counter')?control:control.querySelector(a?'.client-counter,button':'button')||control;
  const cr=c.getBoundingClientRect(),fr=footer.getBoundingClientRect();
  const box=(n,origin)=>{const r=n.getBoundingClientRect();return {x:round(r.x-origin.x),y:round(r.y-origin.y),width:round(r.width),height:round(r.height)};};
  const pr=price.getBoundingClientRect(),ar=action.getBoundingClientRect();
  const range=d.createRange();range.selectNodeContents(price);const ink=range.getBoundingClientRect();
  const inkOverlap=round(Math.max(0,Math.min(ink.right,ar.right)-Math.max(ink.left,ar.left))*Math.max(0,Math.min(ink.bottom,ar.bottom)-Math.max(ink.top,ar.top)));
  const s=w.getComputedStyle(footer);
  return {id:a?c.querySelector('[data-original-add]')?.dataset.originalAdd:c.dataset.rollsbarSourceId,
   section:c.closest('section')?.id,accent:c.className.includes('accent'),card:{width:round(cr.width),height:round(cr.height)},
   footer:box(footer,cr),price:box(price,fr),action:box(action,fr),bottom:round(cr.bottom-fr.bottom),gap:s.gap,
   separation:round(ar.left-pr.right),inkOverlap,overlap:round(Math.max(0,Math.min(pr.right,ar.right)-Math.max(pr.left,ar.left))*Math.max(0,Math.min(pr.bottom,ar.bottom)-Math.max(pr.top,ar.top))),
   overflow:round(Math.max(0,fr.right-cr.right,cr.left-fr.left,ar.right-cr.right,cr.left-ar.left,ar.bottom-cr.bottom)),
   clipping:round(Math.max(0,ar.bottom-fr.bottom,fr.top-ar.top)),
   priceText:price.textContent.replace(/\s+/g,' ').trim()};
 });
}
