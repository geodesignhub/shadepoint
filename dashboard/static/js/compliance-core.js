/**
 * compliance-core.js
 *
 * Shared 3/30/300 live compliance computation for the "Add Trees" page.
 * Loaded as a classic script on the main thread (synchronous fallback) and via
 * importScripts() inside compliance-worker.js, so both execution paths always
 * produce the same numbers.
 *
 * Rules:
 *   Rule 3   — Trees visible: % of buildings (within the study bounds) with at
 *              least 3 drawn trees within 50 m of their centroid.
 *   Rule 30  — Canopy cover: total tree canopy area (drawn trees + the optional
 *              Existing Canopy layer) divided by the study area. Canopy is
 *              clipped to the study bounds and dissolved, so overlaps and
 *              out-of-bounds features are counted once.
 *   Rule 300 — Green space access: % of buildings (within the study bounds)
 *              whose centroid is within 300 m of a green space polygon.
 *              Drawn trees are deliberately NOT treated as green space: tree
 *              planting and green space provision are separate interventions.
 */
(function (global) {
    'use strict';

    var DEFAULT_CROWN_RADIUS_M = 2.5;    // 5 m canopy diameter per street tree
    var TREE_VIEW_DISTANCE_M = 50;       // Rule 3 — trees visible from buildings
    var GREEN_SPACE_DISTANCE_M = 300;    // Rule 300 — access distance
    var CANOPY_UNION_LIMIT = 1500;       // union cost guard for big canopy layers
    var TREE_UNION_LIMIT = 500;          // union cost guard for drawn tree circles

    // True when a geometry bbox overlaps the study bounds [minx, miny, maxx, maxy].
    function bboxOverlapsBounds(bbox, boundsBox) {
        return !(
            bbox[2] < boundsBox[0] ||
            bbox[0] > boundsBox[2] ||
            bbox[3] < boundsBox[1] ||
            bbox[1] > boundsBox[3]
        );
    }

    // Clip polygon features to the study bounds, dropping anything outside.
    function clipToBounds(turf, features, boundsBox) {
        var clipped = [];
        (features || []).forEach(function (f) {
            var geom = f && f.geometry;
            if (!geom || (geom.type !== 'Polygon' && geom.type !== 'MultiPolygon')) return;
            var bb;
            try {
                bb = turf.bbox(f);
            } catch (e) {
                return;
            }
            if (!bb || !bboxOverlapsBounds(bb, boundsBox)) return;
            try {
                var c = turf.bboxClip(f, boundsBox);
                if (c && c.geometry && turf.area(c) > 0) clipped.push(c);
            } catch (e) {
                // skip malformed geometry rather than failing the whole stat
            }
        });
        return clipped;
    }

    // Dissolve features into a single geometry. Returns null when the union
    // fails, so callers can fall back to summing (approximate) areas.
    function unionAll(turf, features) {
        if (!features || features.length === 0) return null;
        if (features.length === 1) return features[0];
        var acc = features[0];
        for (var i = 1; i < features.length; i++) {
            try {
                var merged = turf.union(turf.featureCollection([acc, features[i]]));
                if (merged && merged.geometry) acc = merged;
            } catch (e) {
                return null;
            }
        }
        return acc;
    }

    // Distance check against green spaces: exact distance only for candidates
    // whose (degree-padded) bbox could be within maxMeters, which keeps the
    // building x green-space loop cheap for city-wide layers.
    function isWithinGreenSpace(turf, point, greenSpaces, maxMeters) {
        var p = point.geometry.coordinates;
        var latPad = maxMeters / 111320;
        var cosLat = Math.max(Math.cos(p[1] * Math.PI / 180), 1e-6);
        var lonPad = maxMeters / (111320 * cosLat);
        for (var i = 0; i < greenSpaces.length; i++) {
            var entry = greenSpaces[i];
            var bb = entry.bbox;
            if (p[0] < bb[0] - lonPad || p[0] > bb[2] + lonPad ||
                p[1] < bb[1] - latPad || p[1] > bb[3] + latPad) {
                continue;
            }
            var d;
            try {
                var gs = entry.feature;
                if (gs.geometry.type === 'Polygon' || gs.geometry.type === 'MultiPolygon') {
                    // pointToPolygonDistance is negative when the point is
                    // inside the polygon (turf >= 7), which still satisfies
                    // the "within" check.
                    d = turf.pointToPolygonDistance(point, gs, { units: 'meters' });
                } else {
                    d = turf.distance(point, turf.centroid(gs), { units: 'meters' });
                }
            } catch (e) {
                continue;
            }
            if (d <= maxMeters) return true;
        }
        return false;
    }

    // Share of the study area within GREEN_SPACE_DISTANCE_M of a green space.
    // Only used when the buildings layer is unavailable (mirrors the backend's
    // coverage_gap statistic). Returns null if it cannot be computed.
    function greenSpaceCoveragePct(turf, prepared) {
        if (!prepared.greenSpaces.length || !(prepared.studyAreaSize > 0)) return null;
        try {
            var greenFeatures = prepared.greenSpaces.map(function (entry) {
                return entry.feature;
            });
            var greenUnion = unionAll(turf, greenFeatures);
            if (!greenUnion) return null;
            var buffered = turf.buffer(greenUnion, GREEN_SPACE_DISTANCE_M, { units: 'meters' });
            if (!buffered) return null;
            var inside = turf.intersect(
                turf.featureCollection([turf.bboxPolygon(prepared.boundsBox), buffered])
            );
            var covered = inside ? turf.area(inside) : 0;
            return Math.min(100, Math.round((covered / prepared.studyAreaSize) * 100));
        } catch (e) {
            return null;
        }
    }

    function computeRule300(turf, prepared) {
        if (!prepared.greenSpaces.length) {
            return { text: 'Layer unavailable', badgeClass: 'bg-secondary' };
        }
        var buildings = prepared.buildingsInBounds;
        if (buildings.length > 0) {
            var within = 0;
            buildings.forEach(function (b) {
                var centroid;
                try {
                    centroid = turf.centroid(b);
                } catch (e) {
                    return;
                }
                if (isWithinGreenSpace(turf, centroid, prepared.greenSpaces, GREEN_SPACE_DISTANCE_M)) {
                    within += 1;
                }
            });
            var pct = Math.round((within / buildings.length) * 100);
            return {
                text: pct + '% / buildings \u2264 300 m',
                badgeClass: pct >= 100 ? 'bg-success' : 'bg-danger',
            };
        }
        var coveragePct = greenSpaceCoveragePct(turf, prepared);
        if (coveragePct === null) {
            return { text: 'Layer unavailable', badgeClass: 'bg-secondary' };
        }
        return {
            text: coveragePct + '% / area \u2264 300 m',
            badgeClass: coveragePct >= 100 ? 'bg-success' : 'bg-danger',
        };
    }

    function computeRule30(turf, treePoints, prepared) {
        var studyAreaSize = prepared.studyAreaSize;
        if (!(studyAreaSize > 0)) {
            return { text: '\u2014', badgeClass: 'bg-secondary' };
        }

        var treeCircles = treePoints.map(function (tree) {
            var r = (tree.properties && tree.properties.crown_radius) || DEFAULT_CROWN_RADIUS_M;
            return turf.circle(tree.geometry.coordinates, r, { units: 'meters' });
        });

        var treeArea = 0;
        var treeUnion = null;
        if (treeCircles.length > 0) {
            if (treeCircles.length <= TREE_UNION_LIMIT) {
                treeUnion = unionAll(turf, treeCircles);
            }
            if (treeUnion) {
                try {
                    treeUnion = turf.bboxClip(treeUnion, prepared.boundsBox);
                } catch (e) {
                    // keep the unclipped union; the error is a boundary sliver
                }
                treeArea = turf.area(treeUnion);
            } else {
                // union unavailable/slow: sum circle areas (slight overcount
                // where drawn crowns overlap)
                treeArea = treeCircles.reduce(function (sum, c) {
                    return sum + turf.area(c);
                }, 0);
            }
        }

        var canopyArea;
        if (prepared.canopyGeometry && treeUnion) {
            var combined = unionAll(turf, [prepared.canopyGeometry, treeUnion]);
            canopyArea = combined ? turf.area(combined) : prepared.canopyArea + treeArea;
        } else {
            canopyArea = prepared.canopyArea + treeArea;
        }

        var canopyPct = Math.min(100, (canopyArea / studyAreaSize) * 100);
        return {
            text: canopyPct.toFixed(1) + '% / 30%',
            badgeClass: canopyPct >= 30 ? 'bg-success' : 'bg-danger',
        };
    }

    function computeRule3(turf, treePoints, prepared) {
        if (prepared.buildingsInBounds.length === 0) {
            // Fallback: average number of tree neighbours within 50 m of each tree
            if (treePoints.length === 0) {
                return { text: 'no trees', badgeClass: 'bg-secondary' };
            }
            var treeFC = turf.featureCollection(treePoints);
            var totalNeighbours = 0;
            treePoints.forEach(function (tree) {
                var buf = turf.circle(tree.geometry.coordinates, TREE_VIEW_DISTANCE_M, { units: 'meters' });
                var within = turf.pointsWithinPolygon(treeFC, buf);
                totalNeighbours += Math.max(0, within.features.length - 1);
            });
            var avg = (totalNeighbours / treePoints.length).toFixed(1);
            return {
                text: 'avg ' + avg + ' trees / 50 m',
                badgeClass: parseFloat(avg) >= 3 ? 'bg-success' : 'bg-danger',
            };
        }

        // % of buildings (within the study bounds) with >=3 trees within 50 m
        // of their centroid — mirrors the backend site evaluation.
        var treeFC = turf.featureCollection(treePoints);
        var metBuildings = 0;
        prepared.buildingsInBounds.forEach(function (b) {
            var bc;
            try {
                bc = turf.centroid(b);
            } catch (e) {
                return;
            }
            var buf = turf.circle(bc.geometry.coordinates, TREE_VIEW_DISTANCE_M, { units: 'meters' });
            var within = turf.pointsWithinPolygon(treeFC, buf);
            if (within.features.length >= 3) metBuildings += 1;
        });
        var pct = Math.round((metBuildings / prepared.buildingsInBounds.length) * 100);
        return {
            text: pct + '% / buildings \u22653 trees',
            badgeClass: pct >= 100 ? 'bg-success' : 'bg-danger',
        };
    }

    /**
     * Pre-process the static analytical layers for a study area.
     * Expensive operations (bbox filtering, clipping, dissolving canopy,
     * Rule 300 building distances) happen once here, not on every tree edit.
     *
     * @param {object} turf       the turf namespace
     * @param {object} layers     { existingCanopy, greenSpaces, buildings } feature arrays
     * @param {number[]} boundsBox [minx, miny, maxx, maxy] (WGS84)
     */
    function prepareLayers(turf, layers, boundsBox) {
        layers = layers || {};
        var prepared = {
            boundsBox: boundsBox,
            studyAreaSize: Math.max(0, turf.area(turf.bboxPolygon(boundsBox))),
            buildingsInBounds: [],
            greenSpaces: [],
            canopyGeometry: null,
            canopyArea: 0,
            rule300: { text: 'Layer unavailable', badgeClass: 'bg-secondary' },
        };

        // Rule 3 — filter the (often city-wide) buildings layer to the study area
        (layers.buildings || []).forEach(function (b) {
            try {
                if (bboxOverlapsBounds(turf.bbox(b), boundsBox)) {
                    prepared.buildingsInBounds.push(b);
                }
            } catch (e) {
                // skip malformed feature
            }
        });

        // Rule 300 — precompute green-space bboxes for cheap distance checks.
        // Keep only green spaces whose 300 m neighbourhood can reach the study
        // area, so the per-building check stays cheap for city-wide layers.
        var distancePadDeg = GREEN_SPACE_DISTANCE_M / 111320;
        var greenEntries = [];
        (layers.greenSpaces || []).forEach(function (gs) {
            if (!gs || !gs.geometry) return;
            var bb;
            try {
                bb = turf.bbox(gs);
            } catch (e) {
                return; // skip malformed feature
            }
            greenEntries.push({ feature: gs, bbox: bb });
        });
        prepared.greenSpaces = greenEntries.filter(function (entry) {
            return bboxOverlapsBounds(
                [
                    entry.bbox[0] - distancePadDeg,
                    entry.bbox[1] - distancePadDeg,
                    entry.bbox[2] + distancePadDeg,
                    entry.bbox[3] + distancePadDeg,
                ],
                boundsBox
            );
        });

        // Rule 30 — clip existing canopy to the study area and dissolve it so
        // overlaps (and multi-part features) are not double counted
        var clippedCanopy = clipToBounds(turf, layers.existingCanopy, boundsBox);
        if (clippedCanopy.length > 0) {
            if (clippedCanopy.length > CANOPY_UNION_LIMIT) {
                prepared.canopyArea = clippedCanopy.reduce(function (sum, f) {
                    return sum + turf.area(f);
                }, 0);
            } else {
                var merged = unionAll(turf, clippedCanopy);
                if (merged) {
                    prepared.canopyGeometry = merged;
                    prepared.canopyArea = turf.area(merged);
                } else {
                    prepared.canopyArea = clippedCanopy.reduce(function (sum, f) {
                        return sum + turf.area(f);
                    }, 0);
                }
            }
        }

        prepared.rule300 = computeRule300(turf, prepared);
        return prepared;
    }

    function computeCompliance(turf, treePoints, prepared) {
        treePoints = (treePoints || []).filter(function (f) {
            return f && f.geometry && f.geometry.type === 'Point';
        });
        return {
            rule3: computeRule3(turf, treePoints, prepared),
            rule30: computeRule30(turf, treePoints, prepared),
            rule300: prepared.rule300,
        };
    }

    global.ComplianceCore = {
        DEFAULT_CROWN_RADIUS_M: DEFAULT_CROWN_RADIUS_M,
        prepareLayers: prepareLayers,
        computeCompliance: computeCompliance,
    };
})(self);
