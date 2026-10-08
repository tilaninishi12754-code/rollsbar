<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Safety policy for provider geocode precision before delivery-zone lookup.
 *
 * DaData qc_geo meanings come from the provider's documented address API:
 * 0 exact house, 1 nearest house, 2 street, 3 settlement, 4 city,
 * 5 coordinates not determined.
 *
 * Only exact-house coordinates may silently drive point-in-polygon delivery
 * assignment. Everything else requires explicit customer clarification or a
 * later approved fallback flow.
 */
final class RollsBar_Geocode_Policy {

	public static function evaluate( $qc_geo ): array {
		$qc = is_numeric( $qc_geo ) ? (int) $qc_geo : null;

		if ( 0 === $qc ) {
			return array(
				'qc_geo'                => 0,
				'status'                => 'exact_house',
				'allow_auto_zone'       => true,
				'requires_confirmation' => false,
				'requires_fallback'     => false,
			);
		}

		if ( 1 === $qc ) {
			return array(
				'qc_geo'                => 1,
				'status'                => 'nearest_house',
				'allow_auto_zone'       => false,
				'requires_confirmation' => true,
				'requires_fallback'     => false,
			);
		}

		if ( null !== $qc && $qc >= 2 && $qc <= 4 ) {
			return array(
				'qc_geo'                => $qc,
				'status'                => 'insufficient_precision',
				'allow_auto_zone'       => false,
				'requires_confirmation' => true,
				'requires_fallback'     => true,
			);
		}

		return array(
			'qc_geo'                => $qc,
			'status'                => 'unresolved',
			'allow_auto_zone'       => false,
			'requires_confirmation' => true,
			'requires_fallback'     => true,
		);
	}

	public static function can_auto_assign_zone( $qc_geo ): bool {
		$policy = self::evaluate( $qc_geo );
		return true === $policy['allow_auto_zone'];
	}
}
