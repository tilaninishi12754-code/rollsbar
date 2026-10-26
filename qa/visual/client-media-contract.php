<?php
/** Offline WordPress/Woo CRUD fixture exercising the real importer and media sync. */
define('ABSPATH', sys_get_temp_dir() . '/rollsbar-client-media-fixture/');
define('ROLLSBAR_CORE_DIR', dirname(__DIR__, 2) . '/wordpress/wp-content/plugins/rollsbar-core/');
@mkdir(ABSPATH . 'wp-admin/includes', 0777, true);
file_put_contents(ABSPATH . 'wp-admin/includes/image.php', '<?php');
require ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-catalog-importer.php';
require ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-client-media.php';
$products=[]; $attachments=[]; $options=[]; $seq=0; $writes=0; $environment='local';
function check($ok, $why) { if (!$ok) throw new Exception($why); }
class WC_Product {
 public int $id=0; public array $data=['meta'=>[], 'image_id'=>0];
 function __construct($id=0) { $this->id=$id; }
 function __call($method,$args) {
  if(str_starts_with($method,'set_')) {$this->data[substr($method,4)]=$args[0];return;}
  if(str_starts_with($method,'get_')) return $this->data[substr($method,4)]??'';
  throw new Exception('Unsupported fixture method '.$method);
 }
 function get_meta($key,$single=true) {return $this->data['meta'][$key]??'';}
 function update_meta_data($key,$value) {$this->data['meta'][$key]=$value;}
 function get_type() {return $this instanceof WC_Product_Variation?'variation':($this instanceof WC_Product_Variable?'variable':'simple');}
 function is_type($type) {return $this->get_type()===$type;}
 function save() {global $products,$seq,$writes;if(!$this->id)$this->id=++$seq;$products[$this->id]=$this;++$writes;return $this->id;}
 function get_children() {global $products;return array_keys(array_filter($products,fn($p)=>$p->is_type('variation')&&$p->get_parent_id()===$this->id));}
}
class WC_Product_Simple extends WC_Product {}
class WC_Product_Variable extends WC_Product {static function sync($id) {}}
class WC_Product_Variation extends WC_Product {}
class WC_Product_Attribute {function __call($method,$args) {}}
function wc_get_product_id_by_sku($sku) {global $products;foreach($products as $id=>$p)if($p->get_sku()===$sku)return $id;return 0;}
function wc_get_product($id) {global $products;return $products[$id]??false;}
function wp_delete_post($id,$force=false) {global $products;unset($products[$id]);}
function sanitize_title($s) {return rawurlencode($s);}
function wp_strip_all_tags($s) {return strip_tags($s);}
function esc_url_raw($s) {return $s;}
function term_exists($s,$type) {return ['term_id'=>1];}
function is_wp_error($v) {return false;}
function wp_json_encode($v,$flags=0) {return json_encode($v,$flags);}
function wp_get_environment_type() {global $environment;return $environment;}
function home_url($s='/') {return 'https://staging.rollsbar.ru'.$s;}
function wp_parse_url($v,$part) {return parse_url($v,$part);}
function get_post_stati($args=[],$output='names') {return ['publish'=>'publish','draft'=>'draft','trash'=>'trash'];}
function get_posts($args) {
 global $products,$attachments;
 if($args['post_type']==='product')return array_keys(array_filter($products,fn($p)=>$p->get_type()!=='variation'&&$p->get_meta($args['meta_key'])===$args['meta_value']));
 return array_keys(array_filter($attachments,function($a)use($args){foreach($args['meta_query'] as $q)if(is_array($q)&&($a['meta'][$q['key']]??'')===$q['value'])return true;return false;}));
}
function get_post_meta($id,$key,$single=true) {global $attachments;return $attachments[$id]['meta'][$key]??'';}
function update_post_meta($id,$key,$v) {global $attachments;$attachments[$id]['meta'][$key]=$v;}
function get_attached_file($id) {global $attachments;return $attachments[$id]['file']??false;}
function get_post_mime_type($id) {global $attachments;return $attachments[$id]['post_mime_type']??'';}
function get_post_status($id) {global $attachments;return $attachments[$id]['post_status']??'';}
function wp_get_attachment_image_url($id,$size) {return isset($GLOBALS['attachments'][$id])?'https://staging.rollsbar.ru/uploads/'.basename(get_attached_file($id)):false;}
function wp_upload_bits($name,$unused,$bytes) {
 global $seq,$writes;$path=ABSPATH.'upload-'.(++$seq).'-'.$name;file_put_contents($path,$bytes);++$writes;return ['file'=>$path,'error'=>false];
}
function wp_insert_attachment($args,$file,$parent,$error) {global $attachments,$seq,$writes;$id=++$seq;$attachments[$id]=$args+['file'=>$file,'meta'=>$args['meta_input']];++$writes;return $id;}
function wp_get_attachment_metadata($id) {global $attachments;return $attachments[$id]['metadata']??false;}
function wp_generate_attachment_metadata($id,$file) {$d=getimagesize($file);return ['width'=>$d[0],'height'=>$d[1]];}
function wp_update_attachment_metadata($id,$meta) {global $attachments;$attachments[$id]['metadata']=$meta;}
function add_option($key,$value,$deprecated='',$autoload=false) {global $options;if(isset($options[$key]))return false;$options[$key]=$value;return true;}
function delete_option($key) {global $options;unset($options[$key]);}

