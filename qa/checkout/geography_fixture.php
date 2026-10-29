<?php
require __DIR__ . '/delivery_rules_fixture.php';
$cases=json_decode(file_get_contents(__DIR__.'/geography-points.json'),true,512,JSON_THROW_ON_ERROR);
foreach($cases as $minimum=>$points){
 foreach($points as $point){
  $data=identity(array('street'=>'Улица вне точной таблицы','geo_lon'=>$point[0],'geo_lat'=>$point[1]));
  $result=RollsBar_Delivery_Minimum::classify($data);
  check_rule('resolved'===$result['status']&&(int)$minimum===$result['minimum']&&true===$result['provisional']&&'owner_geographic_advisory'===$result['basis'],'independent geographic point '.$minimum.' '.json_encode($point));
  foreach(array(null,1,2,3,4,5) as $qc){$low=$data;$low['qc_geo']=$qc;check_rule(null===RollsBar_Delivery_Minimum::classify($low)['minimum'],'no polygon assignment with qc_geo='.var_export($qc,true));}
  $invalid=$data;$invalid['house_fias_id']='';check_rule(null===RollsBar_Delivery_Minimum::classify($invalid)['minimum'],'no polygon assignment without verified house');
  $GLOBALS['rb_fixture_environment']='production';check_rule(null===RollsBar_Delivery_Minimum::classify($data)['minimum'],'geographic fallback disabled outside staging');unset($GLOBALS['rb_fixture_environment']);
 }
}
$methods=new ReflectionMethod(RollsBar_Delivery_Minimum::class,'in_ring');
$ring=array(array(0,0),array(2,0),array(2,2),array(0,2),array(0,0));
check_rule($methods->invoke(null,1.,1.,$ring),'ring inside');check_rule(!$methods->invoke(null,3.,1.,$ring),'ring outside');check_rule($methods->invoke(null,0.,1.,$ring),'ring edge');
check_rule(null===RollsBar_Delivery_Minimum::classify(identity(array('street'=>'Вне таблицы','geo_lon'=>'nan','geo_lat'=>44.95)))['minimum'],'invalid coordinate rejected');
$known=RollsBar_Delivery_Minimum::classify(identity(array('geo_lon'=>$point[0],'geo_lat'=>$point[1])));
check_rule(1200===$known['minimum']&&'fias_identity'===$known['basis'],'exact table identity precedes geographic background');
echo "DELIVERY_GEOGRAPHY_FIXTURE_PASS\n";
