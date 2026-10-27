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
		$this->add_rate( array( 'id' => $this->id, 'label' => 'Доставка', 'cost' => 0, 'taxes' => false, 'package' => $package ) );
	}
}
