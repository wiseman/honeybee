#!/bin/sh

MAP1=$1
MAP2=$2


TMPMAP1=/var/tmp/map1.sql
TMPMAP2=/var/tmp/map2.sql

sed s/x_world2/x_world/g < "$MAP1" > $TMPMAP1
sed s/x_world/x_world2/g < "$MAP2" > $TMPMAP2

mysql --user=root travian < schema.sql
for i in $TMPMAP1 $TMPMAP2
do
  echo $i
  mysql --user=root travian < $i
done

