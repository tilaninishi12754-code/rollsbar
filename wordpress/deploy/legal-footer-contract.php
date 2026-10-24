<?php
/** Rendered B15 legal navigation contract; no network or source-code matching. */
function rollsbar_verify_legal_footer( string $html ): void {
	if ( ! class_exists( 'DOMDocument' ) ) {
		throw new RuntimeException( 'DOM extension is required for legal footer verification.' );
	}
	$previous = libxml_use_internal_errors( true );
	try {
		$document = new DOMDocument();
		$document->loadHTML( '<?xml encoding="UTF-8">' . $html, LIBXML_NONET );
	} finally {
		libxml_clear_errors();
		libxml_use_internal_errors( $previous );
	}
	$xpath = new DOMXPath( $document );
	$anchors = $xpath->query( '//footer[contains(concat(" ", normalize-space(@class), " "), " rollsbar-footer ")]//nav//a[@href]' );
	$destinations = array();
	foreach ( $anchors as $anchor ) {
		$href = $anchor->getAttribute( 'href' );
		if ( preg_match( '/\.html(?:[?#]|$)/i', $href ) ) {
			throw new RuntimeException( 'Static .html link leaked into WordPress footer.' );
		}
		if ( '' !== trim( $anchor->textContent ) ) {
			$destinations[] = $href;
		}
	}
	foreach ( array( 'dostavka-i-oplata', 'rekvizity-prodavca', 'publichnaya-oferta', 'oplata-i-vozvrat', 'politika-konfidencialnosti', 'cookies', 'bezopasnost-onlajn-oplaty' ) as $slug ) {
		if ( ! in_array( home_url( '/' . $slug . '/' ), $destinations, true ) ) {
			throw new RuntimeException( "Footer is missing legal link: /{$slug}/" );
		}
	}
}
