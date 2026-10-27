"""Offline native Blocks transport. Test fixtures only; never contacts staging.

The accepted PHP cart fixture remains the cart authority. Store API responses are
schema projections of that fixture, not another cart. Production has no such adapter.
"""
import copy,json,mimetypes,re,subprocess,urllib.request,urllib.parse
from pathlib import Path

class NativeFixture:
 def __init__(self,root,out,hydrate):
  self.root=root;self.out=out;self.hydrate=hydrate;self.customers={};self.unhandled=[]
  self.node=subprocess.Popen(['node','qa/checkout/native_fixture_server.mjs','4197'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
  self.server=json.loads(self.node.stdout.readline());self.origin='http://127.0.0.1:4197'
  self.home=self.node_call('/')[0].decode('utf8').replace('http://localhost','https://staging.rollsbar.ru').replace('url:"/fixture-cart"','url:"/?wc-ajax=rollsbar_cart"')
  match=re.search(r'<script[^>]+id="rollsbarProductDetailsData"[^>]*>(.*?)</script>',self.home,re.S)
  self.products=json.loads(match[1]);self.template=(out/'initial.html').read_text(encoding='utf8')
  match=re.search(r"var wcSettings = JSON.parse\( decodeURIComponent\( '([^']+)' \) \);",self.template)
  self.settings=json.loads(urllib.parse.unquote(match[1]));self.prototype=copy.deepcopy(self.settings['checkoutData']['__experimentalCart'])
  self.item=copy.deepcopy(self.prototype['items'][0]);self.nonce='local-fixture'
  if not (root/'qa/.runtime/wp-7.1.3/wordpress/wp-includes/js/dist/api-fetch.min.js').exists():raise RuntimeError('Official WordPress 7.1.3 runtime assets required')
 def close(self):
  if self.node.poll() is None:
   self.node.stdin.write('stop\n');self.node.stdin.flush();self.node.wait(timeout=10)
 def node_call(self,path,body=None,cookie=''):
  req=urllib.request.Request(self.origin+path,data=body,headers={'Cookie':cookie,'Content-Type':'application/x-www-form-urlencoded'})
  with urllib.request.urlopen(req,timeout=10) as response:return response.read(),dict(response.headers)
 def cart_read(self,cookie,operation=None):
  body=urllib.parse.urlencode({'nonce':self.nonce,'request':json.dumps(operation or {'operation':'read'})}).encode()
  raw,headers=self.node_call('/fixture-cart',body,cookie);data=json.loads(raw)
  if not data['success']:raise RuntimeError('Native PHP fixture refused operation')
  return data['data'],headers
 def customer(self,cookie):
  key=cookie.split('rollsbar_fixture=')[-1].split(';')[0]
  address={'first_name':'','last_name':'','company':'','address_1':'','address_2':'','city':'','state':'','postcode':'','country':'RU','phone':''}
  return self.customers.setdefault(key,{'billing_address':dict(address,email='guest-shadow@checkout.rollsbar.invalid'),'shipping_address':dict(address),'additional_fields':{},'customer_note':''})
 def cart(self,cookie):
  snapshot,headers=self.cart_read(cookie);cart=copy.deepcopy(self.prototype);cart['items']=[];total=0
  for line in snapshot['lines']:
   item=copy.deepcopy(self.item);product=self.products[line['source_id']];minor=cart['totals']['currency_minor_unit']
   price=round(float(re.sub(r'[^0-9,.]','',line['unit_price']).replace(',','.'))*10**minor);subtotal=price*line['quantity'];total+=subtotal
   item.update(id=product['woo_id'],key=line['key'],name=product['name'],quantity=line['quantity'])
   item['prices'].update(price=str(price),regular_price=str(price),sale_price=str(price))
   raw=str(price*10**(item['prices']['raw_prices']['precision']-minor))
   item['prices']['raw_prices'].update(price=raw,regular_price=raw,sale_price=raw)
   for key in ['line_subtotal','line_total']:item['totals'][key]=str(subtotal)
   image=re.search(r'src="([^"]+)"',line.get('media',''))
   if image:
    for asset in item['images']:asset['src']=asset['thumbnail']=image[1]
   cart['items'].append(item)
  cart['items_count']=sum(i['quantity'] for i in cart['items']);cart['totals']['total_items']=cart['totals']['total_price']=str(total)
  cart.update(copy.deepcopy(self.customer(cookie)))
  return self.hydrate(cart),headers
 def checkout(self,cookie):
  data=copy.deepcopy(self.settings['checkoutData']);data.update(copy.deepcopy(self.customer(cookie)));data['__experimentalCart']=self.cart(cookie)[0];return self.hydrate(data)
 def api(self,path,method,body,cookie):
  clean=urllib.parse.urlsplit(path).path
  if clean=='/wc/store/v1/batch':
   responses=[]
   for entry in body['requests']:
    data=self.api(entry['path'],entry.get('method','GET'),entry.get('body') or {},cookie)
    responses.append({'status':200,'headers':{'Nonce':self.nonce},'body':data})
   return {'responses':responses}
  if clean=='/wc/store/v1/cart/update-customer':
   customer=self.customer(cookie)
   for key in ['billing_address','shipping_address']:
    if key in body:customer[key].update(body[key])
   return self.cart(cookie)[0]
  if clean=='/wc/store/v1/cart/remove-item':
   self.cart_read(cookie,{'operation':'line_remove','key':body['key']});return self.cart(cookie)[0]
  if clean=='/wc/store/v1/cart':return self.cart(cookie)[0]
  if clean=='/wc/store/v1/cart/select-shipping-rate':
   cart=self.cart(cookie)[0]
   packages=[p for p in cart['shipping_rates'] if body.get('package_id') is None or p['package_id']==body['package_id']]
   if not packages or not all(any(r['rate_id']==body['rate_id'] and r['selected'] for r in p['shipping_rates']) for p in packages):
    raise RuntimeError('Fixture supports only the captured native pickup rate')
   return cart
  if clean=='/wc/store/v1/checkout':
   if method=='POST':raise RuntimeError('Checkout POST forbidden even in fixture')
   customer=self.customer(cookie)
   for key in ['billing_address','shipping_address','additional_fields']:
    if key in body:customer[key].update(body[key])
   if 'customer_note' in body:customer['customer_note']=body['customer_note']
   return self.checkout(cookie)
  if clean=='/rollsbar/v1/address-suggestions':
   query=urllib.parse.parse_qs(urllib.parse.urlsplit(path).query).get('query',[''])[0];exact='Кечкеметская' in query
   return {'suggestions':[{'display':'г Симферополь, ул Кечкеметская, д 1' if exact else 'г Симферополь, ул Киевская','token':'fixture-exact' if exact else 'fixture-low'}]}
  if clean=='/rollsbar/v1/address-resolve':
   exact=body['token']=='fixture-exact'
   return {'display':'г Симферополь, ул Кечкеметская, д 1' if exact else 'г Симферополь, ул Киевская','qc_geo':0 if exact else 2,'lat':44.973625,'lon':34.099205,'precision':{'allow_auto_zone':exact}}
  raise RuntimeError('Unhandled native fixture endpoint: '+path)
 def html(self,cookie):
  settings=self.hydrate(copy.deepcopy(self.settings));settings['checkoutData']=self.checkout(cookie)
  pattern=r"var wcSettings = JSON.parse\( decodeURIComponent\( '([^']+)' \) \);";match=re.search(pattern,self.template)
  html=self.template[:match.start(1)]+urllib.parse.quote(json.dumps(settings,ensure_ascii=False),safe='')+self.template[match.end(1):]
  preload=re.search(r"createPreloadingMiddleware\( JSON.parse\( decodeURIComponent\( '([^']+)'",html)
  if not preload:raise RuntimeError('Captured native Store API preload required')
  data=json.loads(urllib.parse.unquote(preload[1]))
  for path,response in data.items():
   if path=='/wc/store/v1/cart':response['body']=self.cart(cookie)[0]
   elif path=='/wc/store/v1/checkout':response['body']=self.checkout(cookie)
   else:raise RuntimeError('Unhandled captured preload: '+path)
  html=html[:preload.start(1)]+urllib.parse.quote(json.dumps(data,ensure_ascii=False),safe='')+html[preload.end(1):]
  html=html.replace('window.rollsBarCheckoutConfig={','window.rollsBarCheckoutConfig={"internalEmail":"guest-shadow@checkout.rollsbar.invalid",')
  return re.sub(r'<script type="speculationrules">.*?</script>','',html,flags=re.S)
 def route(self,route):
  req=route.request;url=urllib.parse.urlsplit(req.url);path=url.path;cookie=req.all_headers().get('cookie','');headers={}
  try:
   if path=='/' and urllib.parse.parse_qs(url.query).get('wc-ajax')==['rollsbar_cart']:
    content,headers=self.node_call('/fixture-cart',req.post_data.encode(),cookie);mime='application/json'
   elif path=='/':
    content=self.home.replace('</body>','<script>'+(self.out/'return-ui.js').read_text(encoding='utf8')+'</script></body>').encode();mime='text/html;charset=utf-8'
   elif path=='/fixture-cart':
    content,headers=self.node_call(path,req.post_data.encode(),cookie);mime='application/json'
   elif path=='/checkout/':content=self.html(cookie).encode();mime='text/html;charset=utf-8'
   elif path.startswith('/wp-json/'):
    data=json.loads(req.post_data or '{}');method=req.all_headers().get('x-http-method-override',req.method).upper();content=json.dumps(self.api(path.removeprefix('/wp-json')+('?' + url.query if url.query else ''),method,data,cookie),ensure_ascii=False).encode();mime='application/json';headers={'Nonce':self.nonce}
   else:
    if path.startswith('/wp-includes/'):file=self.root/'qa/.runtime/wp-7.1.3/wordpress'/path.lstrip('/')
    elif path.startswith('/wp-content/uploads/'):file=self.root/'qa/.runtime/native-media'/path.lstrip('/')
    elif path.startswith('/wp-content/plugins/woocommerce/'):file=self.root/'qa/.runtime/woo-11.1.2/woocommerce'/path.removeprefix('/wp-content/plugins/woocommerce/')
    elif path.startswith('/wp-content/'):file=self.root/'wordpress'/path.lstrip('/')
    else:file=self.root/path.lstrip('/')
    if file.exists() and file.is_file():content=file.read_bytes();mime=mimetypes.guess_type(file)[0] or 'application/octet-stream'
    else:
     content,headers=self.node_call(path,cookie=cookie);mime=headers.get('content-type','application/octet-stream')
   headers={k:v for k,v in headers.items() if k.lower() in ['set-cookie','nonce']}
   route.fulfill(status=200,body=content,headers=headers,content_type=mime)
  except Exception as error:
   detail={'path':path,'error':repr(error),'body':req.post_data};print('FIXTURE_ERROR',detail,flush=True)
   self.unhandled.append(detail);route.fulfill(status=500,json={'code':'fixture_error','message':str(error)})

