<?php
/** Read-only live proof consumed by the staging media release and browser gate. */
$plan = RollsBar_Client_Media::plan();
$assets = array(); $products = array();
foreach ( $plan['assets'] as $key => $asset ) {
	$id = $plan['attachments'][ $key ];
	if ( ! $id || ! wp_get_attachment_metadata( $id ) ) { throw new RuntimeException( 'Missing imported media/metadata: ' . $key ); }
	$assets[] = array( 'key' => $key, 'attachment_id' => $id, 'sha256' => $asset['derived_sha256'], 'mime' => $asset['derived_mime'],
		'url' => wp_get_attachment_image_url( $id, 'full' ), 'display_url' => wp_get_attachment_image_url( $id, 'large' ), 'source_ids' => $asset['source_ids'] );
}
foreach ( $plan['products'] as $source => $key ) {
	$p = $plan['woo_products'][ $source ]; $id = $plan['attachments'][ $key ];
	$image = rollsbar_resolve_product_image( $p );
	if ( (int) $p->get_image_id() !== $id || (int) RollsBar_Client_Media::attachment_for( $p ) !== $id || $image['attachment_id'] !== $id || $image['source'] !== 'client-canon' ) {
		throw new RuntimeException( 'Wrong canonical featured/render identity: ' . $source );
	}
	$products[] = array( 'source_id' => $source, 'woo_id' => $p->get_id(), 'name' => $p->get_name(), 'media_key' => $key, 'attachment_id' => $id, 'display_url' => $image['url'] );
}
echo wp_json_encode( array( 'status' => 'PASS', 'counts' => $plan['counts'], 'assets' => $assets, 'products' => $products ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
