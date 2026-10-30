<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }
$map_url = '';
if ( 'staging' === wp_get_environment_type() && defined( 'ROLLSBAR_CORE_FILE' ) ) {
    $map_file = dirname( ROLLSBAR_CORE_FILE ) . '/assets/delivery-map.html';
    $map_url = add_query_arg( 'ver', rollsbar_theme_asset_version( $map_file, ROLLSBAR_CORE_VERSION ), plugins_url( 'assets/delivery-map.html', ROLLSBAR_CORE_FILE ) );
}
?>
<section class="rollsbar-home-delivery rollsbar-shell" id="delivery">
  <div class="delivery-layout">
    <article class="delivery-card">
      <div class="delivery-card__head">
        <h2>Карта доставки</h2>
        <p>Минимальная сумма заказа для бесплатной доставки зависит от адреса.</p>
      </div>
      <?php if ( $map_url ) : ?>
        <iframe class="rollsbar-delivery-map" title="Карта зон доставки Rolls Bar" src="<?php echo esc_url( $map_url ); ?>" loading="lazy"></iframe>
      <?php endif; ?>
      <div class="map-note">Выберите адрес при оформлении — покажем минимальную сумму для него. Если адрес определён приблизительно, покажем предварительный минимум. Условия уточнит менеджер, заявку можно оставить.</div>
    </article>
    <aside class="conditions-card">
      <h3>Доставка и оплата</h3>
      <div class="condition"><b>Доставка курьером</b><span>Минимальная сумма определяется по адресу при оформлении заказа. Если минимум определён точно, для доставки нужно набрать эту сумму.</span></div>
      <div class="condition"><b>Самовывоз</b><span>Симферополь, Кечкеметская улица, 1. Минимальная сумма доставки на самовывоз не распространяется.</span></div>
      <div class="condition"><b>Оплата</b><span>Наличными или картой при получении.</span></div>
      <div class="notice">Если адрес не удалось определить, оставьте телефон и согласие на обработку персональных данных — менеджер свяжется с вами и уточнит доставку.</div>
    </aside>
  </div>
</section>
