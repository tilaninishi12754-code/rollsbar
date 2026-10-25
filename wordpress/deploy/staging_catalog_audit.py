#!/usr/bin/env python3
"""Read-only accepted staging catalog contract shared by deploy and maintenance.

The release marker is checked only when a caller explicitly supplies its expected
SHA. Deploy runs before marker persistence; maintenance retains its pinned guard.
No price amount is accepted as production business data by this contract.
"""
from __future__ import annotations

import json

DOMAIN = "staging.rollsbar.ru"
EXPECTED_UPSELLS = ("upsell-soy-sauce", "upsell-ginger", "upsell-wasabi")


def parse_audit(output: str) -> dict:
    for line in reversed(output.splitlines()):
        try:
            value = json.loads(line.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise RuntimeError("WooCommerce readback did not return its JSON proof")


def validate_catalog_audit(audit: dict, *, expected_deployed_sha: str | None = None) -> None:
    required = {
        "host": DOMAIN, "environment": "staging",
        "canonical_count": 118, "canonical_missing": 0, "canonical_duplicates": 0,
        "canonical_marked_upsell": 0, "canonical_wrong_status": 0,
        "variable_parents": 13, "variations": 26, "actual_variation_posts": 26,
        "variation_mismatches": 0, "blank_variation_attributes": 0,
        "upsell_count": 3, "upsell_duplicates": 0, "upsell_identity_mismatches": 0,
        "wrong_upsell_type": 0, "wrong_upsell_visibility": 0,
        "wrong_upsell_status": 0, "missing_provisional_provenance": 0,
        "published_total": 121, "unexpected_published_products": 0,
    }
    if expected_deployed_sha is not None:
        required["deployed_sha"] = expected_deployed_sha
    if any(audit.get(key) != value for key, value in required.items()):
        raise RuntimeError("Final WooCommerce readback failed one or more fixed state assertions")
    if sorted(audit.get("upsell_source_ids", ())) != sorted(EXPECTED_UPSELLS):
        raise RuntimeError("Global upsell-only source identity set differs from the exact intended trio")


AUDIT_PHP = r'''$catalog=RollsBar_Catalog_Importer::load_catalog()['products'];
$canonicalIds=[];$canonicalMissing=0;$canonicalDuplicates=0;$canonicalMarked=0;$canonicalWrongStatus=0;$parents=0;$variations=0;$variationMismatches=0;$blankAttrs=0;
$allIds=get_posts(['post_type'=>'product','post_status'=>array_values(get_post_stati([], 'names')),'numberposts'=>-1,'fields'=>'ids']);$sourceMap=[];foreach($allIds as $allId){$source=(string)get_post_meta($allId,'_rollsbar_source_id',true);if($source!=='')$sourceMap[$source][]=(int)$allId;}
foreach($catalog as $row){$source=(string)$row['id'];$id=wc_get_product_id_by_sku(RollsBar_Catalog_Importer::sku_for($source));if(!$id){$canonicalMissing++;continue;}$p=wc_get_product($id);if(!$p||$p->get_meta('_rollsbar_source_id',true)!==$source){$canonicalMissing++;continue;}if(count($sourceMap[$source]??[])!==1)$canonicalDuplicates++;if(isset($canonicalIds[$id]))$canonicalDuplicates++;$canonicalIds[$id]=true;if($p->get_status()!=='publish')$canonicalWrongStatus++;if($p->get_meta('_rollsbar_upsell_only',true)==='yes')$canonicalMarked++;if(!empty($row['variants'])){$parents++;foreach($row['variants'] as $variant){$variations++;$vid=wc_get_product_id_by_sku(RollsBar_Catalog_Importer::variation_sku($source,(string)$variant['label']));$v=$vid?wc_get_product($vid):false;$expected=RollsBar_Catalog_Importer::variation_attributes((string)$variant['label']);$key=(string)array_key_first($expected);$attrs=$v&&$v->is_type('variation')?$v->get_attributes():[];$actual=(string)($attrs[$key]??'');if(!$v||!$v->is_type('variation')||(int)$v->get_parent_id()!==(int)$id||$actual!==(string)$variant['label'])$variationMismatches++;if($actual===''||$actual==='any')$blankAttrs++;}}}
$upsellPosts=get_posts(['post_type'=>'product','post_status'=>array_values(get_post_stati([], 'names')),'numberposts'=>-1,'fields'=>'ids','meta_key'=>'_rollsbar_upsell_only','meta_value'=>'yes']);$sourceIds=[];$upsellDuplicates=0;$wrongType=0;$wrongVisibility=0;$wrongStatus=0;$missingProvenance=0;$identityMismatches=0;$seen=[];
foreach($upsellPosts as $pid){$p=wc_get_product($pid);$source=$p?(string)$p->get_meta('_rollsbar_source_id',true):'';$sourceIds[]=$source;if(isset($seen[$source]))$upsellDuplicates++;$seen[$source]=true;if(!$p||!$p->is_type('simple'))$wrongType++;if(!$p||$p->get_catalog_visibility()!=='hidden')$wrongVisibility++;if(!$p||$p->get_status()!=='publish')$wrongStatus++;$prov=$p?(string)$p->get_meta('_rollsbar_price_provenance',true):'';if(!str_contains($prov,'provisional')||!str_contains($prov,'client confirmation'))$missingProvenance++;}
$expectedUpsells=['upsell-soy-sauce','upsell-ginger','upsell-wasabi'];sort($sourceIds);$sortedExpected=$expectedUpsells;sort($sortedExpected);if($sourceIds!==$sortedExpected)$identityMismatches++;
$actualVariationPosts=count(get_posts(['post_type'=>'product_variation','post_status'=>array_values(get_post_stati([], 'names')),'numberposts'=>-1,'fields'=>'ids']));
$acceptedIds=array_fill_keys(array_merge(array_keys($canonicalIds),$upsellPosts),true);$unexpectedPublished=0;foreach($allIds as $allId){if(get_post_status($allId)==='publish'&&!isset($acceptedIds[$allId]))$unexpectedPublished++;}
$host=strtolower((string)wp_parse_url(home_url('/'),PHP_URL_HOST));$published=(int)(wp_count_posts('product')->publish??0);$marker=trim((string)file_get_contents(getenv('HOME').'/.rollsbar-staging-deployed-sha'));
echo wp_json_encode(['host'=>$host,'environment'=>wp_get_environment_type(),'deployed_sha'=>$marker,'canonical_count'=>count($canonicalIds),'canonical_missing'=>$canonicalMissing,'canonical_duplicates'=>$canonicalDuplicates,'canonical_marked_upsell'=>$canonicalMarked,'canonical_wrong_status'=>$canonicalWrongStatus,'variable_parents'=>$parents,'variations'=>$variations,'actual_variation_posts'=>$actualVariationPosts,'variation_mismatches'=>$variationMismatches,'blank_variation_attributes'=>$blankAttrs,'upsell_count'=>count($upsellPosts),'upsell_source_ids'=>$sourceIds,'upsell_duplicates'=>$upsellDuplicates,'upsell_identity_mismatches'=>$identityMismatches,'wrong_upsell_type'=>$wrongType,'wrong_upsell_visibility'=>$wrongVisibility,'wrong_upsell_status'=>$wrongStatus,'missing_provisional_provenance'=>$missingProvenance,'published_total'=>$published,'unexpected_published_products'=>$unexpectedPublished]);'''
