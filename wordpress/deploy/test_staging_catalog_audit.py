"""Offline regressions execute the shared PHP audit against an isolated Woo adapter."""
import ast
import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import staging_catalog_audit as contract
import maintain_staging_catalog as maintenance

ROOT = Path(__file__).resolve().parents[2]
PHP = str(ROOT / 'qa/.runtime/php/php.exe') if os.name == 'nt' else 'php'
OLD_SHA = maintenance.EXPECTED_SHA
ADAPTER = r'''
class RollsBar_Catalog_Importer {
 static function load_catalog(){global $fixture;return ['products'=>$fixture['catalog']];}
 static function sku_for($s){return $s;}
 static function variation_sku($s,$v){return $s.':'.$v;}
 static function variation_attributes($v){return ['option'=>$v];}
}
class Product {
 function __construct(public $data){}
 function get_meta($k,$single=true){return $this->data['meta'][$k]??'';}
 function get_status(){return $this->data['status'];}
 function is_type($t){return $this->data['type']===$t;}
 function get_catalog_visibility(){return $this->data['visibility'];}
 function get_parent_id(){return $this->data['parent']??0;}
 function get_attributes(){return $this->data['attrs']??[];}
}
function get_post_stati(...$args){return ['publish','draft','trash','private'];}
function get_posts($args){global $fixture;$ids=[];foreach($fixture['posts'] as $id=>$p){if($p['post_type']!==$args['post_type'])continue;if(isset($args['meta_key'])&&($p['meta'][$args['meta_key']]??'')!==$args['meta_value'])continue;$ids[]=(int)$id;}return $ids;}
function wc_get_product_id_by_sku($sku){global $fixture;foreach($fixture['posts'] as $id=>$p){if($p['sku']===$sku)return (int)$id;}return 0;}
function wc_get_product($id){global $fixture;return isset($fixture['posts'][$id])?new Product($fixture['posts'][$id]):false;}
function get_post_meta($id,$key,$single){return wc_get_product($id)->get_meta($key);}
function get_post_status($id){return wc_get_product($id)->get_status();}
function wp_parse_url($url,$part){return parse_url($url,$part);}
function home_url($path){return 'https://staging.rollsbar.ru/';}
function wp_get_environment_type(){return 'staging';}
function wp_count_posts($type){global $fixture;return (object)['publish'=>count(array_filter($fixture['posts'],fn($p)=>$p['post_type']===$type&&$p['status']==='publish'))];}
function wp_json_encode($value){return json_encode($value);}
'''


def fixture():
    catalog = json.loads((ROOT / 'wordpress/data/catalog.json').read_text(encoding='utf-8'))['products']
    posts = {}
    for row in catalog:
        pid = len(posts)+1
        posts[pid] = product(row['id'], type='variable' if row.get('variants') else 'simple')
        for variant in row.get('variants', []):
            posts[len(posts)+1] = product(row['id']+':'+variant['label'], type='variation',
                                         post_type='product_variation', parent=pid,
                                         attrs={'option':variant['label']})
    for source in contract.EXPECTED_UPSELLS:
        posts[len(posts)+1] = product(source, visibility='hidden', meta={
            '_rollsbar_source_id':source, '_rollsbar_upsell_only':'yes',
            '_rollsbar_price_provenance':'provisional; client confirmation required before production'})
    return {'catalog':catalog, 'posts':posts}


def product(source, **kwargs):
    return dict({'sku':source, 'post_type':'product', 'status':'publish', 'type':'simple',
                 'visibility':'visible', 'meta':{'_rollsbar_source_id':source}}, **kwargs)


