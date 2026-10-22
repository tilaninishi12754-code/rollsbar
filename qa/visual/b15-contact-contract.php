<?php
// Deterministic real settings + real template mapping. No WP process/database.
ob_start(); require __DIR__.'/preview.php'; $default=ob_get_clean();
$checks=0;
function b15check($ok,$label){global $checks;if(!$ok)throw new Exception($label);$checks++;}
b15check(str_contains($default,'tel:+79786882288'),'Default phone');
b15check(str_contains($default,'Симферополь, Кечкеметская улица, 1.'),'Default address');
b15check(str_contains($default,'https://vk.ru/rollsbar82'),'Default VK');
b15check(str_contains($default,'https://telegram.me/rollsbar82'),'Default Telegram');
$GLOBALS['b15_settings']=['phone_display'=>'+7 999 123-45-67','phone_href'=>'+79991234567','city'=>'Тестовый город','address'=>'Очень длинная тестовая улица, дом 123, корпус 4','vk_url'=>'https://vk.ru/test_b15','telegram_url'=>'https://t.me/test_b15'];
ob_start();require $theme.'/footer.php';$custom=ob_get_clean();
foreach(['tel:+79991234567','+7 999 123-45-67','+7 (999) 123-45-67','Тестовый город, Очень длинная тестовая улица, дом 123, корпус 4.','https://vk.ru/test_b15','https://t.me/test_b15'] as $value)b15check(str_contains($custom,$value),'Mapped '.$value);
foreach(['tel:+79786882288','https://vk.ru/rollsbar82','https://telegram.me/rollsbar82'] as $old)b15check(!str_contains($custom,$old),'No stale default '.$old);
b15check(str_contains($custom,'в городе Тестовый город'),'Footer description uses edited city');
b15check(!str_contains($custom,'Симферополю'),'No stale city in description');
$GLOBALS['b15_settings']=['city'=>'Город <script>','address'=>'Улица & дом','vk_url'=>'','telegram_url'=>''];
ob_start();require $theme.'/footer.php';$empty=ob_get_clean();
b15check(str_contains($empty,'Город &lt;script&gt;, Улица &amp; дом.'),'Escaped settings');
b15check(!str_contains($empty,'target="_blank"'),'Blank social settings omit links');
b15check(str_contains($empty,'tel:+79786990399'),'Approved second phone preserved');
$GLOBALS['b15_front_page']=false;
$GLOBALS['b15_theme_mods']=['custom_logo'=>42];
ob_start();require $theme.'/footer.php';$internal=ob_get_clean();
b15check(!str_contains($internal,'id="contacts"'),'Contacts only on public homepage');
b15check(str_contains($internal,'href="/#top"'),'Internal page logo destination');
b15check(str_contains($internal,'href="/#sets"'),'Internal page menu destination');
b15check(str_contains($internal,'src="/fixture-media/42.png"'),'Editable WP custom logo');
echo json_encode(['pass'=>true,'assertions'=>$checks,'database'=>'none','source'=>'RollsBar_Settings::all/get → rollsbar_setting → actual footer.php'],JSON_UNESCAPED_UNICODE).PHP_EOL;
