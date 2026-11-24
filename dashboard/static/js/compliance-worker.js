/**
 * compliance-worker.js
 *
 * Background (Web Worker) computation of the 3/30/300 live compliance stats
 * shown on the "Add Trees" page. Bulk tree additions (e.g. grids created from
 * measurements) therefore do not freeze the map UI.
 *
 * The actual rules live in compliance-core.js, which is also loaded on the main
 * thread as the synchronous fallback — both paths share one implementation.
 *
 * Protocol (main thread -> worker):
 *   { type: 'init', turfUrl: '<url of turf.min.js>', coreUrl: '<url of compliance-core.js>' }
 *   { type: 'layers', bounds: [minx, miny, maxx, maxy],
 *     existingCanopy: [...], greenSpaces: [...], buildings: [...] }
 *   { type: 'compute', generation: <int>, trees: [...], bounds: [minx, miny, maxx, maxy] }
 *
 * Protocol (worker -> main thread):
 *   { type: 'result', generation: <int>, stats: { rule3, rule30, rule300 } }
 *   where each rule is { text: <string>, badgeClass: 'bg-success'|'bg-danger'|'bg-secondary' }
 */

'use strict';

let turf = null;
let core = null;
let LAYERS = {
    existingCanopy: [],
    greenSpaces: [],
    buildings: [],
};
// Pre-processed layer data (filtered/clipped/dissolved) for the study bounds.
let prepared = null;
let lastSeenGeneration = 0;

self.onmessage = function (e) {
    const msg = e.data || {};

    if (msg.type === 'init') {
        if (!core && msg.coreUrl) {
            importScripts(msg.coreUrl);
            core = self.ComplianceCore;
        }
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
        prepared = null;
        // Prepare eagerly when the study bounds are known so the first tree
        // edit does not pay for clipping/dissolving the analytical layers.
        if (core && turf && msg.bounds) {
            prepared = core.prepareLayers(turf, LAYERS, msg.bounds);
        }
        return;
    }

    if (msg.type !== 'compute' || !turf || !core) return;
    const generation = msg.generation || 0;
    // Ignore out-of-order compute requests
    if (generation <= lastSeenGeneration) return;
    lastSeenGeneration = generation;

    if (!prepared) {
        prepared = core.prepareLayers(turf, LAYERS, msg.bounds);
    }
    const stats = core.computeCompliance(turf, msg.trees || [], prepared);
    self.postMessage({ type: 'result', generation: generation, stats: stats });
};
