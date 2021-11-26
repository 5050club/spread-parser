<?php

///////////  CURRENT USE
$hostname_logon = 'db';      //Database server LOCATION
$database_logon = '5050club_2019';       //Database NAME
$username_logon = 'root';       //Database USERNAME
$password_logon = 'root';       //Database PASSWORD

 
//connect to database
$con = mysqli_connect($hostname_logon, $username_logon, $password_logon, $database_logon);
if( mysqli_connect_errno() ) {
	echo "Failed to connect to MySQL: " . mysqli_connect_error();
}



////////// FUTURE USE
$mysqli = new mysqli("db", "root", "root", "5050club_2019", 3306);
if ($mysqli->connect_errno) {
    echo "Failed to connect to MySQL: (" . $mysqli->connect_errno . ") " . $mysqli->connect_error;
}


//////////OLD WAY
/*
//Connect to db server
$dbcnx = @mysqli_connect(localhost, root, "root");
if (!$dbcnx) {
        echo("<p>Unable to connect to db server.</p>");
        exit();
}

//Select database
@mysqli_select_db("5050club_testing", $dbcnx);
if (! @mysqli_select_db("5050club_testing")) {
        echo("<p>Can't find database.</p>");
        exit();
}
*/

?>
