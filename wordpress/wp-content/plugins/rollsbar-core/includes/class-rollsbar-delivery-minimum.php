<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

/** Exact workbook identities first; owner-authorized advisory geography second. */
final class RollsBar_Delivery_Minimum {
	public static function rules(): array {
		static $rules;
		if ( null === $rules ) {
			$rules = json_decode( file_get_contents( dirname( __DIR__ ) . '/data/delivery-minimum.json' ), true, 512, JSON_THROW_ON_ERROR );
		}
		return $rules['rules'];
	}

	public static function normalize( string $value ): string {
		return trim( preg_replace( '/[\s.\-]+/u', ' ', str_replace( 'ё', 'е', mb_strtolower( $value, 'UTF-8' ) ) ) );
	}

	public static function classify( array $data ): array {
		$unknown = array( 'status' => 'unresolved', 'minimum' => null, 'message' => 'Для этого адреса условия доставки пока не определены. Уточните доставку по телефону: +7 978 688-22-88.' );
		if ( empty( $data['house'] ) || empty( $data['house_fias_id'] ) ) {
			$unknown['message'] = 'Выберите точный адрес с номером дома из подсказок.';
			return $unknown;
		}
		// Scope every same-named street/locality to the provider's administrative identity.
		$city = self::normalize( (string) ( $data['city'] ?? '' ) );
		$area = self::normalize( (string) ( $data['area'] ?? '' ) );
		$region = self::normalize( (string) ( $data['region'] ?? '' ) );
		$approved_border_village = 'бахчисарайский' === $area && 'приятное свидание' === self::normalize( (string) ( $data['settlement'] ?? '' ) );
		if ( 'крым' !== $region || ( 'симферополь' !== $city && 'симферопольский' !== $area && ! $approved_border_village ) ) { return $unknown; }
		$street = self::normalize( (string) ( $data['street'] ?? '' ) );
		if ( 'симферополь' === $city && in_array( $street, array( 'кечкеметская', 'беспалова' ), true ) ) {
			$unknown['status'] = 'ambiguous';
			$unknown['message'] = 'Для этого участка улицы условия доставки требуют уточнения. Позвоните: +7 978 688-22-88.';
			return self::geographic( $data, $unknown );
		}
		$matches = array();
		foreach ( self::rules() as $rule ) {
			// These are whole-identity rules with a verified FIAS house. Coordinates
			// never determine a minimum, split a street, or imply polygon membership.
			// The independent geocode policy retains the original qc_geo restrictions.
			if ( ! empty( $data['planning_structure_fias_id'] ) && in_array( self::normalize( (string) ( $data['planning_structure'] ?? '' ) ), array_map( array( __CLASS__, 'normalize' ), $rule['area_aliases'] ?? array() ), true ) ) { $matches[] = $rule; continue; }
			$type = $rule['type'];
			if ( 'unresolved' === $type ) { continue; }
			$key = 'street' === $type ? 'street' : ( 'locality' === $type ? ( ! empty( $data['settlement'] ) ? 'settlement' : 'city' ) : 'planning_structure' );
			if ( empty( $data[ $key . '_fias_id' ] ) ) { continue; }
			if ( 'street' === $type && ( 'симферополь' !== $city || ! empty( $data['settlement'] ) ) ) { continue; }
			$value = self::normalize( (string) ( $data[ $key ] ?? '' ) );
			foreach ( $rule['aliases'] as $alias ) {
				if ( $value === self::normalize( $alias ) ) { $matches[] = $rule; break; }
			}
		}
		$amounts = array_unique( array_column( $matches, 'minimum' ) );
		if ( 1 !== count( $amounts ) ) {
			// Conflicting exact identities are not resolved by an approximate geographic hypothesis.
			return $matches ? $unknown : self::geographic( $data, $unknown );
		}
		$minimum = (int) reset( $amounts );
		return array( 'status' => 'resolved', 'minimum' => $minimum, 'basis' => 'fias_identity', 'sources' => array_column( $matches, 'cell' ), 'message' => 'Бесплатная доставка при заказе от ' . number_format( $minimum, 0, '.', ' ' ) . ' ₽.' );
	}

	/** Owner-approved coverage: containing area first, nearest existing area next. */
	private static function geographic( array $data, array $unknown ): array {
		if ( 'staging' !== wp_get_environment_type() || ! RollsBar_Geocode_Policy::can_auto_assign_zone( $data['qc_geo'] ?? null ) ) { return $unknown; }
		$lat = $data['geo_lat'] ?? null; $lon = $data['geo_lon'] ?? null;
		if ( ! is_numeric( $lat ) || ! is_numeric( $lon ) || abs( (float) $lat ) > 90 || abs( (float) $lon ) > 180 || 0.0 === (float) $lat || 0.0 === (float) $lon ) { return $unknown; }
		static $geography;
		if ( null === $geography ) { $geography = json_decode( file_get_contents( dirname( __DIR__ ) . '/data/delivery-geography.json' ), true, 512, JSON_THROW_ON_ERROR ); }
		$matches = array(); $nearest = array(); $best = INF;
		foreach ( $geography['features'] as $feature ) {
			$geometry = $feature['geometry'];
			$polygons = 'Polygon' === $geometry['type'] ? array( $geometry['coordinates'] ) : $geometry['coordinates'];
			foreach ( $polygons as $polygon ) {
				$distance = self::polygon_distance( (float) $lon, (float) $lat, $polygon );
				if ( $distance < $best - 0.000001 ) { $best = $distance; $nearest = array( $feature['properties'] ); }
				elseif ( abs( $distance - $best ) <= 0.000001 ) { $nearest[] = $feature['properties']; }
				$inside = self::in_ring( (float) $lon, (float) $lat, $polygon[0] );
				foreach ( array_slice( $polygon, 1 ) as $hole ) { if ( self::in_ring( (float) $lon, (float) $lat, $hole ) ) { $inside = false; } }
				if ( $inside ) { $matches[] = $feature['properties']; break; }
			}
		}
		// Geographic locality footprints take priority over the city background.
		$local = array_values( array_filter( $matches, static fn( $m ) => 'locality' === $m['kind'] ) );
		$matches = $local ?: $matches;
		$inside = (bool) $matches;
		$matches = $matches ?: $nearest;
		if ( ! $matches ) { return $unknown; }
		// An exact shared edge/equal distance uses the higher existing minimum.
		$minimum = (int) max( array_column( $matches, 'minimum' ) );
		return array( 'status' => 'resolved', 'minimum' => $minimum, 'basis' => $inside ? 'owner_geographic_advisory' : 'owner_nearest_zone', 'distance_m' => $inside ? 0 : (int) round( $best ), 'provisional' => true, 'zones' => array_values( array_unique( array_column( $matches, 'id' ) ) ), 'message' => 'Бесплатная доставка от ' . number_format( $minimum, 0, '.', ' ' ) . ' ₽.' );
	}