$theme=file_get_contents(dirname(__DIR__,2).'/wordpress/wp-content/themes/rollsbar-theme/functions.php');
$start=strpos($theme,'function rollsbar_resolve_product_image(');
$end=strpos($theme,'function rollsbar_product_image_url(', $start);
eval(substr($theme,$start,$end-$start));
$manifest=json_decode(file_get_contents(RollsBar_Client_Media::root().'/manifest.json'),true);
$negative=0;
function fails($work,$label) {global $writes,$negative;$before=$writes;try{$work();}catch(Throwable $e){check($writes===$before,'Partial mutation on '.$label);++$negative;return;}throw new Exception('Expected safe rejection: '.$label);}
function invalid($change,$label) {global $manifest;$m=$manifest;$change($m);fails(fn()=>RollsBar_Client_Media::validate($m),$label);}
invalid(function(&$m){$m['schema_version']=999;},'manifest schema');
invalid(function(&$m){$m['sources'][0]['sha256']=str_repeat('0',64);},'archive provenance checksum');
invalid(function(&$m){$m['counts']['assets']=35;},'count mismatch');
invalid(function(&$m){$m['assets'][0]['file']='images/absent.webp';},'missing repo asset');
invalid(function(&$m){$m['assets'][0]['derived_sha256']=str_repeat('0',64);},'hash mismatch');
invalid(function(&$m){$m['assets'][1]['media_key']=$m['assets'][0]['media_key'];},'duplicate media key');
invalid(function(&$m){$m['assets'][0]['dimensions']=[1,1];},'dimensions');
invalid(function(&$m){$m['assets'][0]['derived_mime']='image/jpeg';},'MIME mismatch');
invalid(function(&$m){$m['assignments'][0]['source_id']='not-in-catalog';},'unknown source ID');
invalid(function(&$m){$m['assignments'][0]['source_id']='pizza-margarita';},'wrong existing source ID');
invalid(function(&$m){$m['assignments'][0]['source_id']=['baked-rice-shrimp','baked-rice-salmon'];},'multiple source IDs');
invalid(function(&$m){$m['assignments'][0]['photo_name']='unknown';},'unknown table photo');
invalid(function(&$m){$m['assignments'][1]['table_row']=$m['assignments'][0]['table_row'];},'duplicate assignment row');
invalid(function(&$m){foreach($m['assignments'] as &$r)if($r['product_name']==='Маргарита'&&$r['variant']==='50 см'){$r['media_key']='ogonek';$r['photo_name']='Огонек';}},'variable parent conflicting photos');
invalid(function(&$m){foreach($m['assignments'] as &$r)if($r['status']==='deferred_new_product_identity'){$r['source_id']='pizza-pepperoni';break;}},'invented deferred ID');
check(RollsBar_Client_Media::validate()['counts']['deferred_rows']===4,'Deferred records must be nonfatal');
fails(fn()=>RollsBar_Client_Media::sync(true),'missing Woo identity, all-assets preflight');
$environment='production';fails(fn()=>RollsBar_Client_Media::sync(),'production forbidden');$environment='local';

