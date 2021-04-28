DATE=$(date | awk -F " " '{print $3 " " $2 " " $1}')
HOUR=$(date | awk -F" " '{print $5}' | awk -F":" '{print $1":"$2}')

AUX=0

FILE="horario.txt"

getopts "nabs" OPTVAR
case "$OPTVAR" in
   "n") echo "----------------" >> $FILE
	echo $DATE >> $FILE
	printf "Entrada:  \t%s\n" $HOUR >> $FILE
	AUX=1
	;;
   "a")	printf "Saida almoço: \t%s\n" $HOUR >> $FILE
	;;
   "b") printf "Volta almoço: \t%s\n" $HOUR >> $FILE
	;;
   "s") printf "Saida: \t\t%s\n" $HOUR >> $FILE
	;;
esac
