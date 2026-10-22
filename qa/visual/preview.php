<?php
// TEST ONLY: execute the real theme against the packaged catalog, without WP/DB.
define('ABSPATH', __DIR__);
$root = $argv[1];
$theme = $root . '/wordpress/wp-content/themes/rollsbar-theme';
$catalog = json_decode(file_get_contents($root . '/wordpress/data/catalog.json'), true);
function add_action(...$args) {}
function add_filter(...$args) {}
function esc_attr($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }
function esc_html($s) { return esc_attr($s); }
function esc_url($s) { return esc_attr($s); }
function esc_url_raw($s) { return $s; }
function wp_kses_post($s) { return $s; }
function wp_strip_all_tags($s) { return strip_tags($s); }
function wp_json_encode($s, $flags=0) { return json_encode($s, $flags | JSON_UNESCAPED_UNICODE); }
function home_url($s='/') { return $s; }
function get_template_directory_uri() { return '/wordpress/wp-content/themes/rollsbar-theme'; }
function get_theme_file_uri($s) { return get_template_directory_uri().'/'.$s; }
function get_theme_mod($s) { return 0; }
function get_posts($args) { return []; }
function is_front_page() { return true; }
function has_custom_logo() { return false; }
function language_attributes() { echo 'lang="ru"'; }
function bloginfo($s) { echo 'UTF-8'; }
function body_class() { echo 'class="home"'; }
function wp_body_open() {}
function wp_head() { echo '<link rel="stylesheet" href="'.get_template_directory_uri().'/assets/css/app.css">'; }
function wp_footer() { echo '<script src="'.get_template_directory_uri().'/assets/js/app.js"></script>'; }
function get_template_part($s) { global $theme; require $theme.'/'.$s.'.php'; }
function get_header() { global $theme; require $theme.'/header.php'; }
function get_footer() { global $theme; require $theme.'/footer.php'; }
function wc_get_cart_url() { return '/cart/'; }
function WC() { return (object)['cart'=>new class { function get_cart_contents_count() { return 0; } function get_cart_subtotal() { return '0 ₽'; } }]; }
function wc_price($n) { return '<span class="woocommerce-Price-amount amount"><bdi>'.number_format((float)$n,0,',',' ').'&nbsp;<span class="woocommerce-Price-currencySymbol">₽</span></bdi></span>'; }
function wc_get_price_to_display($p) { return $p->get_price(); }
function wc_get_formatted_variation($p,...$args) { return $p->row['label']; }
function has_term($cat,$tax,$id) { global $products; foreach($products as $p) if($p->get_id()===$id) return $p->row['cat']===$cat; return false; }
class WooCommerce {}
class RollsBar_Catalog_Importer { static function load_catalog() { global $catalog; return $catalog; } }
class WC_Product {
 public function __construct(public array $row, public int $id) {}
 function get_id() { return $this->id; }
 function get_meta($k,...$a) { return match($k) { '_rollsbar_source_id'=>$this->row['id'], '_rollsbar_source_image'=>$this->row['img']??'', '_rollsbar_options_json'=>isset($this->row['options'])?json_encode($this->row['options']):'', default=>'' }; }
 function is_type($s) { return $s===(isset($this->row['variants'])?'variable':'simple'); }
 function get_name() { return $this->row['name']; }
 function get_short_description() { return $this->row['desc']; }
 function get_description() { return $this->row['desc']; }
 function get_permalink() { return '/product/'.$this->row['id'].'/'; }
 function add_to_cart_url() { return '/?add-to-cart='.$this->id; }
 function get_image_id() { return 0; }
 function get_price() { return $this->row['price']; }
 function get_price_html() { return wc_price($this->get_price()); }
 function get_variation_price(...$a) { return min(array_column($this->row['variants'],'price')); }
 function get_available_variations(...$a) { return array_map(fn($v,$i)=>new FixtureVariation($v,$this->id*100+$i),$this->row['variants'],array_keys($this->row['variants'])); }
}
class FixtureVariation extends WC_Product {
 function get_attributes() { return ['fixture-choice'=>$this->row['label']]; }
 function variation_is_active() { return true; }
 function variation_is_visible() { return true; }
 function is_purchasable() { return true; }
 function is_in_stock() { return true; }
}
$products = array_map(fn($p,$i)=>new WC_Product($p,$i+1),$catalog['products'],array_keys($catalog['products']));
function wc_get_products($args) { global $products; return array_values(array_filter($products,fn($p)=>$p->row['cat']===$args['category'][0])); }
require $theme.'/functions.php';
require $theme.'/front-page.php';
