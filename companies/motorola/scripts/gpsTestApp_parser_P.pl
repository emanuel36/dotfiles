#  Gps Route Parser for Android O
#
#  Generate a Google Earth file (.kml) from Main Logs
#  Source:  Modified version of
#  https://sites.google.com/a/motorola.com/lbswisl/tools-repository

#!/usr/bin/perl
use Math::Trig;

#### Get file argument Or If none provided attempt all *.log files
#### in current directory.
#KML plot colors  - transparency,B,G,R
%my_colors = ('ORANGE','ff00aaff',
	'YELLOW','ff00ffff',
	'RED',   'ff0000ff',
	'GREEN', 'ff00ff00',
	'BLUE',  'ffffbf00',
	'PURPLE','ffee82ee',
	'CYAN',  'ffffff00',
	'TAN',   'ffaddeff',
	'FADETAN', 'c0addeff');
$numArgs = $#ARGV +1;
$ground_truth_lat = "42.2905416";
$ground_truth_long = "-87.9991067";
$color = "";
@accuracy_reports;

@TTFF_array;
$OldFormat = 0;

sub calcDist($$$$);
sub parseSvInfo($);

if ($numArgs >= 1)
{
	@files;
	for ($i=0; $i < $numArgs; $i+=1)
	{
		if ($ARGV[$i] =~ /-color/) { $color = $ARGV[$i+1]; $i+=1; }
		elsif ($ARGV[$i] =~ /-lat/) { $ground_truth_lat = $ARGV[$i+1]; $i+=1; }
		elsif ($ARGV[$i] =~ /-long/) { $ground_truth_long = $ARGV[$i+1]; $i+=1; }
		elsif ($ARGV[$i] =~ /-old/) { $OldFormat = 1; }
		else { push @files,$ARGV[$i]; }
	}
	$color = "BLUE";
	$color =~ tr/a-z/A-Z/;
	$color = $my_colors{$color};
}
else
{
	printf ("Usage:  \"parser.pl logfile\" \n\n");
	exit;
}


parse_files();

exit;


sub getNewColor
{
	$random_color1 = int(rand(255));
	$random_color2 = int(rand(255));
	$random_color3 = int(rand(255));
	$hexval1 = sprintf("%x", $random_color1); if (length $hexval1 == 1) {$hexval1 = '0'.$hexval1;}
	$hexval2 = sprintf("%x", $random_color2); if (length $hexval2 == 1) {$hexval2 = '0'.$hexval2;}
	$hexval3 = sprintf("%x", $random_color3); if (length $hexval3 == 1) {$hexval3 = '0'.$hexval3;}
	$color = "FF".$hexval1.$hexval2.$hexval3;
	#printf ("Iteration $iteration  rand1: $hexval1  rand2: $hexval2 rand3: $hexval3 ---- color:  $color\n");
}


