#!/bin/sh

echo "select count(*) from x_world2 as a where a.user_id = $1" | mysql --user=root travian | tail -1