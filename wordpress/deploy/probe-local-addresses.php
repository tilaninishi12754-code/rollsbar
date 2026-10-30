<?php
// Read-only provider diagnosis: public fixture queries, no cart/order writes.
$method = new ReflectionMethod( RollsBar_Address_Suggestions::class, 'provider_request' );
foreach ( array( 'Приятное Свидание', 'Крым Приятное Свидание' ) as $query ) {
 foreach ( array( 'configured', 'region' ) as $scope ) {
  $rows = 'configured' === $scope ? $method->invoke( null, $query, 5 ) : wp_remote_post( 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address', array( 'timeout'=>8, 'headers'=>array('Content-Type'=>'application/json','Authorization'=>'Token '.ROLLSBAR_DADATA_API_KEY), 'body'=>wp_json_encode(array('query'=>$query,'count'=>5,'locations'=>array(array('region'=>'Крым')))) ) );
  if ( 'region' === $scope && ! is_wp_error($rows) ) { $rows = json_decode(wp_remote_retrieve_body($rows),true)['suggestions'] ?? array(); }
  $safe=array();
  if ( ! is_wp_error($rows) ) { foreach($rows as $row){ $safe[]=array('value'=>$row['value']??null,'identity'=>array_intersect_key($row['data']??array(),array_flip(array('region','area','city','settlement','settlement_fias_id'))),'local'=>RollsBar_Address_Suggestions::local_scope($row['data']??array())); } }
  echo wp_json_encode(array('scope'=>$scope,'query'=>$query,'error'=>is_wp_error($rows)?$rows->get_error_code():null,'rows'=>$safe),JSON_UNESCAPED_UNICODE)."\n";
 }
}
