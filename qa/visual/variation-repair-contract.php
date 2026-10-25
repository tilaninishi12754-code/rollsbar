<?php
// Deterministic Woo CRUD contract for the narrow in-place variable attribute repair.
define('ABSPATH', __DIR__);
define('ROLLSBAR_CORE_DIR', dirname(__DIR__, 2) . '/wordpress/wp-content/plugins/rollsbar-core/');
function sanitize_title($value) { return rawurlencode(strtolower((string)$value)); }
require ROLLSBAR_CORE_DIR . 'includes/class-rollsbar-catalog-importer.php';
$catalog = json_decode(file_get_contents(dirname(__DIR__, 2) . '/wordpress/data/catalog.json'), true);
$store = [];
class RepairFixtureProduct {
 public function __construct(public int $id, public string $source_id) {}
 function get_meta($key, $single = true) { return $key === '_rollsbar_source_id' ? $this->source_id : ''; }
}
class WC_Product_Variable extends RepairFixtureProduct {}
class WC_Product_Variation extends RepairFixtureProduct {
 public array $attributes = [];
 public int $parent_id;
 function __construct(int $id, string $source_id, int $parent_id) { parent::__construct($id, $source_id); $this->parent_id=$parent_id; }
 function get_parent_id() { return $this->parent_id; }
 function get_attributes() { return $this->attributes; }
 function set_attributes($attributes) { $this->attributes=$attributes; }
 function save() { return $this->id; }
}
foreach ($catalog['products'] as $row) {
 if (empty($row['variants'])) { continue; }
 $parent_id = count($store) + 1;
 $parent = new WC_Product_Variable($parent_id, (string)$row['id']);
 $store[RollsBar_Catalog_Importer::sku_for((string)$row['id'])] = $parent;
 foreach ($row['variants'] as $variant) {
  $id = count($store) + 1001;
  $child = new WC_Product_Variation($id, (string)$row['id'], $parent_id);
  $child->source_id = (string)$row['id'];
  $store[RollsBar_Catalog_Importer::variation_sku((string)$row['id'], (string)$variant['label'])] = $child;
 }
}
function wc_get_product_id_by_sku($sku) { global $store; return isset($store[$sku]) ? $store[$sku]->id : 0; }
function wc_get_product($id) { global $store; foreach ($store as $product) { if ($product->id === $id) { return $product; } } return false; }
$dry = RollsBar_Catalog_Importer::repair_variable_attributes(true);
if ($dry !== ['parents'=>13,'variations'=>26,'updated'=>26,'dry_run'=>true]) { throw new Exception('Repair dry-run cardinalities or detection failed'); }
foreach ($store as $product) { if ($product instanceof WC_Product_Variation && $product->attributes !== []) { throw new Exception('Dry run mutated Woo attributes'); } }
$result = RollsBar_Catalog_Importer::repair_variable_attributes();
if ($result !== ['parents'=>13,'variations'=>26,'updated'=>26,'dry_run'=>false]) { throw new Exception('Repair cardinalities failed'); }
foreach ($catalog['products'] as $row) {
 if (empty($row['variants'])) { continue; }
 foreach ($row['variants'] as $variant) {
  $child=$store[RollsBar_Catalog_Importer::variation_sku((string)$row['id'], (string)$variant['label'])];
  if ($child->attributes !== RollsBar_Catalog_Importer::variation_attributes((string)$variant['label'])) { throw new Exception('Repair emitted a blank or non-canonical Woo attribute'); }
 }
}
$again=RollsBar_Catalog_Importer::repair_variable_attributes();
if ($again['updated'] !== 0 || $again['parents'] !== 13 || $again['variations'] !== 26) { throw new Exception('Repair is not idempotent'); }
echo json_encode(['pass'=>true,'canonical_variable_parents'=>$result['parents'],'canonical_variations'=>$result['variations'],'updated'=>$result['updated'],'repeat_updated'=>$again['updated']], JSON_PRETTY_PRINT) . PHP_EOL;
