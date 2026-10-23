<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }
// Public presentation only. Schematic SVG is decorative, never delivery-rule geometry.
?>
<section class="rollsbar-home-delivery rollsbar-shell" id="delivery">
      <div class="delivery-layout">
        <article class="delivery-card">
          <div class="delivery-card__head">

            <h2>Карта доставки</h2>
              <p>Адрес будет автоматически сопоставляться с утверждённой зоной. Реальные границы зон подключим после окончательного согласования с клиентом.</p>
          </div>
          <div class="yandex-map-wrap yandex-map-wrap--delivery" aria-label="Яндекс Карта Rolls Bar со схематичными зонами доставки">
            <iframe class="yandex-map-frame" title="Rolls Bar на Яндекс Картах" src="https://yandex.ru/map-widget/v1/?ll=34.099398%2C44.973541&mode=search&oid=229692973623&ol=biz&z=12&lang=ru_RU" loading="lazy" allowfullscreen></iframe>
            <svg class="delivery-zone-overlay" viewBox="0 0 1000 620" preserveAspectRatio="none" aria-hidden="true">
              <polygon class="zone-3" points="70,155 210,55 510,35 805,80 955,235 930,445 735,570 405,585 145,505 35,330"/>
              <polygon class="zone-2" points="185,190 300,110 525,95 745,135 850,255 815,405 665,495 430,505 250,445 145,320"/>
              <polygon class="zone-1" points="330,230 420,175 555,170 675,220 715,315 655,390 535,430 410,405 320,335 285,275"/>
            </svg>
            <span class="map-schema-chip">Демо-зоны на карте</span>
            <span class="map-store-marker" aria-hidden="true"></span>
            <a class="map-open-yandex" href="https://yandex.ru/maps/?ll=34.099398%2C44.973541&z=12" target="_blank" rel="noopener">Открыть Яндекс.Карты ↗</a>
            <div class="map-zone-readout"><strong>Схематичные границы</strong>Карта зафиксирована, поэтому зоны не «съезжают» при панорамировании.</div>
          </div>
          <div class="map-zone-legend" aria-label="Схематичные зоны доставки">
            <span><i class="map-zone-dot map-zone-dot--1"></i>Зона 1</span>
            <span><i class="map-zone-dot map-zone-dot--2"></i>Зона 2</span>
            <span><i class="map-zone-dot map-zone-dot--3"></i>Зона 3</span>
            <span>Без вымышленных минимальных сумм</span>
          </div>
          <div class="map-note">Сейчас это рабочая схема интерфейса: зоны нарисованы поверх зафиксированного фрагмента Яндекс Карты и поэтому остаются на своих местах. После подключения Yandex Maps JavaScript API заменим их географическими полигонами, которые будут корректно двигаться и масштабироваться вместе с картой.</div>
        </article>
        <aside class="conditions-card">
          <h3>Доставка и оплата</h3>
          <div class="condition"><b>Доставка курьером</b><span>Бесплатно от суммы по району. Ниже порога нужно добавить товары в заказ. Зона будет определяться по адресу после утверждения точных границ.</span></div>
          <div class="condition"><b>Самовывоз</b><span><?php echo esc_html( rollsbar_setting( 'address', 'Кечкеметская улица, 1' ) ); ?>. Условия самовывоза и возможные скидки уточняются у оператора при подтверждении заказа.</span></div>
          <div class="condition"><b>Оплата</b><span>На старте — при получении заказа. Онлайн-оплата будет подключаться отдельно при необходимости.</span></div>
          <div class="notice">Уважаемые клиенты, в связи с возможными сбоями связи, пожалуйста, будьте готовы оплатить заказ наличными при получении.</div>
        </aside>
      </div>
    </section>
