<?php


$today = date('m/d/Y');

$date = new DateTime($today);
$weekNum = $date->format("W");
if( date('N') =="1" ){
	$weekNum = $weekNum - 1;
}

//dow for strtotime should be on Tuesday
if ($today > date('m/d/Y', strtotime("12/24/2019"))){$curweek='Week17';}
else if ($today > date('m/d/Y', strtotime("12/17/2019"))){$curweek='Week16';}
else if ($today > date('m/d/Y', strtotime("12/10/2019"))){$curweek='Week15';}
else if ($today > date('m/d/Y', strtotime("12/03/2019"))){$curweek='Week14';}
else if ($today > date('m/d/Y', strtotime("11/26/2019"))){$curweek='Week13';}
else if ($today > date('m/d/Y', strtotime("11/19/2019"))){$curweek='Week12';}
else if ($today > date('m/d/Y', strtotime("11/12/2019"))){$curweek='Week11';}
else if ($today > date('m/d/Y', strtotime("11/05/2019"))){$curweek='Week10';}
else if ($today > date('m/d/Y', strtotime("10/29/2019"))){$curweek='Week9';}
else if ($today > date('m/d/Y', strtotime("10/22/2019"))){$curweek='Week8';}
else if ($today > date('m/d/Y', strtotime("10/15/2019"))){$curweek='Week7';}
else if ($today > date('m/d/Y', strtotime("10/08/2019"))){$curweek='Week6';}
else if ($today > date('m/d/Y', strtotime("10/01/2019"))){$curweek='Week5';}
else if ($today > date('m/d/Y', strtotime("09/24/2019"))){$curweek='Week4';}
else if ($today > date('m/d/Y', strtotime("09/17/2019"))){$curweek='Week3';}
else if ($today > date('m/d/Y', strtotime("09/10/2019"))){$curweek='Week2';}
else if ($today > date('m/d/Y', strtotime("08/01/2019"))){$curweek='Week1';}
else $curweek='Offseason';


if ($curweek=='Week1'){ 
	$prevweekno=1;
}
//Before Week10, we need to only strip off last char to subtract 1.  Once it hits Week10, we need to strip off last 2 char to then subtract 1
//else if ( $curweek=='Week10' or $curweek=='Week11' or $curweek=='Week12' or $curweek=='Week13' or $curweek=='Week14' or $curweek='Week15' or $curweek='Week16' or $curweek='Week17' ){
else if ( substr($curweek,-2) >= 10 ){
	$prevweekno = substr($curweek,-2)-1;
}
else {
	$prevweekno = substr($curweek,-1)-1;
}

$prevweek = "Week" . $prevweekno;

?>
