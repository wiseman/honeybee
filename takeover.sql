select a.user_id, a.village_id, a.population, a.x, a.y from x_world2 as a, x_world2 as b
where a.alliance_id = 0
and a.x >= 190 and a.x <= 230
and a.y >= 0 and a.y <= 27
and a.user_id = b.user_id
group by abs(a.x - 210) * abs(a.x - 210) + abs(a.y - 7) * abs(a.y - 7)

