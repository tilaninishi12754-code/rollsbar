# Rolls Bar — delivery zones source input

Date: 2026-10-02
Status: SOURCE INPUT / NOT YET POLYGONIZED / NOT YET PRODUCTION-ENABLED

## Owner-provided source

1200 ₽:
- Москольцо
- Кечкеметская
- Лермонтово
- Гагарина
- ж/д вокзал до Павленко

1500 ₽:
- Луговое
- 51 Армии
- Б. Куна
- Бородина
- Загородный
- Белое 5
- М. Жукова
- Г. Сталинграда

2000 ₽:
- Живописное
- Давыдовка
- Свобода
- Мирное
- Дубки
- от гостиницы Москва до Марьино
- старый аэропорт
- ГРЭС

2500 ₽:
- Строгановка
- Молодежное
- Аграрное
- Белое 3
- Марьино
- всё, что от ул. Батурина

3000 ₽:
- Белое 4
- Денисовка

3500 ₽:
- Урожайное
- Долина от Лозового
- Фонтаны

4000 ₽:
- Донское
- Мазанка

## Current interpretation

The numeric values are preserved exactly as provided. They are treated as candidate minimum-order thresholds by area, pending explicit confirmation.

This source replaces neither exact polygons nor geocoding rules by itself. Directional descriptions such as "ж/д вокзал до Павленко", "от гостиницы Москва до Марьино", "всё, что от ул. Батурина", and "Долина от Лозового" require exact map boundaries before automatic address -> zone resolution can be production-enabled.

## Still unresolved

- confirm that 1200/1500/.../4000 ₽ mean minimum order amount, not delivery fee;
- confirm whether courier delivery is free once the minimum is met or whether a separate delivery fee applies;
- define free-delivery thresholds if any;
- convert the area descriptions into exact polygons/boundaries;
- define behavior for addresses on a boundary or outside all polygons.

Rule: do not invent polygons, fees or thresholds not explicitly supplied.
