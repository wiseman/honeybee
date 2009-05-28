select x_world.village_id
from x_world,x_world2
where x_world.village_id = x_world2.village_id
  and x_world.population = x_world2.population
  and x_world2.alliance_id = 0
  and x_world.x >= 200 and x_world.x <= 220
  and x_world.y >= 0 and x_world.y <= 17
  and x_world.population > 7
group by x_world.user_id;