	/** Distance to polygon area, including hole boundaries, in local metric coordinates. */
	private static function polygon_distance( float $x, float $y, array $polygon ): float {
		$inside = self::in_ring( $x, $y, $polygon[0] );
		foreach ( array_slice( $polygon, 1 ) as $hole ) { if ( self::in_ring( $x, $y, $hole ) ) { $inside = false; } }
		if ( $inside ) { return 0.0; }
		$scale_x = 6371000 * M_PI / 180 * cos( deg2rad( $y ) ); $scale_y = 6371000 * M_PI / 180; $best = INF;
		foreach ( $polygon as $ring ) {
			for ( $i = 0, $j = count( $ring ) - 1; $i < count( $ring ); $j = $i++ ) {
				$ax = ( $ring[$j][0] - $x ) * $scale_x; $ay = ( $ring[$j][1] - $y ) * $scale_y;
				$bx = ( $ring[$i][0] - $x ) * $scale_x; $by = ( $ring[$i][1] - $y ) * $scale_y;
				$dx = $bx - $ax; $dy = $by - $ay; $length = $dx * $dx + $dy * $dy;
				$t = $length > 0 ? max( 0, min( 1, -( $ax * $dx + $ay * $dy ) / $length ) ) : 0;
				$best = min( $best, hypot( $ax + $t * $dx, $ay + $t * $dy ) );
			}
		}
		return $best;
	}

	/** Ray casting with explicit edge inclusion; holes are excluded by the caller. */
	private static function in_ring( float $x, float $y, array $ring ): bool {
		$inside = false; $count = count( $ring );
		for ( $i = 0, $j = $count - 1; $i < $count; $j = $i++ ) {
			$a = $ring[$j]; $b = $ring[$i];
			$cross = ( $x - $a[0] ) * ( $b[1] - $a[1] ) - ( $y - $a[1] ) * ( $b[0] - $a[0] );
			if ( abs( $cross ) < 1e-12 && $x >= min( $a[0], $b[0] ) && $x <= max( $a[0], $b[0] ) && $y >= min( $a[1], $b[1] ) && $y <= max( $a[1], $b[1] ) ) { return true; }
			if ( ( $a[1] > $y ) !== ( $b[1] > $y ) && $x < ( $b[0] - $a[0] ) * ( $y - $a[1] ) / ( $b[1] - $a[1] ) + $a[0] ) { $inside = ! $inside; }
		}
		return $inside;
	}

	/** Signed provider identity; client-supplied minima never enter this contract. */
	public static function proof( array $data, string $display ): string {
		$keys = array( 'qc_geo', 'house', 'house_fias_id', 'geo_lat', 'geo_lon', 'region', 'city', 'city_fias_id', 'area', 'settlement', 'settlement_fias_id', 'street', 'street_fias_id', 'planning_structure', 'planning_structure_fias_id' );
		$payload = base64_encode( wp_json_encode( array( 'data' => array_intersect_key( $data, array_flip( $keys ) ), 'display' => $display, 'expires' => time() + 12 * HOUR_IN_SECONDS ) ) );
		return $payload . '.' . hash_hmac( 'sha256', $payload, wp_salt( 'auth' ) );
	}

	public static function verify( string $proof, string $address, float $amount ): array {
		$invalid = array( 'status' => 'unresolved', 'minimum' => null, 'message' => 'Выберите адрес с домом из подсказок, чтобы определить условия доставки.' );
		if ( strlen( $proof ) > 10000 || 1 !== substr_count( $proof, '.' ) ) { return $invalid; }
		list( $payload, $signature ) = explode( '.', $proof, 2 );
		if ( ! hash_equals( hash_hmac( 'sha256', $payload, wp_salt( 'auth' ) ), $signature ) ) { return $invalid; }
		$decoded = json_decode( (string) base64_decode( $payload, true ), true );
		if ( ! is_array( $decoded ) || ( $decoded['expires'] ?? 0 ) < time() || trim( $address ) !== ( $decoded['display'] ?? null ) || ! is_array( $decoded['data'] ?? null ) ) { return $invalid; }
		$result = self::classify( $decoded['data'] );
		if ( 'resolved' === $result['status'] && (int) round( $amount * 100 ) < $result['minimum'] * 100 ) {
			$result['status'] = 'below_minimum';
			$result['message'] = 'Для доставки добавьте товары на ' . number_format( $result['minimum'] - $amount, 2, ',', ' ' ) . ' ₽. Минимальный заказ — ' . $result['minimum'] . ' ₽.';
		}
		return $result;
	}
}
