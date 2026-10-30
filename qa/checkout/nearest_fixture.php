<?php
require __DIR__.'/geography_fixture.php';
$cases=json_decode(file_get_contents(__DIR__.'/nearest-points.json'),true,512,JSON_THROW_ON_ERROR);
check_rule(hash_file('sha256',__DIR__.'/../../wordpress/wp-content/plugins/rollsbar-core/data/delivery-geography.json')===$cases['geography_sha256'],'independent oracle bound to unchanged geography');
$quadrants=array();
foreach($cases['cases'] as $case){
 $data=identity(array('street'=>'Молодёжная вне точной таблицы','geo_lon'=>$case['point'][0],'geo_lat'=>$case['point'][1]));
 $r=RollsBar_Delivery_Minimum::classify($data);
 check_rule($r['minimum']===$case['minimum']&&$r['basis']==='owner_nearest_zone'&&abs($r['distance_m']-$case['distance_m'])<=1,'nearest boundary matches independent Shapely '.$case['quadrant'].' '.json_encode($case['point']));
 foreach(array(1,2,3,4,5,null) as $qc){$data['qc_geo']=$qc;check_rule(null===RollsBar_Delivery_Minimum::classify($data)['minimum'],'nearest never promotes imprecise coordinates');}
 $quadrants[$case['quadrant']]=true;
}
check_rule(count($quadrants)===4,'nearest covers north/south/east/west, not store-centred rings');
$method=new ReflectionMethod(RollsBar_Delivery_Minimum::class,'polygon_distance');
$outer=array(array(0,0),array(4,0),array(4,4),array(0,4),array(0,0));$hole=array(array(1,1),array(3,1),array(3,3),array(1,3),array(1,1));
check_rule(0.0===$method->invoke(null,.5,.5,array($outer,$hole)),'polygon area has zero distance');
check_rule($method->invoke(null,2.,2.,array($outer,$hole))>100000,'hole uses its boundary rather than pretending containment');
echo "NEAREST_ZONE_FIXTURE_PASS\n";
