<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class RollsBar_SMTP {
	public static function init(): void {
		add_action( 'phpmailer_init', array( __CLASS__, 'configure_phpmailer' ), 20 );
		add_filter( 'wp_mail_from', array( __CLASS__, 'filter_from_address' ), 20 );
		add_filter( 'wp_mail_from_name', array( __CLASS__, 'filter_from_name' ), 20 );
	}

	public static function is_configured(): bool {
		return defined( 'ROLLSBAR_SMTP_ENABLED' )
			&& (bool) ROLLSBAR_SMTP_ENABLED
			&& defined( 'ROLLSBAR_SMTP_HOST' )
			&& '' !== trim( (string) ROLLSBAR_SMTP_HOST )
			&& defined( 'ROLLSBAR_SMTP_USERNAME' )
			&& is_email( (string) ROLLSBAR_SMTP_USERNAME )
			&& defined( 'ROLLSBAR_SMTP_APP_PASSWORD' )
			&& '' !== trim( (string) ROLLSBAR_SMTP_APP_PASSWORD );
	}

	public static function configure_phpmailer( $phpmailer ): void {
		if ( ! self::is_configured() ) {
			return;
		}

		$host       = (string) ROLLSBAR_SMTP_HOST;
		$username   = (string) ROLLSBAR_SMTP_USERNAME;
		$password   = (string) ROLLSBAR_SMTP_APP_PASSWORD;
		$port       = defined( 'ROLLSBAR_SMTP_PORT' ) ? (int) ROLLSBAR_SMTP_PORT : 587;
		$encryption = defined( 'ROLLSBAR_SMTP_SECURE' ) ? trim( (string) ROLLSBAR_SMTP_SECURE ) : 'tls';

		$phpmailer->isSMTP();
		$phpmailer->Host       = $host;
		$phpmailer->Port       = $port;
		$phpmailer->SMTPAuth   = true;
		$phpmailer->Username   = $username;
		$phpmailer->Password   = $password;
		$phpmailer->SMTPSecure = $encryption;
		$phpmailer->SMTPAutoTLS = true;
		$phpmailer->CharSet    = 'UTF-8';
	}

	public static function filter_from_address( string $from ): string {
		if ( ! self::is_configured() ) {
			return $from;
		}

		$address = defined( 'ROLLSBAR_SMTP_FROM_ADDRESS' )
			? trim( (string) ROLLSBAR_SMTP_FROM_ADDRESS )
			: trim( (string) ROLLSBAR_SMTP_USERNAME );

		return is_email( $address ) ? $address : $from;
	}

	public static function filter_from_name( string $name ): string {
		if ( ! self::is_configured() || ! defined( 'ROLLSBAR_SMTP_FROM_NAME' ) ) {
			return $name;
		}

		$from_name = trim( (string) ROLLSBAR_SMTP_FROM_NAME );
		return '' !== $from_name ? $from_name : $name;
	}
}
