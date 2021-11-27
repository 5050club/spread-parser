<?php

include "curweek.php";
include "dbcnx.php";

/*set log location and date*/
$path = "logs/";
shell_exec("touch $path$curweek.script.log");
$outputfile = "$path" . "$curweek" . ".script.log";
$now = date(DATE_RFC822) . "\n";


/**************************************************************************************
/* Fucntion for cron job.  we dont want spread updating after kickoff and before tues*/
/**************************************************************************************/ 
function execution_check($file, $curweek) {

  $dow=date('N');
  $hod=date('G');
  $moh=date('i');
  $now = date(DATE_RFC822) . "\n";

  if($curweek == "Week1") {
	return true;
  }
            //dow - 1 is Monday
  #else if( ($dow=="1" /*and $hod>=16 /*and $moh>1*/) or ($dow=="2") or ($dow=="4" and $hod>=16 /*and $moh>1*/) or ($dow=="7" and $hod>=11 /*and $moh>1*/) ) {
  else if($dow=="1") {
	if(!is_writable($file)) {
                echo "File is not writable, check permissions.\n";
        }
        else {
                $logfile = fopen($file,"a");

                if(!$logfile) {
                        echo "Error writing to the output file.\n";
                }
                else {
                        $warning = "Its either Monday, Tuesday, after 4pm on Thursday, or after 9am on Sunday.  Therefore the script did not update the spreads.\n\n";
			fwrite($logfile,$now);
			fwrite($logfile,$warning);
                        fclose($logfile);
                }
        }
	return false;

  }   /*closes if statement*/
  else  return true;
}
/**************************************************************************************
// Fucntion for converting shorthand team name to official team name
/**************************************************************************************/ 
function properTeam($rawteam) {

        $newteam = "";
        switch($rawteam){
          case "ARI CARDINALS":$newteam="Arizona Cardinals";break;
          case "ATL FALCONS":$newteam="Atlanta Falcons";break;
          case "BAL RAVENS":$newteam="Baltimore Ravens";break;
          case "BUF BILLS":$newteam="Buffalo Bills";break;
          case "CAR PANTHERS":$newteam="Carolina Panthers";break;
          case "CHI BEARS":$newteam="Chicago Bears";break;
          case "CIN BENGALS":$newteam="Cincinnati Bengals";break;
          case "CLE BROWNS":$newteam="Cleveland Browns";break;
          case "DAL COWBOYS":$newteam="Dallas Cowboys";break;
          case "DEN BRONCOS":$newteam="Denver Broncos";break;
          case "DET LIONS":$newteam="Detroit Lions";break;
          case "GB PACKERS":$newteam="Green Bay Packers";break;
          case "HOU TEXANS":$newteam="Houston Texans";break;
          case "IND COLTS":$newteam="Indianapolis Colts";break;
          case "JAX JAGUARS":$newteam="Jacksonville Jaguars";break;
          case "KC CHIEFS":$newteam="Kansas City Chiefs";break;
          case "LA RAMS":$newteam="Los Angeles Rams";break;
          case "MIA DOLPHINS":$newteam="Miami Dolphins";break;
          case "MIN VIKINGS":$newteam="Minnesota Vikings";break;
          case "NE PATRIOTS":$newteam="New England Patriots";break;
          case "NO SAINTS":$newteam="New Orleans Saints";break;
          case "NY GIANTS":$newteam="New York Giants";break;
          case "NY JETS":$newteam="New York Jets";break;
          case "OAK RAIDERS":$newteam="Oakland Raiders";break;
          case "PHI EAGLES":$newteam="Philadelphia Eagles";break;
          case "PIT STEELERS":$newteam="Pittsburgh Steelers";break;
          case "SDG CHARGERS":$newteam="San Diego Chargers";break;
          case "SEA SEAHAWKS":$newteam="Seattle Seahawks";break;
          case "SFO 49ERS":$newteam="San Francisco 49ers";break;
          case "TB BUCCANEERS":$newteam="Tampa Bay Buccaneers";break;
          case "TEN TITANS":$newteam="Tennessee Titans";break;
          case "WAS REDSKINS":$newteam="Washington Redskins";break;
          default:$newteam=$rawteam;
        }

        return $newteam;
}

