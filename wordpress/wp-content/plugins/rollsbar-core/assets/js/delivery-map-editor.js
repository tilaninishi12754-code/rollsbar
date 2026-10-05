(() => {
  'use strict';

  const config = window.RollsBarDeliveryMapConfig || {};
  const MAX_VERTICES = Number(config.maxVertices || 150);
  const DEFAULT_CENTER = Array.isArray(config.center) ? config.center : [34.1003, 44.9521];
  const DEFAULT_ZOOM = Number(config.zoom || 11);

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  const zoneSelect = $('#rollsbar-map-zone-select');
  const editToggle = $('#rollsbar-map-edit-toggle');
  const undoButton = $('#rollsbar-map-undo');
  const clearButton = $('#rollsbar-map-clear');
  const editorStatus = $('#rollsbar-map-editor-status');
  const mapElement = $('#rollsbar-yandex-map');

  if (!zoneSelect || !editToggle || !undoButton || !clearButton || !editorStatus || !mapElement) {
    return;
  }

  let map = null;
  let polygonFeature = null;
  let vertexMarkers = [];
  let editing = false;
  let currentZone = Number(zoneSelect.value || 0);
  let points = [];

  const fieldFor = (index) => document.querySelector(`.rollsbar-polygon-field[data-zone-index="${index}"]`);
  const statusFor = (index) => document.querySelector(`.rollsbar-polygon-status[data-zone-index="${index}"]`);

  const safeParsePoints = (raw) => {
    try {
      const value = JSON.parse(raw || '[]');
      if (!Array.isArray(value)) return [];
      return value
        .filter((point) => Array.isArray(point) && point.length >= 2)
        .map((point) => [Number(point[0]), Number(point[1])])
        .filter(([lng, lat]) => Number.isFinite(lng) && Number.isFinite(lat) && lng >= -180 && lng <= 180 && lat >= -90 && lat <= 90)
        .slice(0, MAX_VERTICES);
    } catch (_) {
      return [];
    }
  };

  const loadZone = (index) => {
    currentZone = Number(index);
    const field = fieldFor(currentZone);
    points = field ? safeParsePoints(field.value) : [];
    updateStatus();
    renderGeometry();
  };

  const persist = () => {
    const field = fieldFor(currentZone);
    if (field) {
      field.value = JSON.stringify(points);
      field.dispatchEvent(new Event('change', { bubbles: true }));
    }
    updateStatus();
  };

  const updateStatus = () => {
    const zoneStatus = statusFor(currentZone);
    const label = points.length >= 3 ? `${points.length} точек` : 'Не задана';
    if (zoneStatus) zoneStatus.textContent = label;
    editorStatus.textContent = editing
      ? `Редактирование: ${points.length}/${MAX_VERTICES} точек`
      : `Граница: ${label}`;
    editToggle.textContent = editing ? 'Завершить редактирование' : 'Редактировать границу';
  };

  const closeRing = (coords) => {
    if (coords.length < 3) return [];
    return [...coords, [...coords[0]]];
  };

  const removeCurrentGeometry = () => {
    if (!map) return;
    if (polygonFeature) {
      map.removeChild(polygonFeature);
      polygonFeature = null;
    }
    vertexMarkers.forEach((marker) => map.removeChild(marker));
    vertexMarkers = [];
  };

  const updatePolygonOnly = () => {
    if (!polygonFeature) return;
    if (points.length < 3) {
      map.removeChild(polygonFeature);
      polygonFeature = null;
      return;
    }
    polygonFeature.update({
      geometry: {
        type: 'Polygon',
        coordinates: [closeRing(points)],
      },
    });
  };

  const createVertexElement = (index) => {
    const element = document.createElement('div');
    element.className = 'rollsbar-map-vertex';
    element.title = `Точка ${index + 1}. Перетащите для изменения.`;
    element.setAttribute('role', 'button');
    element.setAttribute('aria-label', `Точка границы ${index + 1}`);

    element.addEventListener('click', (event) => event.stopPropagation());
    element.addEventListener('dblclick', (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (!editing || points.length <= 3) return;
      points.splice(index, 1);
      persist();
      renderGeometry();
    });

    return element;
  };

  const renderGeometry = () => {
    if (!map || !window.ymaps3) return;
    removeCurrentGeometry();

    const { YMapFeature, YMapMarker } = window.ymaps3;

    if (points.length >= 3) {
      polygonFeature = new YMapFeature({
        id: `rollsbar-zone-${currentZone}`,
        geometry: {
          type: 'Polygon',
          coordinates: [closeRing(points)],
        },
        style: {
          fill: 'rgba(29, 78, 216, 0.15)',
          stroke: [{ color: '#1d4ed8', width: 3 }],
        },
      });
      map.addChild(polygonFeature);
    }

    points.forEach((point, index) => {
      const element = createVertexElement(index);
      const marker = new YMapMarker(
        {
          coordinates: point,
          draggable: editing,
          onDragMove: (coordinates) => {
            if (!editing || !Array.isArray(coordinates)) return;
            const next = [Number(coordinates[0]), Number(coordinates[1])];
            if (!Number.isFinite(next[0]) || !Number.isFinite(next[1])) return;
            points[index] = next;
            marker.update({ coordinates: next });
            persist();
            updatePolygonOnly();
          },
          onDragEnd: () => {
            persist();
            updateStatus();
          },
        },
        element
      );
      vertexMarkers.push(marker);
      map.addChild(marker);
    });

    updateStatus();
  };

  const addPoint = (coordinates) => {
    if (!editing || !Array.isArray(coordinates) || points.length >= MAX_VERTICES) return;
    const lng = Number(coordinates[0]);
    const lat = Number(coordinates[1]);
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) return;
    points.push([lng, lat]);
    persist();
    renderGeometry();
  };

  const init = async () => {
    if (!window.ymaps3) {
      editorStatus.textContent = 'Yandex Maps API не загрузился.';
      return;
    }

    try {
      await window.ymaps3.ready;
      const {
        YMap,
        YMapDefaultSchemeLayer,
        YMapDefaultFeaturesLayer,
        YMapListener,
      } = window.ymaps3;

      map = new YMap(mapElement, {
        location: {
          center: DEFAULT_CENTER,
          zoom: DEFAULT_ZOOM,
        },
      });
      map.addChild(new YMapDefaultSchemeLayer({}));
      map.addChild(new YMapDefaultFeaturesLayer({}));
      map.addChild(
        new YMapListener({
          layer: 'any',
          onClick: (object, event) => {
            if (!editing || object !== undefined || !event || !Array.isArray(event.coordinates)) return;
            addPoint(event.coordinates);
          },
        })
      );

      loadZone(currentZone);
    } catch (error) {
      console.error('RollsBar delivery map init failed', error);
      editorStatus.textContent = 'Не удалось инициализировать карту. Проверьте API key и HTTP Referer restriction.';
    }
  };

  zoneSelect.addEventListener('change', () => {
    editing = false;
    loadZone(Number(zoneSelect.value));
  });

  editToggle.addEventListener('click', () => {
    editing = !editing;
    renderGeometry();
  });

  undoButton.addEventListener('click', () => {
    if (!points.length) return;
    points.pop();
    persist();
    renderGeometry();
  });

  clearButton.addEventListener('click', () => {
    if (!points.length) return;
    if (!window.confirm('Очистить сохранённую границу выбранной зоны? Изменение применится только после сохранения формы.')) return;
    points = [];
    persist();
    renderGeometry();
  });

  $$('.rollsbar-polygon-field').forEach((field) => {
    const index = Number(field.dataset.zoneIndex || 0);
    const parsed = safeParsePoints(field.value);
    const status = statusFor(index);
    if (status) status.textContent = parsed.length >= 3 ? `${parsed.length} точек` : 'Не задана';
  });

  init();
})();
