---
title: "{{title}}"
type: sail-boat
slug: {{slug}}
class: "{{class}}"
hull_length_m: {{hull_length_m}}
crew: {{crew}}
sail_area_m2: {{sail_area_m2}}
rig: {{rig}}
upwind_twa: {{upwind_twa}}
downwind_twa: {{downwind_twa}}
polar: null
created: {{date}}
updated: {{date}}
tags: []
summary: ""
---

## Заметки

## Выходы и гонки

```dataview
TABLE date, event, result.position AS "место", weather_actual.wind_speed_kt AS "ветер kt"
FROM "sailing/tracks"
WHERE type = "sail-race" AND boat = "{{slug}}"
SORT date DESC
```
