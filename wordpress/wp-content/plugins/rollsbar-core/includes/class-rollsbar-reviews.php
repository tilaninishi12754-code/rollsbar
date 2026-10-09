<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Client-safe site reviews.
 *
 * Public submissions are always created with post_status=pending. Nothing
 * becomes customer-visible until a WordPress administrator explicitly
 * publishes the review.
 */
final class RollsBar_Reviews {

	private const PAGE_OPTION = 'rollsbar_reviews_page_id';
	private const MAX_PHOTO_BYTES = 5242880; // 5 MiB.

	public static function init(): void {
		add_action( 'init', array( __CLASS__, 'maybe_provision_page' ), 30 );
		add_action( 'admin_post_nopriv_rollsbar_submit_review', array( __CLASS__, 'handle_submission' ) );
		add_action( 'admin_post_rollsbar_submit_review', array( __CLASS__, 'handle_submission' ) );
		add_action( 'add_meta_boxes', array( __CLASS__, 'register_meta_box' ) );
		add_action( 'save_post_rb_review', array( __CLASS__, 'save_admin_meta' ) );
		add_filter( 'manage_rb_review_posts_columns', array( __CLASS__, 'admin_columns' ) );
		add_action( 'manage_rb_review_posts_custom_column', array( __CLASS__, 'render_admin_column' ), 10, 2 );
	}

