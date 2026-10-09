<?php

if ( ! class_exists( 'RollsBar_Reviews' ) ) {
	throw new RuntimeException( 'RollsBar_Reviews is not loaded.' );
}

if ( ! post_type_exists( 'rb_review' ) ) {
	throw new RuntimeException( 'rb_review post type is not registered.' );
}

$page = get_page_by_path( 'otzyvy', OBJECT, 'page' );
if ( ! $page instanceof WP_Post || 'publish' !== get_post_status( $page ) ) {
	throw new RuntimeException( '/otzyvy/ page is not published.' );
}

$review_id = 0;

try {
	$created = RollsBar_Reviews::create_pending_review(
		'RollsBar QA Moderation',
		5,
		'Synthetic staging moderation check. This record must be removed automatically.'
	);

	if ( is_wp_error( $created ) ) {
		throw new RuntimeException( 'Synthetic review creation failed: ' . $created->get_error_message() );
	}

	$review_id = (int) $created;

	if ( 'pending' !== get_post_status( $review_id ) ) {
		throw new RuntimeException( 'New site review was not created as pending.' );
	}

	$rating = (int) get_post_meta( $review_id, '_rollsbar_review_rating', true );
	if ( 5 !== $rating ) {
		throw new RuntimeException( 'Review rating metadata was not saved.' );
	}

	$public_before = get_posts(
		array(
			'post_type'      => 'rb_review',
			'post_status'    => 'publish',
			'post__in'       => array( $review_id ),
			'posts_per_page' => 1,
			'fields'         => 'ids',
		)
	);

	if ( ! empty( $public_before ) ) {
		throw new RuntimeException( 'Pending review leaked into the public feed.' );
	}

	$updated = wp_update_post(
		array(
			'ID'          => $review_id,
			'post_status' => 'publish',
		),
		true
	);

	if ( is_wp_error( $updated ) || 'publish' !== get_post_status( $review_id ) ) {
		throw new RuntimeException( 'Admin publish transition failed.' );
	}

	$public_after = get_posts(
		array(
			'post_type'      => 'rb_review',
			'post_status'    => 'publish',
			'post__in'       => array( $review_id ),
			'posts_per_page' => 1,
			'fields'         => 'ids',
		)
	);

	if ( array( $review_id ) !== array_map( 'intval', $public_after ) ) {
		throw new RuntimeException( 'Published review did not enter the public feed.' );
	}

	echo "REVIEWS MODERATION RUNTIME PASS\n";
	echo "page=/otzyvy/ published=yes\n";
	echo "new_submission_status=pending\n";
	echo "pending_publicly_visible=no\n";
	echo "published_publicly_visible=yes\n";
} finally {
	if ( $review_id ) {
		wp_delete_post( $review_id, true );
	}
}