/*******************************************************************************************
/*******************************************************************************************
/*******************************************************************************************


/*checks if we want to update spreads or not (for cron job) */

if (!execution_check($outputfile, $curweek)) {
        echo "stop here";
        exit(0);
}



/*******************************************************************************************
/*******************************************************************************************
Where we download xml spread from pinnacle, parse it, update db
/*******************************************************************************************

//https://the-odds-api.com/
// https://www.mybookie.ag/odds.xml
// lines.betcris.com
//get current cris xml feed and write it to file*/

# uncomment after testing
#shell_exec("curl -q \"https://www.mybookie.ag/odds.xml\" -o spreadfeed.xml");

//create array that stores current games
$xml=simplexml_load_file("spreadfeed.xml") or die("Error: Cannot create object");
#print_r($xml->xpath('league[@IdLeague="1"]/game[@gpd="Game"]'));

$games = array();
$counter = 1;

//foreach($xml->Leagues->league[0]->game as $event){

# uncomment if it doesnt work
# $scope = $xml->xpath('/Data/Leagues/league[@IdLeague="1"]/game[@gpd="Game"]');
$scope = $xml->xpath('league[@IdLeague="1"]/game');
#print_r($scope);

foreach($scope as $event){

  echo $event;
//if( $event->attributes()->idgmtyp=="118" ){

  $crisid = $event->attributes()->idgm;
  $date = $event->attributes()->gmdt;
  $time = $event->attributes()->gmtm;
  $gametime = $date . " " . $time;
  $away = properTeam($event->attributes()->vtm);
  $home = properTeam($event->attributes()->htm);
  $spread = $event->line->attributes()->hsprdt;

  //$rawgamedate = new DateTime($gametime, new DateTimeZone('America/New_York'));
  //$rawgamedate = new DateTime($gametime, new DateTimeZone('America/Chicago'));
  //$rawgamedate = new DateTime($gametime, new DateTimeZone('America/Halifax'));
  //$rawgamedate->setTimeZone(new DateTimeZone('UTC'));
  date_default_timezone_set('America/Los_Angeles');
  $rawgamedate = new DateTime($gametime);
  $rawgamedate->setTimeZone(new DateTimeZone('America/Chicago'));
  $gamedate = $rawgamedate->format('Y-m-d H:i:s');

  $gameWeek = $rawgamedate->format('W'); //Week number of year
  if( $rawgamedate->format('N') == 1){   //day of week (1 for monday)
        $gameWeek = $gameWeek - 1;       //so monday night games dont go towards new week
  }

  //$participants = array($event->attributes()->vtm, $event->attributes()->htm);
  //$invalidteam = array("Team A", "At Team A", "Team B", "At Team B");

  if( $gameWeek == $weekNum or $weekNum < 36 /*and !in_array($invalidteam,$participants)*/ ){  //The < 36 part handles before season starts

      array_push($games,array(
            "gametime" => $gamedate,
            "crisid" => $crisid,
            //"gameid" => $counter,
            "away" => $away,
            "home" => $home,
            "spread" => $spread
        ));

        $counter++;
  }
//}//end if
}//end foreach

/********************************/
/* Edit the entries below to reflect the appropriate values
/********************************/
$databasehost = "0.0.0.0";
$databasename = "5050club_2021";
$databaseusername ="root";
$databasepassword = "root";
$allgamesqueries = "";
$alldefaultpicksqueries = "";
$defaultpicksquery = "";
$memberid=0;
$membersquery="";
$gameid=0;

// set up connection to db
$mysqli = new mysqli($databasehost,$databaseusername,$databasepassword,$databasename);
$mysqli2 = new mysqli($databasehost,$databaseusername,$databasepassword,$databasename);

// check connection to make sure it works
if (mysqli_connect_errno()) {
    printf("Connect failed: %s\n", mysqli_connect_error());
    exit();
}



