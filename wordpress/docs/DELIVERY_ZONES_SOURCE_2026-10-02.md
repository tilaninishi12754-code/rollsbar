# Rolls Bar — delivery zones source input

Date: 2026-10-02
Status: THRESHOLDS CONFIRMED / NOT YET POLYGONIZED / NOT YET PRODUCTION-ENABLED

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

The numeric values are preserved exactly as provided. Father clarified that each value is the minimum order threshold from which delivery to that listed territory is free. If the cart is below the threshold, the intended flow is to ask the customer to add items up to the minimum.

This source replaces neither exact polygons nor geocoding rules by itself. Directional descriptions such as "ж/д вокзал до Павленко", "от гостиницы Москва до Марьино", "всё, что от ул. Батурина", and "Долина от Лозового" require exact map boundaries before automatic address -> zone resolution can be production-enabled.

## Still unresolved

- no separate courier fee has been supplied; current confirmed rule is free delivery from the listed minimum order threshold;
- convert the area descriptions into exact polygons/boundaries;
- define behavior for addresses on a boundary or outside all polygons.

Rule: do not invent polygons, fees or thresholds not explicitly supplied.
