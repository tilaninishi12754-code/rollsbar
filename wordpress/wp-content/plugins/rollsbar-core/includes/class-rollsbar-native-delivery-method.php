<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

/** One Woo shipping method; the minimum is enforced before native submission. */
final class RollsBar_Native_Delivery_Method extends WC_Shipping_Method {
	public function __construct() {
		$this->id = 'rollsbar_delivery';
		$this->method_title = 'Rolls Bar — доставка';
		$this->title = 'Доставка';
		$this->enabled = 'yes';
		$this->tax_status = 'none';
		$this->supports = array();
	}
	public function calculate_shipping( $package = array() ) {
		$address = WC()->customer ? WC()->customer->get_shipping_address_1() : '';
		$proof = WC()->session ? (string) WC()->session->get( 'rollsbar_delivery_address_proof', '' ) : '';
		$decision = RollsBar_Delivery_Minimum::verify( $proof, $address, (float) WC()->cart->get_cart_contents_total() );
		$label = 'Доставка — условия уточнит менеджер';
		if ( 'resolved' === $decision['status'] ) { $label = 'Бесплатная доставка'; }
		elseif ( 'below_minimum' === $decision['status'] ) { $label = 'Доставка от ' . number_format( $decision['minimum'], 0, '.', ' ' ) . ' ₽'; }
		$this->add_rate( array( 'id' => $this->id, 'label' => $label, 'cost' => 0, 'taxes' => false, 'package' => $package ) );
	}
}
