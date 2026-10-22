// Relative B15 geometry permits the intentionally deferred delivery section above it.
export function footerGeometry(body){
 const d=body.ownerDocument,w=d.defaultView,approved=!!d.querySelector('.footer');
 const footer=d.querySelector(approved?'.footer':'.rollsbar-footer'),contacts=d.querySelector('#contacts');
 const round=x=>Math.round(x*100)/100;
 const geometry=(root,selectors)=>{
  const origin=root.getBoundingClientRect();
  return [root,...selectors.flatMap(s=>[...root.querySelectorAll(s)])].map(n=>{
   const r=n.getBoundingClientRect(),s=w.getComputedStyle(n);
   return {x:round(r.x-origin.x),y:round(r.y-origin.y),width:round(r.width),height:round(r.height),font:s.fontSize,line:s.lineHeight,color:s.color,background:s.backgroundColor,border:s.border,borderRadius:s.borderRadius,padding:s.padding,gap:s.gap,shadow:s.boxShadow};
  });
 };
 return {footer:geometry(footer,[approved?'.shell':'.rollsbar-footer__grid',approved?'.brand':'.rollsbar-footer__logo','img','p',approved?'.footer-links':'.rollsbar-footer__links',approved?'.footer-links a':'.rollsbar-footer__links a']),contacts:geometry(contacts,[approved?'.section-heading':'.rollsbar-contacts__heading','h2',approved?'.content-grid':'.rollsbar-contacts__grid','article','h3','p','a']),gap:round(footer.getBoundingClientRect().top-contacts.getBoundingClientRect().bottom)};
}
export function footerOverflow(body){
 const d=body.ownerDocument,w=d.defaultView;
 const excess=n=>n&&n.getClientRects().length?Math.max(0,n.scrollWidth-n.clientWidth,n.getBoundingClientRect().right-w.innerWidth,-n.getBoundingClientRect().left):0;
 const footer=d.querySelector('.rollsbar-footer');
 const content=Math.max(0,...[...d.querySelectorAll('.rollsbar-footer a,.rollsbar-footer p,#contacts article,#contacts a')].map(excess));
 return {page:Math.max(0,d.documentElement.scrollWidth-w.innerWidth),footer:excess(footer),content,header:excess(d.querySelector('.rollsbar-header')),search:excess(d.querySelector('.product-search')),mobile:excess(d.querySelector('[data-rollsbar-orderbar]'))};
}
