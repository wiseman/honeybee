#!/bin/sh
awk '
BEGIN {printf("%5s %9s %8s %12s %5s %4s %4s\n", "numv", "distance", "user", "village", "pop", "x", "y");}
/^[0-9]+/ {
  dx = 210 - $4;
  if (dx < 0) dx = -dx;
  dy = 7 - $5;
  if (dy < 0) dy = -dy;
  dist = dx*dx + dy*dy;
  dist = sqrt(dist);
  command = "./numvillages.sh " $1
  command | getline numvillages
  close(command)
printf("%5s %9s %8s %12s %5s %4s %4s\n", numvillages, dist, $1, $2, $3, $4, $5);}
'