sub parse_files
{
	foreach $file (@files)
	{
		open(DATA, "+< $file") || file_not_open($file);
		open(DATAOUT, ">".$file.".kml") || file_not_open($file.".kml");
		open(CSVOUT, ">".$file.".csv") || file_not_open($file.".csv");

		printf ("\n-- Processing file $file --\n");


		#Varables
		$cno_normalize = 0;
		$count = 1;
		$folder = 1;
		$parseSv = 0;
		$CNO = "";

		print_kml();

		printf (CSVOUT "timedate, time, lat, lon, unc, mph, dop m/s, del m/s, delta(m), err%%, heading\n");

		while(<DATA>)
		{
			$line = $_;
			if ($line =~ /(\d.+) +\d+ +\d+.+reportLocation.+gps (.+,.+),(.+,.+) hAcc=(.+) et=(.+) alt=(.+) vel=([\d.]+) (bear=(.+) |)vAcc=(.+) sAcc=(.+) bAcc=(.+)\]/) {

				$timedate = $1;
				$lat = $2;
				$long = $3;
				$unc = $4;
				$et = $5;
				$alt = $6;
				$vel = $7;
				$bearing = $9;
				$vacc = $10;
				$sacc = $11;
				$bacc = $12;
				$time = "0";

				$lat =~ s/\,/./g;
				$long =~ s/\,/./g;

				if($bearing eq "") {
					$bearing = "0.0";
				}

				$speed = $vel;               # m/s
				$speedmph = $speed * 2.23694;  # convert to mph
				$derror = 0;
				$distance = 0;
				$tdelta = $7 - $time;
				$distspeed = 0;

				$count += 1;

				printf (CSVOUT "'$timedate', %14d, %11.7f, %11.7f, %5.1f, %4.1f,  %6.3f, %6.3f, %5.1f, %3d, %3d, CNOs:, $CNO\n",
					$time, $lat, $long, $unc, $speedmph, $speed, $distspeed, $distance, $derror, $bearing);
				printkml();
				$CNO = "";

				END:
			}
		}

		#### Subroutines ####


		sub parseSvInfo($){
			my($str) = @_;

			if ($str =~ /sv count:/) {

			}elsif ($str =~ /PRN/) {

			}elsif($str =~ /SNR/){
				($junk, $CNO) = split(/GpsLocationProvider: SNR/,$str);

				#print($CNO);
				chomp($CNO);
			}elsif($str =~ /AZM/){
				$parseSv = 0;
			}

		}

		sub  calcDist($$$$)  {
			my($lat1, $lon1, $lat2, $lon2) = @_;
			return sqrt((6378137*cos($lat1/57.29583)*($lon2 - $lon1)/57.29583)**2 + (6378137*($lat2 - $lat1)/57.29583)**2);
		}

		sub printkml
		{

			printf (DATAOUT "   <Placemark> \n");
			printf (DATAOUT "     <name>Iteration: $count</name> \n");

			printf (DATAOUT "     <description> \n");
			printf (DATAOUT " $timedate<br />Time:  $time<br />lat:  $lat<br /> long: $long<br /> unc: $unc m<br />speed: %.2f mph %.2f m/s<br />bearing: $bearing<br />\n",$speedmph, $speed );
			printf (DATAOUT "CNOs:$CNO<br />\n");

			printf (DATAOUT "	  </description> \n");

			printf (DATAOUT "        <styleUrl>#celltype_1</styleUrl> \n");

			if ($speed != 0.0) { printf (DATAOUT "        <styleUrl>#2dfix_heading</styleUrl> \n"); }
			else { printf (DATAOUT "        <styleUrl>#celltype_1</styleUrl> \n"); }


			printf (DATAOUT "<Style>\n");
			printf (DATAOUT "<IconStyle>\n");
			if ($bearing != 0.0) { printf (DATAOUT "<heading>%d</heading>\n", ($bearing+180)%360); }
			#if ($bearing != 0.0) { printf (DATAOUT "<heading>%d</heading>\n", ($bearing)); }
			printf (DATAOUT "<color>%s</color>\n", $color);
			printf (DATAOUT "</IconStyle>\n");
			printf (DATAOUT "</Style>\n");


			printf (DATAOUT "        <Point> \n");
			printf (DATAOUT "            <coordinates>$long,$lat,0</coordinates> \n");
			printf (DATAOUT "        </Point>  \n");
			printf (DATAOUT "</Placemark> \n");
			printf (DATAOUT "\n");

		}

		printf (DATAOUT "");
		printf (DATAOUT "</Folder>\n");
		printf (DATAOUT "</Document>");
		printf (DATAOUT "</kml>\n");

		close(DATA);
		close(DATAOUT);
		close(CSVOUT);
	}

}

sub circlegen()
{

	my($radius, $color, $text, $latitude, $longitude) = @_;

	local($lat1);
	local($long1);
	local($i);
	$MY_PI = 3.14159265;

	# convert coordinates to radians
	$lat1 = deg2rad($latitude);
	$long1 = deg2rad($longitude);

	$d_rad = $radius/6378137;

	#change radius to a string to print.
	$radius = sprintf ("%1.2f",$radius);

	# write header:
	print DATAOUT "<Folder>\n<name>$text $radius M</name>\n<visibility>1</visibility>\n<Placemark>\n<name>circle</name>\n<visibility>1</visibility>\n<Style>\n<geomColor>$color</geomColor>\n<geomScale>3</geomScale></Style>\n<LineString>\n<coordinates>\n";

	# loop through the array and write path linestrings
	for($i=0; $i<=360; $i++) {
		$radial = deg2rad($i);
		$lat_rad = asin(sin($lat1)*cos($d_rad) + cos($lat1)*sin($d_rad)*cos($radial));
		$dlon_rad = atan2(sin($radial)*sin($d_rad)*cos($lat1), cos($d_rad)-sin($lat1)*sin($lat_rad));
		$lon_rad = &fmod(($long1+$dlon_rad + $MY_PI), 2 * $MY_PI) - $MY_PI;


		#fwrite( $fileappend, rad2deg($lon_rad).",".rad2deg($lat_rad).",0 ");
		printf DATAOUT ("%10.6f, %10.6f, 0\n", rad2deg($lon_rad), rad2deg($lat_rad));
	}

	# output footer
	print DATAOUT "</coordinates>\n</LineString>\n</Placemark>\n</Folder>";

}

