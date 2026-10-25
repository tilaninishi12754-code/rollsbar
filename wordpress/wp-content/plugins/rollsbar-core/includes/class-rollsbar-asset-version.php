<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/** Content versions for local plugin assets; independent of the active theme. */
final class RollsBar_Asset_Version {

	/** Local absolute path -> SHA-256 prefix; supplied release version on failure. */
	public static function for_file( string $absolute_path, string $fallback ): string {
		static $versions = array();

		if ( ! array_key_exists( $absolute_path, $versions ) ) {
			$versions[ $absolute_path ] = null;
			if ( preg_match( '~^(?:/(?!/)|[A-Za-z]:[\\\\/])~', $absolute_path )
				&& @is_file( $absolute_path ) && @is_readable( $absolute_path ) ) {
				// The file can disappear after is_readable(); keep the public page safe.
				$hash = @hash_file( 'sha256', $absolute_path );
				if ( false !== $hash ) {
					$versions[ $absolute_path ] = substr( $hash, 0, 16 );
				}
			}
		}

		return $versions[ $absolute_path ] ?? $fallback;
	}
}
