<?php
/** Read-only native Woo integration fixture. Never save/process an order or send mail. */
if ( ! defined( 'ABSPATH' ) ) { exit( 1 ); }
function rb_direct_assert( $condition, $label ) {
 if ( ! $condition ) { throw new RuntimeException( $label ); }
 echo 'PASS ' . $label . "\n";
}
rb_direct_assert( 'staging' === wp_get_environment_type() && 'https://staging.rollsbar.ru' === home_url(), 'staging only' );
rb_direct_assert( '11.1.2' === WC_VERSION, 'actual WooCommerce 11.1.2' );
$excluded=apply_filters('wp_speculation_rules_href_exclude_paths',array('/keep/*'),'prefetch');
rb_direct_assert(in_array('/checkout/*',$excluded,true)&&in_array('/cart/*',$excluded,true)&&in_array('/product/*',$excluded,true)&&in_array('/keep/*',$excluded,true)&&!in_array('/*',$excluded,true),'native speculation configuration excludes stateful Woo documents only');
if ( ! WC()->session ) { wc_load_cart(); }
$email = RollsBar_Checkout::internal_email();
rb_direct_assert( is_email( $email ) && str_ends_with( $email, '@checkout.rollsbar.invalid' ), 'native WP accepts reserved internal identity' );
$controller = new Automattic\WooCommerce\StoreApi\Utilities\OrderController();
$ref = new ReflectionClass( $controller );
$validate_email = $ref->getMethod( 'validate_email' );
$validate_address = $ref->getMethod( 'validate_address_fields' );
$order = new WC_Order();
foreach ( array( '', 'broken' ) as $invalid ) {
 $order->set_billing_email( '' );
 if ( $invalid ) {
  // WC_Order itself rejects invalid data; exercise the Store API empty case too.
  try { $order->set_billing_email( $invalid ); } catch ( WC_Data_Exception $e ) { echo "PASS native order setter rejects malformed email\n"; }
 }
 $failed = false;
 try { $validate_email->invoke( $controller, $order ); } catch ( Automattic\WooCommerce\StoreApi\Exceptions\RouteException $e ) { $failed = true; }
 rb_direct_assert( $failed, 'unmodified Store API rejects missing email' );
}
$order->set_billing_email( $email );
$validate_email->invoke( $controller, $order );
rb_direct_assert( 0 === $order->get_id(), 'email validation accepts unsaved native order; no order created' );
$address = array( 'country' => 'RU', 'first_name' => 'Тест', 'phone' => '+79780000000', 'address_1' => 'Кечкеметская улица, 1' );
$order->set_address( $address, 'billing' );
$errors = new WP_Error();
$validate_address->invoke( $controller, $order, 'billing', $errors );
rb_direct_assert( ! $errors->has_errors(), 'native address validation accepts approved fields with optional locality/surname/state/postcode absent' );
foreach ( array( 'phone' ) as $key ) {
 $test = $address; $test[$key] = ''; $order->set_address( $test, 'billing' ); $errors = new WP_Error();
 $validate_address->invoke( $controller, $order, 'billing', $errors );
 rb_direct_assert( $errors->has_errors(), 'native address validator requires ' . $key );
}
$order->set_address( array_merge( $address, array( 'address_1' => '' ) ), 'billing' );
$errors = new WP_Error();
$validate_address->invoke( $controller, $order, 'billing', $errors );
rb_direct_assert( ! $errors->has_errors(), 'pickup native billing contract permits absent customer address; delivery has separate pre-order proof validation' );
$field_service = Automattic\WooCommerce\Blocks\Package::container()->get( Automattic\WooCommerce\Blocks\Domain\Services\CheckoutFields::class );
$order_fields = array('rollsbar/privacy-consent'=>true,'rollsbar/entrance'=>'2','rollsbar/door-code'=>'10','rollsbar/floor'=>'3','rollsbar/apartment-office'=>'4');
rb_direct_assert( ! $field_service->validate_fields_for_location($order_fields,'order')->has_errors(), 'native Additional Checkout Fields validate approved values' );
$request = new WP_REST_Request( 'POST', '/wc/store/v1/checkout' );
$request->set_body_params( array( 'billing_address' => array_merge( array( 'last_name'=>'', 'company'=>'', 'address_2'=>'', 'city'=>'', 'state'=>'', 'postcode'=>'', 'email'=>'' ), $address ), 'payment_method'=>'cod', 'additional_fields'=>$order_fields, 'customer_note'=>'' ) );
$request->set_param( 'create_account', true );
RollsBar_Checkout::prepare_store_request( null, null, $request );
rb_direct_assert( false === $request->get_param('create_account') && $email === $request->get_param('billing_address')['email'], 'guest request adapter prevents account creation and hydrates email' );
rb_direct_assert( 'RU' === $request->get_param('billing_address')['country'] && 'RU' === $request->get_param('shipping_address')['country'], 'native hidden countries restored before schema validation' );
$server = rest_get_server();
$args = null; $native_route = null;
foreach ( $server->get_routes()['/wc/store/v1/checkout'] ?? array() as $endpoint ) {
 if ( is_array($endpoint) && ! empty($endpoint['methods']['POST']) ) { $args=$endpoint['args']; $native_route=$endpoint['callback'][0]; break; }
}
rb_direct_assert( is_array($args), 'installed Store API POST schema located without dispatching checkout' );
$request->set_attributes( array('args'=>$args) );
$valid = $request->has_valid_params();
rb_direct_assert( ! is_wp_error($valid), 'approved native payload passes actual WP REST / Store API request schema' . (is_wp_error($valid) ? ': '.$valid->get_error_message() : '') );
$sanitized = $request->sanitize_params();
rb_direct_assert( ! is_wp_error($sanitized) && $request->get_param('billing_address')['email']===$email, 'native request sanitization preserves compatibility identity' );
// validate_fields_for_location applies extension callbacks only. Woo enforces
// requiredness in the route's pure validate_callback before processing an order.
rb_direct_assert( $native_route instanceof Automattic\WooCommerce\StoreApi\Routes\V1\Checkout, 'actual installed checkout route validator located' );
rb_direct_assert( true === $native_route->validate_callback($request), 'native route accepts explicit consent without processing an order' );
$request->set_param('additional_fields',array('rollsbar/privacy-consent'=>false));
$without_consent=$native_route->validate_callback($request);
rb_direct_assert( is_wp_error($without_consent) && isset($without_consent->get_error_data()['details']['additional_fields']), 'native route rejects false required privacy consent' );
$request->set_param('additional_fields',$order_fields);
rb_direct_assert( false === apply_filters( 'woocommerce_checkout_registration_enabled', true ), 'native account creation UI disabled' );
rb_direct_assert( false === apply_filters( 'pre_wp_mail', null, array( 'to' => $email, 'headers' => array() ) ), 'mail to compatibility identity blocked before transport' );
rb_direct_assert( null === RollsBar_Checkout::block_internal_mail( null, array( 'to' => 'operator@example.org' ) ), 'operator mail path unchanged' );
$operator = apply_filters( 'wp_mail', array( 'to' => 'operator@example.org', 'headers' => "Reply-to: <$email>\r\nContent-Type: text/html", 'message' => "Contact: $email", 'subject' => 'In-memory fixture', 'attachments' => array() ) );
rb_direct_assert( null === RollsBar_Checkout::block_internal_mail( null, $operator ) && ! str_contains( $operator['message'], $email ), 'native mail filters remove technical Reply-To/contact without suppressing operator mail' );
$locations = get_option( 'pickup_location_pickup_locations' );
rb_direct_assert( 'Симферополь, Кечкеметская улица, 1' === $locations[0]['name'], 'native pickup exact address' );
RollsBar_Checkout::native_field_data();
$registry = Automattic\WooCommerce\Blocks\Package::container()->get( Automattic\WooCommerce\Blocks\Assets\AssetDataRegistry::class );
$data = (new ReflectionClass($registry))->getMethod('get')->invoke($registry);
rb_direct_assert( true === $data['defaultFields']['email']['hidden'], 'native email field configuration hidden before hydration' );
$order->set_address($address,'billing'); $order->set_total(420); $order->set_date_created('2026-10-27 12:00:00'); $order->set_payment_method_title('Оплата при получении');
$summary_ref=new ReflectionClass(Automattic\WooCommerce\Blocks\BlockTypes\OrderConfirmation\Summary::class);
$summary=$summary_ref->newInstanceWithoutConstructor();
$raw_summary=$summary_ref->getMethod('render_content')->invoke($summary,$order,true,array(),'');
rb_direct_assert( str_contains($raw_summary,$email), 'actual native confirmation would expose compatibility email before presentation filter' );
$safe_summary=apply_filters('render_block_woocommerce/order-confirmation-summary',$raw_summary);
rb_direct_assert( !str_contains($safe_summary,'@checkout.rollsbar.invalid') && str_contains($safe_summary,'420') && str_contains($safe_summary,'Оплата при получении'), 'actual native confirmation omits internal contact while retaining totals/payment' );
ob_start(); wc_get_template('order/order-details-customer.php',array('order'=>$order)); $safe_details=ob_get_clean();
rb_direct_assert( !str_contains($safe_details,'@checkout.rollsbar.invalid') && str_contains($safe_details,'+79780000000'), 'actual native customer-details template omits internal email and retains phone' );
$account_ref=new ReflectionClass(Automattic\WooCommerce\Blocks\BlockTypes\OrderConfirmation\CreateAccount::class);
rb_direct_assert( false === $account_ref->getMethod('is_feature_enabled')->invoke($account_ref->newInstanceWithoutConstructor()), 'native delayed account creation disabled, including default option' );
$validate_email->invoke($controller,$order);
rb_direct_assert( $email === $order->get_billing_email(), 'native order email data and validation untouched by display filters' );
rb_direct_assert( 0 === $order->get_id(), 'fixture never persisted an order' );
echo "DIRECT_PORT_NATIVE_INTEGRATION_PASS\n";