	/**
	 * Ensure the approved /otzyvy/ page exists without manual bootstrap work.
	 * The operation is idempotent and writes only when the page is absent.
	 */
	public static function maybe_provision_page(): void {
		if ( wp_installing() ) {
			return;
		}

		$known_id = absint( get_option( self::PAGE_OPTION, 0 ) );
		if ( $known_id && 'page' === get_post_type( $known_id ) && 'trash' !== get_post_status( $known_id ) ) {
			return;
		}

		$existing = get_page_by_path( 'otzyvy', OBJECT, 'page' );
		if ( $existing instanceof WP_Post ) {
			update_option( self::PAGE_OPTION, $existing->ID, false );
			return;
		}

		$page_id = wp_insert_post(
			array(
				'post_type'      => 'page',
				'post_status'    => 'publish',
				'post_title'     => 'Отзывы',
				'post_name'      => 'otzyvy',
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

	public static function handle_submission(): void {
		if ( ! isset( $_POST['rollsbar_review_nonce'] ) ) {
			self::redirect( 'error' );
		}

		$nonce = sanitize_text_field( wp_unslash( $_POST['rollsbar_review_nonce'] ) );
		if ( ! wp_verify_nonce( $nonce, 'rollsbar_submit_review' ) ) {
			self::redirect( 'error' );
		}

		// Honeypot. Bots receive the same success redirect but nothing is stored.
		$honeypot = isset( $_POST['website'] )
			? trim( sanitize_text_field( wp_unslash( $_POST['website'] ) ) )
			: '';
		if ( '' !== $honeypot ) {
			self::redirect( 'received' );
		}

		$name = isset( $_POST['name'] )
			? trim( sanitize_text_field( wp_unslash( $_POST['name'] ) ) )
			: '';
		$rating = isset( $_POST['rating'] ) ? absint( $_POST['rating'] ) : 0;
		$text = isset( $_POST['text'] )
			? trim( sanitize_textarea_field( wp_unslash( $_POST['text'] ) ) )
			: '';

		if ( '' === $name || '' === $text || $rating < 1 || $rating > 5 ) {
			self::redirect( 'invalid' );
		}

		if ( strlen( $name ) > 160 || strlen( $text ) > 12000 ) {
			self::redirect( 'invalid' );
		}

		$review_id = self::create_pending_review( $name, $rating, $text );
		if ( is_wp_error( $review_id ) ) {
			self::redirect( 'error' );
		}

		self::handle_photo_upload( (int) $review_id );
		self::redirect( 'received' );
	}

	/**
	 * Create a review in the exact state used by public form submissions.
	 * Kept public so staging runtime verification can prove moderation behavior
	 * without faking a browser submission or leaving QA content behind.
	 *
	 * @return int|WP_Error
	 */
	public static function create_pending_review( string $name, int $rating, string $text ) {
		$name = trim( sanitize_text_field( $name ) );
		$text = trim( sanitize_textarea_field( $text ) );
		$rating = absint( $rating );

		if ( '' === $name || '' === $text || $rating < 1 || $rating > 5 ) {
			return new WP_Error( 'rollsbar_invalid_review', 'Invalid review payload.' );
		}

		$review_id = wp_insert_post(
			array(
				'post_type'      => 'rb_review',
				'post_status'    => 'pending',
				'post_title'     => $name,
				'post_content'   => $text,
				'comment_status' => 'closed',
				'ping_status'    => 'closed',
			),
			true
		);

		if ( is_wp_error( $review_id ) ) {
			return $review_id;
		}

		update_post_meta( $review_id, '_rollsbar_review_rating', $rating );
		update_post_meta( $review_id, '_rollsbar_review_source', 'site' );
		update_post_meta( $review_id, '_rollsbar_review_submitted_at', gmdate( 'c' ) );

		return (int) $review_id;
	}

	private static function handle_photo_upload( int $review_id ): void {
		if (
			empty( $_FILES['photo'] ) ||
			! is_array( $_FILES['photo'] ) ||
			UPLOAD_ERR_NO_FILE === (int) ( $_FILES['photo']['error'] ?? UPLOAD_ERR_NO_FILE )
		) {
			return;
		}

		$file = $_FILES['photo'];
		if ( UPLOAD_ERR_OK !== (int) ( $file['error'] ?? UPLOAD_ERR_NO_FILE ) ) {
			return;
		}

		if ( (int) ( $file['size'] ?? 0 ) <= 0 || (int) $file['size'] > self::MAX_PHOTO_BYTES ) {
			return;
		}

		require_once ABSPATH . 'wp-admin/includes/file.php';
		require_once ABSPATH . 'wp-admin/includes/media.php';
		require_once ABSPATH . 'wp-admin/includes/image.php';

		$attachment_id = media_handle_upload( 'photo', $review_id );
		if ( is_wp_error( $attachment_id ) ) {
			update_post_meta(
				$review_id,
				'_rollsbar_review_photo_error',
				sanitize_text_field( $attachment_id->get_error_message() )
			);
			return;
		}

		set_post_thumbnail( $review_id, (int) $attachment_id );
	}

	private static function redirect( string $status ): void {
		$url = add_query_arg( 'review', sanitize_key( $status ), home_url( '/otzyvy/' ) );
		wp_safe_redirect( $url, 303 );
		exit;
	}

	public static function register_meta_box(): void {
		add_meta_box(
			'rollsbar_review_details',
			'Данные отзыва',
			array( __CLASS__, 'render_meta_box' ),
			'rb_review',
			'side',
			'high'
		);
	}

	public static function render_meta_box( WP_Post $post ): void {
		wp_nonce_field( 'rollsbar_save_review', 'rollsbar_review_admin_nonce' );
		$rating = absint( get_post_meta( $post->ID, '_rollsbar_review_rating', true ) );
		$source = (string) get_post_meta( $post->ID, '_rollsbar_review_source', true );
		?>
		<p>
			<label for="rollsbar_review_rating"><strong>Оценка</strong></label><br>
			<select id="rollsbar_review_rating" name="rollsbar_review_rating" style="width:100%;">
				<?php for ( $value = 5; $value >= 1; --$value ) : ?>
					<option value="<?php echo esc_attr( (string) $value ); ?>" <?php selected( $rating, $value ); ?>><?php echo esc_html( (string) $value ); ?> / 5</option>
				<?php endfor; ?>
			</select>
		</p>
		<p class="description">Источник: <?php echo esc_html( $source ?: 'admin' ); ?>. Отзывы с сайта создаются со статусом «На утверждении» и появляются на сайте только после публикации администратором.</p>
		<?php
	}

	public static function save_admin_meta( int $post_id ): void {
		if (
			! isset( $_POST['rollsbar_review_admin_nonce'] ) ||
			! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['rollsbar_review_admin_nonce'] ) ), 'rollsbar_save_review' ) ||
			( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) ||
			! current_user_can( 'edit_post', $post_id )
		) {
			return;
		}

		$rating = isset( $_POST['rollsbar_review_rating'] ) ? absint( $_POST['rollsbar_review_rating'] ) : 0;
		if ( $rating < 1 || $rating > 5 ) {
			return;
		}

		update_post_meta( $post_id, '_rollsbar_review_rating', $rating );
	}

	public static function admin_columns( array $columns ): array {
		$updated = array();
		foreach ( $columns as $key => $label ) {
			$updated[ $key ] = $label;
			if ( 'title' === $key ) {
				$updated['rollsbar_rating'] = 'Оценка';
			}
		}
		return $updated;
	}

	public static function render_admin_column( string $column, int $post_id ): void {
		if ( 'rollsbar_rating' !== $column ) {
			return;
		}

		$rating = absint( get_post_meta( $post_id, '_rollsbar_review_rating', true ) );
		echo esc_html( $rating ? $rating . ' / 5' : '—' );
	}
}