sub fmod()
{
	my($x, $y) = @_;
	return ($x - (int($x/$y) * $y));
}


#### -- Support FUNCTIONS -- ####

sub file_not_open($)
{
	my($file) = @_;
	printf ("Could not open file: -$file- !\n"); next;
}

sub average {
	@_ == 1 or die ('Sub usage: $average = average(\@array);');
	my ($array_ref) = @_;
	my $sum;
	my $count = scalar @$array_ref;
	foreach (@$array_ref) { $sum += $_; }
	return $sum / $count;
}

sub median {
	@_ == 1 or die ('Sub usage: $median = median(\@array);');
	my ($array_ref) = @_;
	my $count = scalar @$array_ref;
	# Sort a COPY of the array, leaving the original untouched
	my @array = sort { $a <=> $b } @$array_ref;
	if ($count % 2) {
		return $array[int($count/2)];
	} else {
		return ($array[$count/2] + $array[$count/2 - 1]) / 2;
	}
}

sub max {
	my ($max, @vars) = @_;
	for (@vars) {
		$max = $_ if $_ > $max;
	}
	return $max;
}
sub min {
	my ($max, @vars) = @_;
	for (@vars) {
		$max = $_ if $_ < $max;
	}
	return $max;
}

sub accuracy_calculation
{
	if ($ground_truth_lat == "" && $ground_truth_long == "")
	{
		return -1;
	}
	#Stolen from Eric Hefner's GAM log parser
	my $lat = @_[0];
	my $long = @_[1];

	$pos_accuracy = sqrt((6378137*cos($ground_truth_lat/57.29583)*($long - $ground_truth_long)/57.29583)**2 + (6378137*($lat - $ground_truth_lat)/57.29583)**2);

	# reformat for printing in csv file
	$temp = sprintf("%7.2f",$pos_accuracy);
	$pos_accuracy = $temp;

	return $pos_accuracy;
}

sub get_time
{
	$hrs = @_[0] *60*60*1000;
	$mins = @_[1] *60*1000;
	$secs = @_[2] * 1000;
	$ms = @_[3];
	return $hrs+$mins+$secs+$ms;
}
sub msTOtimestamp
{
	$time = @_[0];
	$hrs = int($time/1000/60/60);
	$mins = ($time/1000/60)%60;
	$secs = ($time/1000)%60;
	$ms = $time%1000;
	if($secs< 10) { $secs = '0'.$secs; }
	if($mins< 10) { $mins = '0'.$mins; }
	if($hrs < 10) { $hrs = '0'.$hrs; }
	if($ms < 100) { if($ms < 10){$ms = '0'.$ms;};$ms = '0'.$ms; }
	return ''.$hrs.':'.$mins.':'.$secs.'.'.$ms;
}
sub msTOsecs
{
	$time = @_[0];
	$secs = $time/1000;
	if($secs< 10) { $secs = '0'.$secs; }
	return ''.$secs;
}

