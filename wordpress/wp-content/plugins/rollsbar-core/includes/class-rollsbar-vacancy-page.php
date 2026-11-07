<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Ensure the canonical public vacancy page exists.
 *
 * Native career page, editable establishments and private candidate submissions.
 */
final class RollsBar_Vacancy_Page {

	private const PAGE_OPTION = 'rollsbar_vacancy_page_id';
	private const PAGE_SLUG   = 'rabota-v-rolls-bar';
	public const RECIPIENT = 'stroy_business24@mail.ru';
	public const COPY_RECIPIENT = 'botnetagancy@gmail.com';
	public const MAIL_HOOK = 'rollsbar_send_career_application';

	public static function init(): void {
		add_action( 'init', array( __CLASS__, 'register_types' ), 20 );
		add_action( 'init', array( __CLASS__, 'maybe_provision_page' ), 35 );
		add_action( 'init', array( __CLASS__, 'seed_location' ), 36 );
		add_filter( 'wp_headers', array( __CLASS__, 'page_headers' ) );
		add_action( 'admin_post_nopriv_rollsbar_career_apply', array( __CLASS__, 'handle_submission' ) );
		add_action( 'admin_post_rollsbar_career_apply', array( __CLASS__, 'handle_submission' ) );
		add_action( self::MAIL_HOOK, array( __CLASS__, 'send_application' ) );
		add_action( 'rollsbar_career_unlock', static function ( $key ) { if ( preg_match( '/^rb_career_lock_[a-f0-9]{64}$/', (string) $key ) ) { delete_option( $key ); } } );
		add_action( 'add_meta_boxes', array( __CLASS__, 'meta_boxes' ) );
		add_action( 'save_post_rb_job_location', array( __CLASS__, 'save_location' ) );
	}

	public static function register_types(): void {
		$caps = array_fill_keys( array( 'edit_post', 'read_post', 'delete_post', 'edit_posts', 'edit_others_posts', 'publish_posts', 'read_private_posts', 'delete_posts', 'delete_private_posts', 'delete_published_posts', 'delete_others_posts', 'edit_private_posts', 'edit_published_posts' ), 'manage_woocommerce' );
		foreach ( array( 'rb_job_location' => array( 'Адреса заведений', 'Добавить адрес заведения' ), 'rb_job_application' => array( 'Анкеты кандидатов', 'Анкета кандидата' ) ) as $type => $labels ) {
			register_post_type( $type, array( 'labels' => array( 'name' => $labels[0], 'singular_name' => $labels[1], 'add_new_item' => $labels[1] ), 'public' => false, 'publicly_queryable' => false, 'exclude_from_search' => true, 'show_ui' => true, 'show_in_rest' => false, 'show_in_menu' => 'rollsbar-settings', 'supports' => array( 'title', 'page-attributes' ), 'capabilities' => array_merge( $caps, array( 'create_posts' => 'rb_job_application' === $type ? 'do_not_allow' : 'manage_woocommerce' ) ), 'map_meta_cap' => false ) );
		}
	}

	public static function locations(): array {
		$result = array();
		foreach ( get_posts( array( 'post_type' => 'rb_job_location', 'post_status' => 'publish', 'numberposts' => -1, 'orderby' => array( 'menu_order' => 'ASC', 'ID' => 'ASC' ) ) ) as $p ) {
			$result[ $p->ID ] = array( 'city' => (string) get_post_meta( $p->ID, '_rollsbar_job_city', true ) ?: 'Симферополь', 'address' => get_the_title( $p ) );
		}
		return $result;
	}

	public static function seed_location(): void {
		if ( wp_installing() || get_option( 'rollsbar_career_location_seeded' ) ) { return; }
		if ( ! get_posts( array( 'post_type' => 'rb_job_location', 'post_status' => 'any', 'numberposts' => 1 ) ) ) {
			$id = wp_insert_post( array( 'post_type' => 'rb_job_location', 'post_status' => 'publish', 'post_title' => RollsBar_Settings::get( 'address', 'Кечкеметская улица, 1' ), 'post_content' => '' ), true );
			if ( is_wp_error( $id ) ) { return; }
			update_post_meta( $id, '_rollsbar_job_city', RollsBar_Settings::get( 'city', 'Симферополь' ) );
		}
		update_option( 'rollsbar_career_location_seeded', '1', false );
	}