class DeployCatalogContract(unittest.TestCase):
    def audit(self, data):
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        with tempfile.TemporaryDirectory() as home:
            (Path(home)/'.rollsbar-staging-deployed-sha').write_text(OLD_SHA)
            script = "<?php\n$fixture=json_decode(base64_decode('"+encoded+"'),true);\n"+ADAPTER+contract.AUDIT_PHP
            result = subprocess.run([PHP], input=script, text=True, encoding='utf-8',
                                    capture_output=True, env={**os.environ,'HOME':home}, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return contract.parse_audit(result.stdout)

    def test_accepted_state_and_old_failure(self):
        audit = self.audit(fixture())
        self.assertEqual((audit['canonical_count'], audit['upsell_count'], audit['published_total']), (118,3,121))
        old = subprocess.check_output(['git','show','a7e33f7dfa1668c193e8e49924e11bf2b0c09eb2:wordpress/deploy/deploy_staging_wordpress.py'],cwd=ROOT,text=True)
        self.assertIn('EXPECTED_STAGING_PRODUCTS = 118', old)
        self.assertIn('[[ "$product_count" == "{EXPECTED_STAGING_PRODUCTS}" ]]', old)
        with self.assertRaises(AssertionError):
            assert audit['published_total'] == 118
        contract.validate_catalog_audit(audit)
        maintenance.validate_audit(audit)
        with self.assertRaises(RuntimeError):
            contract.validate_catalog_audit(audit, expected_deployed_sha='f'*40)
        # Deployment accepts the catalog while the previous verified marker persists.
        self.assertEqual(audit['deployed_sha'], OLD_SHA)
        self.assertIs(maintenance.AUDIT_PHP, contract.AUDIT_PHP)

    def test_all_required_negative_payloads_even_at_total_121(self):
        accepted = self.audit(fixture())
        cases = [('canonical_count',117),('canonical_count',119),('canonical_missing',1),
                 ('canonical_duplicates',1),('canonical_marked_upsell',1),('canonical_wrong_status',1),
                 ('variation_mismatches',1),('blank_variation_attributes',1),('upsell_count',2),
                 ('upsell_count',4),('upsell_identity_mismatches',1),('upsell_duplicates',1),
                 ('wrong_upsell_visibility',1),('wrong_upsell_type',1),('wrong_upsell_status',1),
                 ('missing_provisional_provenance',1),('published_total',120),('published_total',122),
                 ('unexpected_published_products',1),('actual_variation_posts',25),
                 ('actual_variation_posts',27),('variable_parents',12),('variations',25)]
        for key,value in cases:
            with self.subTest(key=key,value=value), self.assertRaises(RuntimeError):
                contract.validate_catalog_audit(dict(accepted, **{key:value}))
        for sources in [list(contract.EXPECTED_UPSELLS[:2])+['wrong-source'],
                        list(contract.EXPECTED_UPSELLS)+[contract.EXPECTED_UPSELLS[0]]]:
            with self.subTest(sources=sources), self.assertRaises(RuntimeError):
                contract.validate_catalog_audit(dict(accepted,upsell_source_ids=sources))

    def test_real_readback_detects_corruption(self):
        base = fixture()
        canonical = next(i for i,p in base['posts'].items() if p['post_type']=='product')
        variation = next(i for i,p in base['posts'].items() if p['type']=='variation')
        upsell = next(i for i,p in base['posts'].items() if p['meta'].get('_rollsbar_upsell_only')=='yes')
        cases = {}
        def change(name):
            cases[name] = copy.deepcopy(base)
            return cases[name]['posts']
        change('missing canonical plus unrelated, total 121')[canonical] = product('unrelated')
        posts=change('duplicate canonical');posts[999]=copy.deepcopy(posts[canonical])
        change('canonical marked upsell')[canonical]['meta']['_rollsbar_upsell_only']='yes'
        change('canonical draft')[canonical]['status']='draft'
        del change('missing variation')[variation]
        change('blank variation')[variation]['attrs']={'option':''}
        change('wrong variation parent')[variation]['parent']=999
        del change('two upsells')[upsell]
        change('four upsells')[999]=product('fourth',meta={'_rollsbar_upsell_only':'yes'})
        change('wrong upsell identity')[upsell]['meta']['_rollsbar_source_id']='wrong'
        posts=change('duplicate upsell');posts[999]=copy.deepcopy(posts[upsell])
        change('visible upsell')[upsell]['visibility']='visible'
        change('variable upsell')[upsell]['type']='variable'
        change('draft upsell')[upsell]['status']='draft'
        change('missing provenance')[upsell]['meta'].pop('_rollsbar_price_provenance')
        change('unrelated fourth hidden product')[999]=product('unrelated',visibility='hidden')
        posts=change('random 121 products');cases['random 121 products']['posts']={i:product('random-'+str(i)) for i in range(1,122)}
        for name,data in cases.items():
            with self.subTest(case=name):
                audit=self.audit(data)
                with self.assertRaises(RuntimeError):
                    contract.validate_catalog_audit(audit)
                print('REJECTED '+name)
        audit=self.audit(cases['missing canonical plus unrelated, total 121'])
        self.assertEqual(audit['published_total'],121)
        self.assertEqual(audit['unexpected_published_products'],1)

    def test_extraction_parity_and_generated_shell_syntax(self):
        old = subprocess.check_output(['git','show','a7e33f7dfa1668c193e8e49924e11bf2b0c09eb2:wordpress/deploy/maintain_staging_catalog.py'], cwd=ROOT, text=True)
        original = next(n.value.value for n in ast.parse(old).body
                        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='AUDIT_PHP' for t in n.targets))
        added = "$acceptedIds=array_fill_keys(array_merge(array_keys($canonicalIds),$upsellPosts),true);$unexpectedPublished=0;foreach($allIds as $allId){if(get_post_status($allId)==='publish'&&!isset($acceptedIds[$allId]))$unexpectedPublished++;}\n"
        self.assertEqual(contract.AUDIT_PHP.replace(added,'').replace(",'unexpected_published_products'=>$unexpectedPublished",''), original)
        source=(ROOT/'wordpress/deploy/deploy_staging_wordpress.py').read_text(encoding='utf-8')
        remote=next(n.value for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Assign)
                    and any(isinstance(t,ast.Name) and t.id=='remote' for t in n.targets))
        import shlex
        script=eval(compile(ast.Expression(remote),'<offline deploy shell>','eval'), {
            'DOMAIN':contract.DOMAIN, 'RUNTIME_FILE':'.fixture-runtime.env',
            'REPO':'https://example.invalid/offline.git', 'DEPLOY_SHA':'f'*40,
            'EXPECTED_WORDPRESS_VERSION':'7.1.3', 'EXPECTED_WOOCOMMERCE_VERSION':'11.1.2',
            'TELEGRAM_EXPECTED':'yes', 'AUDIT_PHP':contract.AUDIT_PHP,'shell_quote':shlex.quote})
        bash=r'C:/programm/Git/bin/bash.exe' if os.name=='nt' else 'bash'
        result=subprocess.run([bash,'-n'], input=script, text=True,encoding='utf-8',capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_deploy_sequence_and_preserved_guards(self):
        source=(ROOT/'wordpress/deploy/deploy_staging_wordpress.py').read_text(encoding='utf-8')
        ordered=['source "$PROJECT_ROOT/wordpress/deploy/prepare-s1-r2-backup.sh"',
                 'bash "$PROJECT_ROOT/wordpress/deploy/preflight.sh"',
                 'bash "$PROJECT_ROOT/wordpress/deploy/bootstrap-staging.sh"',
                 'bash "$PROJECT_ROOT/wordpress/deploy/repair-s1-r2.sh"',
                 'core verify-checksums', 'wp --path="$WP_PATH" eval {shell_quote(AUDIT_PHP)}',
                 'audit = parse_audit(exec_checked(', 'validate_catalog_audit(audit)',
                 'print("STAGING WORDPRESS DEPLOY PASS")']
        positions=[source.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('EXPECTED_STAGING_PRODUCTS',source)
        self.assertNotIn('expected_deployed_sha=',source)
        self.assertNotIn('mark_staging_deployed_sha',source)
        for guard in ['EXPECTED_WORDPRESS_VERSION = "7.1.3"','EXPECTED_WOOCOMMERCE_VERSION = "11.1.2"',
                      '[[ "$theme_status" == "active" ]]','[[ "$core_status" == "active" ]]',
                      '[[ "$blog_public" == "0" ]]','[[ "$dadata_configured" == "yes" ]]',
                      '[[ "$wp_config_mode" == "640" ]]','[[ "$telegram_configured" == "yes" ]]']:
            self.assertIn(guard,source)
        workflow=(ROOT/'.github/workflows/deploy-reg-ru-staging-wordpress.yml').read_text()
        stages=['run: python3 wordpress/deploy/'+name+'.py' for name in
                ['deploy_staging_wordpress','provision_staging_seo','harden_staging_http','audit_staging_seo','mark_staging_deployed_sha']]
        self.assertEqual([workflow.index(s) for s in stages], sorted(workflow.index(s) for s in stages))
        wrapper=(ROOT/'wordpress/deploy/prepare-s1-r2-backup.sh').read_text()
        self.assertIn('ROLLSBAR_BACKUP_RETENTION=6',wrapper)
        self.assertIn('ROLLSBAR_PRESERVE_BACKUP_SNAPSHOT=20261023T215945Z',wrapper)
        # Marker now uses the same accepted catalog guard; backup bytes stay fixed.
        for name in ['backup-staging.sh','prepare-s1-r2-backup.sh']:
            self.assertEqual((ROOT/'wordpress/deploy'/name).read_bytes().replace(b'\r\n', b'\n'),subprocess.check_output(['git','show','a7e33f7dfa1668c193e8e49924e11bf2b0c09eb2:wordpress/deploy/'+name],cwd=ROOT))


if __name__ == '__main__':
    unittest.main(verbosity=2)