sub print_kml
{

	printf (DATAOUT "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
	printf (DATAOUT "    <kml xmlns=\"http://earth.google.com/kml/2.0\">\n");
	printf (DATAOUT "    <Document>\n");
	printf (DATAOUT "    <open>1</open>\n");
	printf (DATAOUT "    <!-- Begin Style Definitions -->\n");
	printf (DATAOUT "    <Style id=\"pathstyle1\">\n");
	printf (DATAOUT "        <geomScale>3</geomScale>\n");
	printf (DATAOUT "        <LineStyle><color>ffffff00</color></LineStyle>\n");
	printf (DATAOUT "    </Style>\n");
	printf (DATAOUT "\n");


	printf (DATAOUT "   <Style id=\"celltype_0\">\n");
	printf (DATAOUT "    <IconStyle>\n");
	printf (DATAOUT "      <scale>0.5</scale>\n");
	printf (DATAOUT "      <color>  ff00aaff            </color>\n");
	printf (DATAOUT "      <Icon>\n");
	printf (DATAOUT "        <href>http://maps.google.com/mapfiles/kml/shapes/donut.png</href>\n");
	printf (DATAOUT "      </Icon>\n");
	printf (DATAOUT "    </IconStyle>\n");
	printf (DATAOUT "    <balloonStyle>\n");
	printf (DATAOUT "    <text><![CDATA[<b>Cell Type 0:</b><br /><br />$[description]]]></text>\n");
	printf (DATAOUT "    </balloonStyle>\n");
	printf (DATAOUT "    </Style>\n");
	printf (DATAOUT "    \n");
	printf (DATAOUT "\n");

	printf (DATAOUT "   <Style id=\"arrow_0\">\n");
	printf (DATAOUT "    <IconStyle>\n");
	printf (DATAOUT "      <scale>0.3</scale>\n");
	printf (DATAOUT "      <color>  ff00aaff            </color>\n");
	printf (DATAOUT "      <Icon>\n");
	printf (DATAOUT "        <href>http://maps.google.com/mapfiles/kml/shapes/arrow.png</href>\n");
	printf (DATAOUT "      </Icon>\n");
	printf (DATAOUT "    </IconStyle>\n");
	printf (DATAOUT "    <LabelStyle>\n");
	printf (DATAOUT "    <scale>0</scale>\n");
	printf (DATAOUT "    </LabelStyle>\n");
	printf (DATAOUT "    <balloonStyle>\n");
	printf (DATAOUT "    <text><![CDATA[<b>Cell Type 0:</b><br /><br />$[description]]]></text>\n");
	printf (DATAOUT "    </balloonStyle>\n");
	printf (DATAOUT "    </Style>\n");
	printf (DATAOUT "    \n");
	printf (DATAOUT "\n");


	printf (DATAOUT "   <Style id=\"celltype_1\">\n");
	printf (DATAOUT "    <IconStyle>\n");
	printf (DATAOUT "      <scale>0.5</scale>\n");
	printf (DATAOUT "      <color>  ff0000ff            </color>\n");
	printf (DATAOUT "      <Icon>\n");
	printf (DATAOUT "        <href>http://maps.google.com/mapfiles/kml/shapes/donut.png</href>\n");
	printf (DATAOUT "      </Icon>\n");
	printf (DATAOUT "    </IconStyle>\n");
	printf (DATAOUT "    <LabelStyle>\n");
	printf (DATAOUT "    <scale>0</scale>\n");
	printf (DATAOUT "    </LabelStyle>\n");
	printf (DATAOUT "    <balloonStyle>\n");
	printf (DATAOUT "    <text><![CDATA[<b>Stationary Fix:</b><br /><br />$[description]]]></text>\n");
	printf (DATAOUT "    </balloonStyle>\n");
	printf (DATAOUT "    </Style>\n");
	printf (DATAOUT "    \n");
	printf (DATAOUT "\n");



	printf (DATAOUT "   <Style id=\"2dfix_heading\">\n");
	printf (DATAOUT "    <IconStyle>\n");
	printf (DATAOUT "      <scale>0.5</scale>\n");
	printf (DATAOUT "      <color>  ff0000ff            </color>\n");
	printf (DATAOUT "      <Icon>\n");
	printf (DATAOUT "        <href>http://maps.google.com/mapfiles/kml/shapes/arrow.png</href>\n");
	printf (DATAOUT "      </Icon>\n");
	printf (DATAOUT "    </IconStyle>\n");
	printf (DATAOUT "    <LabelStyle>\n");
	printf (DATAOUT "    <scale>0</scale>\n");
	printf (DATAOUT "    </LabelStyle>\n");
	printf (DATAOUT "    <balloonStyle>\n");
	printf (DATAOUT "    <text><![CDATA[<b>2D Fix:</b><br /><br />$[description]]]></text>\n");
	printf (DATAOUT "    </balloonStyle>\n");
	printf (DATAOUT "    </Style>\n");
	printf (DATAOUT "    \n");
	printf (DATAOUT "\n");

	printf (DATAOUT "    <!-- End Style Definitions -->\n");
	printf (DATAOUT "\n");
	printf (DATAOUT "\n");
	printf (DATAOUT "<Folder>\n");
	printf (DATAOUT "<name>Results $folder</name>\n");
	printf (DATAOUT "\n");
	printf (DATAOUT "\n");

}
