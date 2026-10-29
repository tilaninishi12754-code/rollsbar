"""New fulfillment transport fixtures; official Woo JS owns all forms and submission."""
import copy
from native_fixture import NativeFixture

class DeliveryFixture(NativeFixture):
 def __init__(self,root,out,hydrate):
  self.modes={}
  super().__init__(root,out,hydrate)
 def cart(self,cookie):
  cart,headers=super().cart(cookie)
  for package in cart['shipping_rates']:
   pickup=package['shipping_rates'][0]
   delivery=copy.deepcopy(pickup);delivery.update(rate_id='rollsbar_delivery',method_id='rollsbar_delivery',name='Доставка',meta_data=[])
   package['shipping_rates']=[delivery,pickup]
   for rate in package['shipping_rates']:rate['selected']=rate['rate_id']==self.modes.get(cookie,'rollsbar_delivery')
  return cart,headers
 def html(self,cookie):
  # Projection of the PHP render_block_data filter for the captured native document.
  html=super().html(cookie)
  html=html.replace('window.rollsBarCheckoutConfig={','window.rollsBarCheckoutConfig={"mapUrl":"/wp-content/plugins/rollsbar-core/assets/delivery-map.html",')
  import re
  html=html.replace('data-block-name="woocommerce/checkout-shipping-method-block"','data-block-name="woocommerce/checkout-shipping-method-block" data-shipping-text="Доставка" data-local-pickup-text="Самовывоз" data-title="Способ получения"')
  return html
 def api(self,path,method,body,cookie):
  if path.split('?')[0]=='/wc/store/v1/cart/update-item':
   quantity=int(body['quantity']);assert 1<=quantity<=20
   snapshot,_=self.cart_read(cookie)
   old=next(x['quantity'] for x in snapshot['lines'] if x['key']==body['key'])
   for _ in range(abs(quantity-old)):self.cart_read(cookie,{'operation':'line_plus' if quantity>old else 'line_minus','key':body['key']})
   return self.cart(cookie)[0]
  if path.split('?')[0]=='/wc/store/v1/cart/select-shipping-rate':
   assert body['rate_id'] in ['rollsbar_delivery','pickup_location:0']
   self.modes[cookie]=body['rate_id'];return self.cart(cookie)[0]
  if path.split('?')[0]=='/rollsbar/v1/address-suggestions':
   return {'suggestions':[{'display':'г Симферополь, ул Гагарина, д 1','token':'fixture-exact'}]}
  if path.split('?')[0]=='/rollsbar/v1/address-resolve':
   return {'display':'г Симферополь, ул Гагарина, д 1','qc_geo':0,'lat':44.9,'lon':34.1,'precision':{'allow_auto_zone':True},'delivery':{'status':'resolved','minimum':1200,'message':'Бесплатная доставка при заказе от 1 200 ₽.'},'address_proof':'offline-server-proof'}
  return super().api(path,method,body,cookie)
