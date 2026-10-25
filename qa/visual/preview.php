<?php
// TEST ONLY: execute the real theme against the packaged catalog, without WP/DB.
define('ABSPATH', __DIR__);
$root = $argv[1];
$theme = $root . '/wordpress/wp-content/themes/rollsbar-theme';
$catalog = json_decode(file_get_contents($root . '/wordpress/data/catalog.json'), true);
function add_action(...$args) {}
function add_filter(...$args) {}
// Real read-only settings resolution, with optional in-memory QA overrides; no WP DB.
function get_option($key,$fallback=[]) { return $key==='rollsbar_settings' ? ($GLOBALS['b15_settings']??[]) : $fallback; }
function wp_parse_args($value,$defaults) { return array_merge($defaults,$value); }
require $root.'/wordpress/wp-content/plugins/rollsbar-core/includes/class-rollsbar-settings.php';
function esc_attr($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }
function esc_html($s) { return esc_attr($s); }
function esc_url($s) { return esc_attr($s); }
function esc_url_raw($s) { return $s; }
function wp_kses_post($s) { return $s; }
function wp_strip_all_tags($s) { return strip_tags($s); }
function wp_json_encode($s, $flags=0) { return json_encode($s, $flags | JSON_UNESCAPED_UNICODE); }
function home_url($s='/') { global $fixture_site_url;return rtrim($fixture_site_url??'http://localhost','/').$s; }
function wp_parse_url($url,$component=-1) { return parse_url($url,$component); }
function sanitize_title($value) { return rawurlencode(strtolower((string)$value)); }
function get_template_directory_uri() { return '/wordpress/wp-content/themes/rollsbar-theme'; }
function get_theme_file_uri($s) { return get_template_directory_uri().'/'.$s; }
function get_theme_mod($s) { return $GLOBALS['b15_theme_mods'][$s]??0; }
function wp_get_attachment_image_url($id,$size) { return '/fixture-media/'.$id.'.png'; }
function get_posts($args) { return []; }
function is_front_page() { return $GLOBALS['b15_front_page']??true; }
function has_custom_logo() { return false; }
function language_attributes() { echo 'lang="ru"'; }
function bloginfo($s) { echo 'UTF-8'; }
function body_class() { echo 'class="home"'; }
function wp_body_open() {}
function wp_head() { echo '<link rel="stylesheet" href="'.get_template_directory_uri().'/assets/css/app.css">'; }
function wp_footer() { echo '<script>window.rollsbarCart={url:"/fixture-cart",nonce:"local-fixture"}</script><script src="'.get_template_directory_uri().'/assets/js/app.js"></script>'; }
function get_template_part($s) { global $theme; require $theme.'/'.$s.'.php'; }
function get_header() { global $theme; require $theme.'/header.php'; }
function get_footer() { global $theme; require $theme.'/footer.php'; }
function wc_get_cart_url() { return '/cart/'; }
function wc_get_checkout_url() { return '/checkout/'; }
function WC() { global $fixture_cart,$fixture_session; return (object)['session'=>$fixture_session,'cart'=>$fixture_cart ?? new class { function get_cart_contents_count() { return 0; } function get_cart_subtotal() { return '0 ₽'; } }]; }
class FixtureSession { public array $data=[];function get($key,$default=null){return $this->data[$key]??$default;}function set($key,$value){$this->data[$key]=$value;} }
$fixture_session=new FixtureSession();
function wp_get_environment_type() { global $fixture_environment;return $fixture_environment??'local'; }
function wc_price($n) { return '<span class="woocommerce-Price-amount amount"><bdi>'.number_format((float)$n,0,',',' ').'&nbsp;<span class="woocommerce-Price-currencySymbol">₽</span></bdi></span>'; }
function wc_get_price_to_display($p) { return $p->get_price(); }
function wc_get_formatted_variation($p,...$args) { return $p->row['label']; }
function has_term($cat,$tax,$id) { global $fixture_products; foreach($fixture_products as $p) if($p->get_id()===$id) return $p->row['cat']===$cat; return false; }
class WooCommerce {}
define('ROLLSBAR_CORE_DIR',$root.'/wordpress/wp-content/plugins/rollsbar-core/');
require ROLLSBAR_CORE_DIR.'includes/class-rollsbar-catalog-importer.php';
function wc_get_product_id_by_sku($sku) { global $fixture_products;foreach($fixture_products as $p)if(($p->row['sku']??'')===$sku)return $p->id;return 0; }
function wc_get_product($id) {
 global $fixture_products;
 foreach($fixture_products as $p){if($p->get_id()===$id)return $p;if($p->is_type('variable'))foreach($p->get_available_variations() as $v)if($v->get_id()===$id)return $v;}
 return false;
}
class WC_Product {
 public function __construct(public array $row, public int $id) {}
 function get_id() { return $this->id; }
 function get_meta($k,...$a) { return $this->row['meta'][$k]??match($k) { '_rollsbar_source_id'=>$this->row['id'], '_rollsbar_source_image'=>$this->row['img']??'', '_rollsbar_options_json'=>isset($this->row['options'])?json_encode($this->row['options']):'', default=>'' }; }
 function is_type($s) { return in_array(isset($this->row['variants'])?'variable':'simple',(array)$s,true); }
 function get_status() { return 'publish'; }
 function get_name() { return $this->row['name']; }
 function get_short_description() { return $this->row['desc']; }
 function get_description() { return $this->row['desc']; }
 function get_permalink() { return '/product/'.$this->row['id'].'/'; }
 function add_to_cart_url() { return '/?add-to-cart='.$this->id; }
 function get_image_id() { return 0; }
 function get_price() { return $this->row['price']; }
 function is_purchasable() { return true; }
 function is_in_stock() { return $this->row['available']??true; }
 function get_stock_managed_by_id() { return $this->id; }
 function has_enough_stock($qty) { return $qty<=($this->row['stock']??PHP_INT_MAX); }
 function is_sold_individually() { return $this->row['sold_individually']??false; }
 function get_price_html() { return wc_price($this->get_price()); }
 function get_variation_price(...$a) { return min(array_column($this->row['variants'],'price')); }
 function get_available_variations(...$a) { return array_map(fn($v,$i)=>new FixtureVariation($v,$this->id*100+$i),$this->row['variants'],array_keys($this->row['variants'])); }
}
class WC_Product_Simple extends WC_Product {
 function __construct(){parent::__construct(['id'=>'','name'=>'','price'=>0,'desc'=>'','cat'=>''],0);}
 function set_sku($value){$this->row['sku']=$value;}
 function set_name($value){$this->row['name']=$value;}
 function set_status($value){$this->row['status']=$value;}
 function set_catalog_visibility($value){$this->row['visibility']=$value;}
 function get_catalog_visibility(){return $this->row['visibility']??'visible';}
 function set_regular_price($value){$this->row['price']=$value;}
 function set_stock_status($value){$this->row['available']=$value==='instock';}
 function update_meta_data($key,$value){$this->row['meta'][$key]=$value;if($key==='_rollsbar_source_id')$this->row['id']=$value;}
 function save(){global $fixture_products;if(!$this->id){$this->id=5000+count($fixture_products);$fixture_products[]=$this;}return $this->id;}
}
class FixtureVariation extends WC_Product {
 function is_type($s) { return in_array('variation',(array)$s,true); }
 function get_parent_id() { return intdiv($this->id,100); }
 function get_variation_attributes() { $attributes=RollsBar_Catalog_Importer::variation_attributes($this->row['label']);return array_combine(array_map(fn($key)=>'attribute_'.$key,array_keys($attributes)),array_values($attributes)); }
 function get_attributes() { return RollsBar_Catalog_Importer::variation_attributes($this->row['label']); }
 function variation_is_active() { return true; }
 function variation_is_visible() { return true; }
 function is_purchasable() { return true; }
 function is_in_stock() { return $this->row['available']??true; }
}
$products = array_map(fn($p,$i)=>new WC_Product($p,$i+1),$catalog['products'],array_keys($catalog['products']));
$fixture_products = $products;
RollsBar_Catalog_Importer::provision_upsells();
function wc_get_products($args) { global $fixture_products; return array_values(array_filter($fixture_products,fn($p)=>$p->row['cat']===$args['category'][0])); }
require $theme.'/functions.php';
require $theme.'/front-page.php';
