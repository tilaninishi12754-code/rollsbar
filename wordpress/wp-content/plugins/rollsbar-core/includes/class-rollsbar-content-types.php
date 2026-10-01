<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class RollsBar_Content_Types {

	public static function init(): void {
		add_action( 'init', array( __CLASS__, 'register_post_types' ) );
		add_action( 'add_meta_boxes', array( __CLASS__, 'register_promo_meta' ) );
		add_action( 'save_post_rb_promo', array( __CLASS__, 'save_promo_meta' ) );
	}

	public static function register_post_types(): void {
		register_post_type(
			'rb_promo',
			array(
				'labels' => array(
					'name'          => 'Промо-карточки',
					'singular_name' => 'Промо-карточка',
					'add_new_item'  => 'Добавить промо-карточку',
					'edit_item'     => 'Редактировать промо-карточку',
				),
				'public'              => false,
				'show_ui'             => true,
				'show_in_menu'        => 'rollsbar-settings',
				'show_in_rest'        => true,
				'supports'            => array( 'title', 'editor', 'excerpt', 'thumbnail', 'page-attributes' ),
				'menu_icon'           => 'dashicons-images-alt2',
				'capability_type'     => 'post',
				'map_meta_cap'        => true,
			)
		);

		register_post_type(
			'rb_vacancy',
			array(
				'labels' => array(
					'name'          => 'Вакансии',
					'singular_name' => 'Вакансия',
					'add_new_item'  => 'Добавить вакансию',
					'edit_item'     => 'Редактировать вакансию',
				),
				'public'              => false,
				'show_ui'             => true,
				'show_in_menu'        => 'rollsbar-settings',
				'show_in_rest'        => true,
				'supports'            => array( 'title', 'editor', 'excerpt', 'page-attributes' ),
				'menu_icon'           => 'dashicons-businessperson',
				'capability_type'     => 'post',
				'map_meta_cap'        => true,
			)
		);
	}

	public static function register_promo_meta(): void {
		add_meta_box(
			'rollsbar_promo_details',
			'Параметры карточки',
			array( __CLASS__, 'render_promo_meta' ),
			'rb_promo',
			'normal',
			'high'
		);
	}

	public static function render_promo_meta( WP_Post $post ): void {
		wp_nonce_field( 'rollsbar_save_promo', 'rollsbar_promo_nonce' );

		$eyebrow = (string) get_post_meta( $post->ID, '_rollsbar_promo_eyebrow', true );
		$url     = (string) get_post_meta( $post->ID, '_rollsbar_promo_url', true );
		$variant = (string) get_post_meta( $post->ID, '_rollsbar_promo_variant', true );

		?>
		<p>
			<label for="rollsbar_promo_eyebrow"><strong>Маленькая подпись</strong></label><br>
			<input class="regular-text" id="rollsbar_promo_eyebrow" name="rollsbar_promo_eyebrow" value="<?php echo esc_attr( $eyebrow ); ?>" placeholder="Например: Команда">
		</p>
		<p>
			<label for="rollsbar_promo_url"><strong>Ссылка</strong></label><br>
			<input class="regular-text" id="rollsbar_promo_url" name="rollsbar_promo_url" value="<?php echo esc_attr( $url ); ?>" placeholder="/rabota-v-rolls-bar/">
		</p>
		<p>
			<label for="rollsbar_promo_variant"><strong>Цвет карточки</strong></label><br>
			<select id="rollsbar_promo_variant" name="rollsbar_promo_variant">
				<?php
				$options = array(
					'promo'    => 'Красный',
					'work'     => 'Тёмный',
					'delivery' => 'Оранжевый',
					'reviews'  => 'Зелёный',
				);
				foreach ( $options as $value => $label ) :
					?>
					<option value="<?php echo esc_attr( $value ); ?>" <?php selected( $variant, $value ); ?>><?php echo esc_html( $label ); ?></option>
				<?php endforeach; ?>
			</select>
		</p>
		<p class="description">Название = крупный заголовок. Краткое описание = нижняя строка. Изображение записи = фото карточки. Порядок задаётся полем «Порядок».</p>
		<?php
	}

	public static function save_promo_meta( int $post_id ): void {
		if (
			! isset( $_POST['rollsbar_promo_nonce'] ) ||
			! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['rollsbar_promo_nonce'] ) ), 'rollsbar_save_promo' ) ||
			( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) ||
			! current_user_can( 'edit_post', $post_id )
		) {
			return;
		}

		$eyebrow = isset( $_POST['rollsbar_promo_eyebrow'] )
			? sanitize_text_field( wp_unslash( $_POST['rollsbar_promo_eyebrow'] ) )
			: '';

		$url = isset( $_POST['rollsbar_promo_url'] )
			? esc_url_raw( wp_unslash( $_POST['rollsbar_promo_url'] ) )
			: '';

		$variant = isset( $_POST['rollsbar_promo_variant'] )
			? sanitize_key( wp_unslash( $_POST['rollsbar_promo_variant'] ) )
			: 'promo';

		if ( ! in_array( $variant, array( 'promo', 'work', 'delivery', 'reviews' ), true ) ) {
			$variant = 'promo';
		}

		update_post_meta( $post_id, '_rollsbar_promo_eyebrow', $eyebrow );
		update_post_meta( $post_id, '_rollsbar_promo_url', $url );
		update_post_meta( $post_id, '_rollsbar_promo_variant', $variant );
	}
}
