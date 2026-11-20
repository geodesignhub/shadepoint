/**
 * compliance-worker.js
 *
 * Background (Web Worker) computation of the 3/30/300 live compliance stats
 * shown on the "Add Trees" page. Mirrors the logic of updateComplianceStats()
 * in dashboard/templates/add_diagram/draw_trees.html so bulk tree additions
 * (e.g. grids created from measurements) do not freeze the map UI.
 *
 * Protocol (main thread -> worker):
 *   { type: 'init', turfUrl: '<url of turf.min.js>' }   — must be sent first
 *   { type: 'layers', existingCanopy: [...], greenSpaces: [...], buildings: [...] }
 *   { type: 'compute', generation: <int>, trees: [...], bounds: [minx, miny, maxx, maxy] }
 *
 * Protocol (worker -> main thread):
 *   { type: 'result', generation: <int>, stats: { rule3, rule30, rule300 } }
 *   where each rule is { text: <string>, badgeClass: 'bg-success'|'bg-danger'|'bg-secondary' }
 */

'use strict';

let turf = null;
let LAYERS = {
    existingCanopy: [],
    greenSpaces: [],
    buildings: [],
};
let lastSeenGeneration = 0;
const DEFAULT_CROWN_RADIUS_M = 2.5; // assume 5 m canopy diameter per street tree

// True when a geometry's bbox overlaps the study-area bounds [minx, miny, maxx, maxy].
// Used to filter the existing_buildings FGB (which often covers a whole city) down
// to the project bounds before counting trees per building for Rule 3.
function bboxOverlapsBounds(bbox, boundsBox) {
    return !(
        bbox[2] < boundsBox[0] ||
        bbox[0] > boundsBox[2] ||
        bbox[3] < boundsBox[1] ||
        bbox[1] > boundsBox[3]
    );
}

function computeCompliance(treePoints, boundsBox) {
    // Rule 30 — Canopy cover
    const studyAreaPolygon = turf.bboxPolygon(boundsBox);
    const studyAreaSize = turf.area(studyAreaPolygon);
    let totalCanopyArea = 0;
    treePoints.forEach(function (tree) {
        const r = (tree.properties && tree.properties.crown_radius) || DEFAULT_CROWN_RADIUS_M;
        totalCanopyArea += turf.area(
            turf.circle(tree.geometry.coordinates, r, { units: 'meters' })
        );
    });
    LAYERS.existingCanopy.forEach(function (f) {
        totalCanopyArea += turf.area(f);
    });
    const canopyPct = (totalCanopyArea / studyAreaSize) * 100;
    const rule30 = {
        text: canopyPct.toFixed(1) + '% / 30%',
        badgeClass: canopyPct >= 30 ? 'bg-success' : 'bg-danger',
    };

    // Rule 3 — Trees visible
    const treeFC = turf.featureCollection(treePoints);
    let rule3;
    if (!LAYERS.buildings || LAYERS.buildings.length === 0) {
        // Fallback: count tree neighbours within 50 m of each tree
        let totalNeighbours = 0;
        treePoints.forEach(function (tree) {
            const buf = turf.circle(tree.geometry.coordinates, 50, { units: 'meters' });
            const within = turf.pointsWithinPolygon(treeFC, buf);
            totalNeighbours += Math.max(0, within.features.length - 1);
        });
        const avg = (totalNeighbours / treePoints.length).toFixed(1);
        rule3 = {
            text: 'avg ' + avg + ' trees / 50 m',
            badgeClass: parseFloat(avg) >= 3 ? 'bg-success' : 'bg-danger',
        };
    } else {
        // % of buildings (within the study bounds) that have ≥3 trees within
        // 50 m of their centroid. The existing_buildings FGB frequently covers
        // a whole city, so only buildings overlapping the project bounds are
        // counted — mirrors the backend site evaluation (utils.py), which
        // filters buildings by the study area before computing Rule 3.
        let metBuildings = 0;
        let totalBuildings = 0;
        LAYERS.buildings.forEach(function (b) {
            if (boundsBox && !bboxOverlapsBounds(turf.bbox(b), boundsBox)) return;
            const bc = turf.centroid(b);
            const buf = turf.circle(bc.geometry.coordinates, 50, { units: 'meters' });
            const within = turf.pointsWithinPolygon(treeFC, buf);
            totalBuildings += 1;
            if (within.features.length >= 3) metBuildings += 1;
        });
        const pct = totalBuildings > 0 ? Math.round((metBuildings / totalBuildings) * 100) : 0;
        rule3 = {
            text: pct + '% / buildings ≥3 trees',
            badgeClass: pct >= 100 ? 'bg-success' : 'bg-danger',
        };
    }

    // Rule 300 — Green space proximity
    let rule300;
    if (!LAYERS.greenSpaces || LAYERS.greenSpaces.length === 0) {
        rule300 = { text: 'Layer unavailable', badgeClass: 'bg-secondary' };
    } else {
        let maxDist = 0;
        treePoints.forEach(function (tree) {
            let nearestDist = Infinity;
            LAYERS.greenSpaces.forEach(function (gs) {
                const geom = gs.geometry;
                if (!geom) return;
                let dist;
                if (geom.type === 'Polygon' || geom.type === 'MultiPolygon') {
                    // distance to the green space itself, not its centroid
                    dist = turf.pointToPolygonDistance(tree, gs, { units: 'meters' });
                } else {
                    dist = turf.distance(tree, turf.centroid(gs), { units: 'meters' });
                }
                if (dist < nearestDist) nearestDist = dist;
            });
            if (nearestDist > maxDist) maxDist = nearestDist;
        });
        rule300 = {
            text: Math.round(maxDist) + ' m / 300 m',
            badgeClass: maxDist <= 300 ? 'bg-success' : 'bg-danger',
        };
    }

    return { rule3: rule3, rule30: rule30, rule300: rule300 };
}

self.onmessage = function (e) {
    const msg = e.data || {};
    if (msg.type === 'init') {
        if (!turf && msg.turfUrl) {
            importScripts(msg.turfUrl);
            turf = self.turf;
        }
        return;
    }
    if (msg.type === 'layers') {
        LAYERS.existingCanopy = msg.existingCanopy || [];
        LAYERS.greenSpaces = msg.greenSpaces || [];
        LAYERS.buildings = msg.buildings || [];
        return;
    }
    if (msg.type !== 'compute' || !turf) return;
    const generation = msg.generation || 0;
    // Ignore out-of-order compute requests
    if (generation <= lastSeenGeneration) return;
    lastSeenGeneration = generation;
    const stats = computeCompliance(msg.trees || [], msg.bounds);
    self.postMessage({ type: 'result', generation: generation, stats: stats });
};