// A completely empty Woo/media fixture rebuilds from Git, without private ZIP/XLSX.
RollsBar_Catalog_Importer::import_all();
check(count($attachments)===36,'Fresh bootstrap should import exactly 36 unique assets');
check(count(array_filter($products,fn($p)=>$p->get_type()!=='variation'))===118,'Catalog contract');
check(count(array_filter($products,fn($p)=>$p->get_type()==='variation'))===26,'Variation contract');
$plan=RollsBar_Client_Media::plan();check(count($plan['woo_products'])===45,'45 products assigned');
$snapshot=serialize([$products,$attachments]);$before=$writes;
$dry=RollsBar_Client_Media::sync(true);$dry2=RollsBar_Client_Media::sync(true);
check($dry===$dry2&&$before===$writes&&serialize([$products,$attachments])===$snapshot,'Deterministic read-only dry run');
$again=RollsBar_Client_Media::sync();
check($again['created']===0&&$again['assigned']===0&&$again['reused']===36&&$again['unchanged']===45,'Second sync must be no-op');
$source_images=[];foreach($plan['woo_products'] as $sid=>$p)$source_images[$sid]=$p->get_image_id();
RollsBar_Catalog_Importer::import_all();
foreach($source_images as $sid=>$id){$p=wc_get_product(wc_get_product_id_by_sku(RollsBar_Catalog_Importer::sku_for($sid)));check($p->get_image_id()===$id,'Catalog import erased canonical client image');}
check(count($attachments)===36,'Catalog import duplicated media');

// An accidentally overwritten featured image must not defeat rendering precedence.
$p=reset($plan['woo_products']);$correct=$p->get_image_id();$p->set_image_id(999999);$p->update_meta_data('_rollsbar_source_image','https://avatars.mds.yandex.net/legacy');$p->save();
$render=rollsbar_resolve_product_image($p);
check($render['attachment_id']===$correct&&$render['source']==='client-canon','Legacy/incorrect featured image beat client canon');
$repair=RollsBar_Client_Media::sync();check($repair['created']===0&&$repair['assigned']===1&&$p->get_image_id()===$correct,'Accidental image overwrite not reconciled');

$id=array_key_first($attachments);$saved=$attachments[$id];
$file=get_attached_file($id);$bytes=file_get_contents($file);file_put_contents($file,'corrupt attachment bytes');
fails(fn()=>RollsBar_Client_Media::sync(),'actual attachment bytes differ from metadata');file_put_contents($file,$bytes);
$attachments[$id]['meta']['_rollsbar_client_media_sha256']=str_repeat('0',64);
fails(fn()=>RollsBar_Client_Media::sync(),'wrong existing attachment hash');$attachments[$id]=$saved;
$attachments[999999]=$saved;fails(fn()=>RollsBar_Client_Media::sync(),'duplicate attachment identity');unset($attachments[999999]);
$clone=clone $p;$clone->id=999998;$products[$clone->id]=$clone;fails(fn()=>RollsBar_Client_Media::sync(),'ambiguous Woo identity');unset($products[$clone->id]);
$saved_source=$p->get_meta('_rollsbar_source_id');$p->update_meta_data('_rollsbar_source_id','wrong-source');fails(fn()=>RollsBar_Client_Media::sync(),'wrong Woo source ID');$p->update_meta_data('_rollsbar_source_id',$saved_source);
$options['rollsbar_client_media_sync_lock']='running';fails(fn()=>RollsBar_Client_Media::sync(),'concurrent sync lock');unset($options['rollsbar_client_media_sync_lock']);

// Second independent empty state proves runtime has no dependency on source ZIPs.
$products=[];$attachments=[];RollsBar_Catalog_Importer::import_all();$rebuilt=RollsBar_Client_Media::sync();
check(count($attachments)===36&&$rebuilt['created']===0&&$rebuilt['unchanged']===45,'Fresh rebuild from committed canon failed');
echo json_encode(['status'=>'PASS','negative_cases'=>$negative,'assets'=>36,'resolved_rows'=>57,'resolved_source_ids'=>45,'deferred_rows'=>4,'second_sync'=>$again,'catalog_import_persistence'=>'PASS','fresh_rebuild_without_zips'=>'PASS','render_precedence'=>'PASS'],JSON_PRETTY_PRINT).PHP_EOL;
foreach(glob(ABSPATH.'upload-*') as $file)unlink($file);