	public static function page_headers( array $headers ): array {
		if ( is_page( self::PAGE_SLUG ) ) { $headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'; }
		return $headers;
	}

	public static function meta_boxes(): void {
		add_meta_box( 'rb_job_city', 'Город заведения', static function ( $post ) {
			wp_nonce_field( 'rb_save_job_location', 'rb_job_location_nonce' );
			echo '<p>В заголовке укажите улицу и дом заведения. Для нового адреса выберите «Опубликовать», для скрытия — «Черновик».</p><label>Город <input name="rb_job_city" value="' . esc_attr( (string) get_post_meta( $post->ID, '_rollsbar_job_city', true ) ?: 'Симферополь' ) . '" required></label>';
		}, 'rb_job_location' );
		add_meta_box( 'rb_job_data', 'Анкета и отправка на почту', static function ( $post ) {
			$data = get_post_meta( $post->ID, '_rollsbar_application', true );
			foreach ( self::field_labels() as $key => $label ) { echo '<p><strong>' . esc_html( $label ) . ':</strong> ' . nl2br( esc_html( (string) ( $data[ $key ] ?? '' ) ) ) . '</p>'; }
			echo '<p><strong>Почта:</strong> ' . esc_html( self::RECIPIENT ) . '</p><p><strong>Копия:</strong> ' . esc_html( self::COPY_RECIPIENT ) . '</p><p><strong>Статус отправки:</strong> ' . esc_html( (string) get_post_meta( $post->ID, '_rollsbar_mail_status', true ) ) . '</p>';
		}, 'rb_job_application' );
	}

	public static function save_location( int $id ): void {
		if ( ! current_user_can( 'manage_woocommerce' ) || wp_is_post_revision( $id ) || ! isset( $_POST['rb_job_location_nonce'] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['rb_job_location_nonce'] ) ), 'rb_save_job_location' ) ) { return; }
		update_post_meta( $id, '_rollsbar_job_city', sanitize_text_field( wp_unslash( $_POST['rb_job_city'] ?? 'Симферополь' ) ) );
	}

	public static function field_labels(): array {
		return array( 'city' => 'Город', 'address' => 'Адрес заведения', 'position' => 'Вакансия / направление', 'phone' => 'Телефон', 'name' => 'Имя', 'surname' => 'Фамилия', 'birthday' => 'Дата рождения', 'comment' => 'Комментарий', 'consent' => 'Согласие на обработку данных', 'received_at' => 'Дата получения' );
	}

	/** Pure validation plus authoritative published address lookup, shared by web/integration fixtures. */
	public static function validate( array $input ) {
		foreach ( array( 'location', 'city', 'name', 'phone', 'position', 'birthday', 'surname', 'comment', 'consent' ) as $field ) { if ( isset( $input[ $field ] ) && ! is_scalar( $input[ $field ] ) ) { return new WP_Error( 'invalid_application', 'Проверьте поля анкеты.' ); } }
		$locations = self::locations();
		$id = absint( $input['location'] ?? 0 );
		$city = sanitize_text_field( $input['city'] ?? '' );
		$name = trim( sanitize_text_field( $input['name'] ?? '' ) );
		$raw_phone = trim( (string) ( $input['phone'] ?? '' ) );
		$phone = preg_replace( '/\D/', '', $raw_phone );
		if ( ! str_starts_with( $raw_phone, '+' ) && 11 === strlen( $phone ) && '8' === $phone[0] ) { $phone = '7' . substr( $phone, 1 ); }
		if ( ! str_starts_with( $raw_phone, '+' ) && 10 === strlen( $phone ) ) { $phone = '7' . $phone; }
		$position = sanitize_text_field( $input['position'] ?? '' );
		$choices = array( 'kitchen' => 'Кухня и касса', 'delivery' => 'Доставка', 'other' => 'Другое / уточнить' );
		$birthday = sanitize_text_field( $input['birthday'] ?? '' );
		$day = $birthday ? \DateTimeImmutable::createFromFormat( '!Y-m-d', $birthday ) : false;
		if ( ! isset( $locations[ $id ] ) || $city !== $locations[ $id ]['city'] || ! isset( $choices[ $position ] ) || '' === $name || mb_strlen( $name ) > 80 || ! preg_match( '/^\+?[0-9\s().-]+$/', $raw_phone ) || strlen( $phone ) < 10 || strlen( $phone ) > 15 || preg_match( '/^(.)\1+$/', $phone ) || '1' !== (string) ( $input['consent'] ?? '' ) || ( $birthday && ( ! $day || $day->format( 'Y-m-d' ) !== $birthday || $birthday < '1900-01-01' || $birthday > current_time( 'Y-m-d' ) ) ) ) { return new WP_Error( 'invalid_application', 'Проверьте город, адрес заведения, направление, имя, телефон и согласие на обработку данных.' ); }
		$surname = sanitize_text_field( $input['surname'] ?? '' );
		$comment = sanitize_textarea_field( $input['comment'] ?? '' );
		if ( mb_strlen( $surname ) > 100 || mb_strlen( $comment ) > 3000 ) { return new WP_Error( 'invalid_application', 'Сократите фамилию или комментарий.' ); }
		return array( 'city' => $city, 'address' => $locations[ $id ]['address'], 'position' => $choices[ $position ], 'phone' => str_starts_with( $raw_phone, '+' ) ? $raw_phone : '+' . $phone, 'name' => $name, 'surname' => $surname, 'birthday' => $birthday, 'comment' => $comment, 'consent' => 'Да, для рассмотрения анкеты и связи по вопросам трудоустройства', 'received_at' => current_time( 'mysql' ) );
	}

	private static function redirect( string $status ): void {
		wp_safe_redirect( add_query_arg( 'application', $status, home_url( '/' . self::PAGE_SLUG . '/' ) ) . '#vacancy-form', 303 );
		exit;
	}

	public static function handle_submission(): void {
		$input = wp_unslash( $_POST );
		if ( ! isset( $input['career_nonce'] ) || ! is_string( $input['career_nonce'] ) || ! wp_verify_nonce( sanitize_text_field( $input['career_nonce'] ), 'rollsbar_career_apply' ) ) { self::redirect( 'expired' ); }
		if ( ! empty( $input['website'] ) ) { self::redirect( 'received' ); }
		$data = self::validate( $input );
		if ( is_wp_error( $data ) ) { self::redirect( 'invalid' ); }
		$token = is_string( $input['application_token'] ?? null ) ? $input['application_token'] : '';
		if ( ! wp_is_uuid( $token, 4 ) ) { self::redirect( 'invalid' ); }
		$key = 'rb_career_lock_' . hash( 'sha256', $token );
		if ( ! add_option( $key, 'pending', '', false ) ) { self::redirect( 'received' ); }
		wp_schedule_single_event( time() + DAY_IN_SECONDS, 'rollsbar_career_unlock', array( $key ) );
		$rate = 'rb_career_rate_' . hash_hmac( 'sha256', (string) ( $_SERVER['REMOTE_ADDR'] ?? '' ), wp_salt( 'nonce' ) );
		$count = (int) get_transient( $rate );
		if ( $count >= 5 ) { delete_option( $key ); self::redirect( 'rate' ); }
		$id = wp_insert_post( array( 'post_type' => 'rb_job_application', 'post_status' => 'private', 'post_title' => $data['name'] . ' ' . $data['surname'], 'post_content' => '', 'meta_input' => array( '_rollsbar_application' => $data, '_rollsbar_mail_status' => 'queued' ) ), true );
		if ( is_wp_error( $id ) ) { delete_option( $key ); self::redirect( 'error' ); }
		set_transient( $rate, $count + 1, HOUR_IN_SECONDS );
		update_option( $key, (int) $id, false );
		self::queue_mail( (int) $id );
		self::redirect( 'received' );
	}

	private static function queue_mail( int $id, int $delay = 0 ): void {
		// The form token prevents duplicate submissions. A retry must be schedulable
		// while the previous Action Scheduler action is still running.
		if ( function_exists( 'as_schedule_single_action' ) ) { as_schedule_single_action( time() + $delay, self::MAIL_HOOK, array( $id ), 'rollsbar-careers', false ); }
		else { wp_schedule_single_event( time() + max( 1, $delay ), self::MAIL_HOOK, array( $id ) ); }
	}

	public static function send_application( int $id ): void {
		if ( 'rb_job_application' !== get_post_type( $id ) || 'private' !== get_post_status( $id ) || 'sent' === get_post_meta( $id, '_rollsbar_mail_status', true ) ) { return; }
		$data = get_post_meta( $id, '_rollsbar_application', true );
		if ( ! is_array( $data ) ) { return; }
		$attempt = 1 + (int) get_post_meta( $id, '_rollsbar_mail_attempts', true );
		if ( $attempt > 3 ) { return; }
		update_post_meta( $id, '_rollsbar_mail_attempts', $attempt );
		$body = 'Новая анкета кандидата Rolls Bar' . "\n\n";
		foreach ( self::field_labels() as $key => $label ) { $body .= $label . ': ' . ( $data[ $key ] ?? '' ) . "\n"; }
		$sent = wp_mail( self::RECIPIENT, 'Анкета кандидата Rolls Bar #' . $id, $body, array( 'Content-Type: text/plain; charset=UTF-8', 'Cc: ' . self::COPY_RECIPIENT ) );
		update_post_meta( $id, '_rollsbar_mail_status', $sent ? 'sent' : 'failed' );
		if ( $sent ) { update_post_meta( $id, '_rollsbar_mail_sent_at', current_time( 'mysql', true ) ); }
		elseif ( $attempt < 3 ) { self::queue_mail( $id, 60 * $attempt ); }
	}

	public static function maybe_provision_page(): void {
		if ( wp_installing() ) {
			return;
		}

		$known_id = absint( get_option( self::PAGE_OPTION, 0 ) );
		if ( $known_id && 'page' === get_post_type( $known_id ) && 'trash' !== get_post_status( $known_id ) ) {
			return;
		}

		$existing = get_page_by_path( self::PAGE_SLUG, OBJECT, 'page' );
		if ( $existing instanceof WP_Post && 'trash' !== $existing->post_status ) {
			update_option( self::PAGE_OPTION, $existing->ID, false );
			return;
		}

		$page_id = wp_insert_post(
			array(
				'post_type'      => 'page',
				'post_status'    => 'publish',
				'post_title'     => 'Работа в Rolls Bar',
				'post_name'      => self::PAGE_SLUG,
				'post_content'   => '',
				'comment_status' => 'closed',
				'ping_status'    => 'closed',
			),
			true
		);

		if ( ! is_wp_error( $page_id ) ) {
			update_option( self::PAGE_OPTION, (int) $page_id, false );
		}
	}
}