/***************************************************/
// the meat of where we update the tables.
foreach($games as $line) {

        /*we can only pull home/away spread from Pinnacle so this if/else assigns a fav/dog */

        if ($line['spread'] > 0) {
                $fav = $line['away'];
                $dog = "At " . $line['home'];
		$spread = -1 * $line['spread'];
        }
        else if ($line['spread'] == "") {
                $fav = "At " . $line['home'];
                $dog = $line['away'];
		$spread="OFF";
        }
        else {
                $fav = "At " . $line['home'];
                $dog = $line['away'];
		$spread = $line['spread'];
        }
	
	$pinnacleid = $line['crisid'];
	//$gameid = $line['gameid'];
	$date = $line['gametime'];

	/********************
	Update allgames table
	*********************/
	
	/****  see if game exists in allgames table *****/
	$gameexistsquery = $mysqli->query("SELECT count(*) as count from allgames where week='$curweek' and pinnacleid=$pinnacleid");
	#$gameexists = $gameexistsquery->fetch_assoc();
	//if the game doesnt exist in allgames table
	if($gameexists['count'] == 0) {

		//get max gameid, then inc by 1
		$maxgameidquery= $mysqli->query("select max(gameid) from allgames where week='$curweek'");
		$maxgameid = $maxgameidquery->fetch_assoc();
		if ($maxgameid['max(gameid)'] == NULL){
			$gameid=1;
		}
		else {
			$gameid = $maxgameid['max(gameid)'] + 1;
		}
	
		$gamequery = "INSERT INTO allgames (week,/*pinnacleid,*/gameid,date,favorite,underdog,spread,ATSwinner,winner) values('$curweek',/*'$pinnacleid',*/'$gameid','$date','$fav','$dog','$spread','','');";
	
		//Add something here where we create default pick and wager for each member in the picks table
		$membersquery = "SELECT memberid,defaultpick FROM members";

		if ($result = $mysqli->query($membersquery)) {

    		  while ($row = $result->fetch_assoc()) {
		    $memberid = $row['memberid'];
		    $defaultpick = $row['defaultpick'];

		    if( $defaultpick == 'favorite' ){
		      $defaultpicksquery = "INSERT INTO picks (week,pinnacleid,gameid,memberid,pick,wager) values('$curweek','$pinnacleid','$gameid','$memberid','$fav','2');";
		      $alldefaultpicksqueries .= $defaultpicksquery . "\n";
		    }
		    if( $defaultpick == 'underdog' ){
		      $defaultpicksquery = "INSERT INTO picks (week,pinnacleid,gameid,memberid,pick,wager) values('$curweek','$pinnacleid','$gameid','$memberid','$dog','2');";
		      $alldefaultpicksqueries .= $defaultpicksquery . "\n";
		    }
    		  }

    		  $result->free();
		}

	}


	//if game is already in allgames table
	if($gameexists['count'] == 1) {
		$gamequery = "UPDATE allgames SET week='$curweek',date='$date',favorite='$fav',spread='$spread',underdog='$dog' where pinnacleid=$pinnacleid;";
	}

	$allgamesqueries .= $gamequery . "\n";
	//UPDATE - per previous UPDATE line, putting this to set default pick for each member
	/*$alldefaultpicksqueries .= $defaultpicksquery . "\n";*/

}  /*end foreach loop*/

//inserts or updates the concatenation of game queries to the db
$mysqli->multi_query($allgamesqueries);
//UPDATE - per previous UPDATE line, putting this to set default pick for each member
$mysqli2->multi_query($alldefaultpicksqueries);
///////////////////////////////////////////


//UPDATE THIS
//Call script to check if any Upset picks are no longer underdogs
//include '/var/www/html//scripts/checkupsets.php';


/**************************************************************************/
/* Cleanup and printing to log */

// close sql connection
$mysqli->close();
$mysqli2->close();

/*error checking writing to log file*/
if(!is_writable($outputfile)) {
	echo "File is not writable, check permissions.\n";
}
else {
	$logfile = fopen($outputfile,"a");

	if(!$logfile) {
		echo "Error writing to the output file.\n";
	}
}

$newline = "\n";

fwrite($logfile,$now);
//uncomment once we square away the checkupsets.php script
//fwrite($logfile,$checkupsetoutput);
fwrite($logfile,$allgamesqueries);
fwrite($logfile,$alldefaultpicksqueries);
fwrite($logfile,$newline);

fclose($logfile);

?>
