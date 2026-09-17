// Phase 6c item C — the leaf shader, the crown-bent normals and the runtime tree LOD.
//
// WHAT THE ROUND-15 FRAME LOOKED LIKE, and why each piece is here (docs/briefs/phase6c_foliage.md):
//   * the near trees read as FLAT CARDS.  Each leaf card carries its own card normal, so a crown is a
//     pile of randomly-facing quads and the whole canopy shades to one average: no light side, no
//     shaded side, no silhouette.  Real canopies shade roughly like a sphere, which is what the
//     CROWN-BENT NORMAL gives: N = normalize( mix( cardNormal, radial, blend ) ), radial being the
//     direction from the crown's centre to the vertex.  `blend` is a look control, `?leafnormal=`.
//   * no light came THROUGH a leaf.  The Phase 5 material is a Mix Shader between a Principled BSDF
//     and a Translucent BSDF at a per-material factor (scripts/mat_build.py `leaf_material`), i.e. a
//     fraction of the leaf's diffuse response is moved to the BACK hemisphere.  The viewer reproduces
//     exactly that mix and nothing more - no forward-scatter phase function, no rim boost - because
//     the acceptance reference is a Cycles frame of that same mix, and anything extra would be light
//     the reference does not have.
//   * the card EDGES were a hard binary cut at the manifest's alphaTest.  `alphaToCoverage` keeps the
//     cutoff and lets three's own alphatest chunk resolve the boundary texel across the MSAA samples
//     (the composer's target and the Reflector's are both `samples: 4`).
//
// THE TRANSLUCENT TERM, derived.  Blender: surface = (1-t)*Principled + t*Translucent(colour = base *
// `translucent`).  Cycles' Translucent BSDF is a Lambert lobe on -N.  three's direct diffuse is
//     dotNL * lightColour * RECIPROCAL_PI * diffuseColor
// so the mix is reproduced by ADDING the back lobe at t and SUBTRACTING t of the front lobe:
//     delta = sunIrr * RECIPROCAL_PI * base * ( t * tint * max( dot( -N, L ), 0 )
//                                             - t * frontSub * max( dot( N, L ), 0 ) )
// `frontSub` is 1 where the front sun diffuse is still in the shader and 0 where it is not.
//
// WHY THE SHRUB / REED CARDS GET NO TRANSLUCENT TERM BY DEFAULT.  Their material is patched by
// `applyInstanceIrradiance` with `specularOnlySun: true`, so they have NO direct sun diffuse at all:
// their diffuse is one baked scene-linear irradiance per PLACEMENT, added with no cosine.  A
// direction-independent irradiance is already the two-sided model that translucency approximates -
// front and back faces of those cards receive the same light today - and the sun is already inside
// that baked value.  Adding a directional back lobe there would be light the bake has counted once
// already, and it would break the round-15 cam02 level (104.5 against the reference's 106.0, 0.99x).
// They do get the crown-bent normals (their specular and the 7 cov == 0 probe cards see it) and the
// soft edges.  `?leaftrn=shrubs` forces the term on for the A/B; the measurement is in web/README.md.
//
// CROWNS ARE FOUND, NOT ASSUMED.  gltfpack dropped every node name and the export MERGED several
// trees into single primitives (MAT_bark_cypress mesh_26 spans 229 m, MAT_leaf_cypress mesh_29 spans
// 230 m), so "one primitive = one tree" is false and a bbox centre would sit in mid-air between
// trees.  Each geometry's vertices are therefore flood-filled on a coarse XZ grid into CONNECTED
// CLUSTERS, one per crown, and every vertex carries its own cluster's centre in `pfaCrown`.  That one
// attribute then serves both jobs: the normal bend at load, and the runtime LOD distance in the
// vertex shader (so a merged mesh switches per TREE, not per primitive, with no per-frame CPU work).
import * as THREE from 'three';

/** Card materials, by the name the export writes (clones keep the name). */
export const LEAF_RE = /^MAT_leaf_[a-z]+$/;
export const CARD_RE = /^MAT_(shrub(_light|_dry)?|reeds)$/;
export const BARK_RE = /^MAT_bark_[a-z]+$/;
export const isFoliage = ( n ) => LEAF_RE.test( n || '' ) || CARD_RE.test( n || '' );
export const isTreeMat = ( n ) => isFoliage( n ) || BARK_RE.test( n || '' );

/**
 * The Phase 5 constants, read off `scripts/mat_build.py` (`leaf_material(...)` calls, lines 1738-1757):
 * `trn` is the Mix Shader factor and `tint` the multiplier on the base colour that feeds the
 * Translucent BSDF.  In Blender the factor is further modulated per texel by the `*_trn` mask mapped
 * 0.05..0.85 -> 0.35..1.55; that map is export item D and is NOT shipped yet, so the constant stands
 * alone here (mean of the map ~ 1) and this table is replaced by the mask when it lands.
 */
export const PHASE5_LEAF = {
	MAT_leaf_cypress:    { trn: 0.25, tint: [ 0.90, 1.10, 0.50 ] },
	MAT_leaf_pine:       { trn: 0.18, tint: [ 0.70, 0.95, 0.50 ] },
	MAT_leaf_eucalyptus: { trn: 0.30, tint: [ 0.80, 1.00, 0.50 ] },
	MAT_leaf_broadleaf:  { trn: 0.35, tint: [ 0.80, 1.20, 0.40 ] },
	MAT_shrub:           { trn: 0.34, tint: [ 0.85, 1.15, 0.60 ] },
	MAT_shrub_light:     { trn: 0.40, tint: [ 0.90, 1.10, 0.70 ] },
	MAT_shrub_dry:       { trn: 0.22, tint: [ 1.05, 0.95, 0.50 ] },
	MAT_reeds:           { trn: 0.45, tint: [ 0.95, 1.05, 0.60 ] },
};

/** species token -> the impostor prototypes that may stand in for it (C2, near trees only). */
const SPECIES_OF = { MAT_leaf_cypress: 'cypress', MAT_leaf_pine: 'pine',
	MAT_leaf_eucalyptus: 'eucalyptus', MAT_leaf_broadleaf: 'broadleaf' };

const CLUSTER_CELL = 6.0;          // m, the flood-fill grid; > the gap inside one crown, < the gap between two
const PAIR_MAX_M = 9.0;            // m, how far a trunk cluster may be from its crown

function once( src, needle, replacement, what ) {
	const n = src.split( needle ).length - 1;
	if ( n !== 1 ) throw new Error( `foliage patch "${what}": expected 1 occurrence, found ${n}` );
	return src.replace( needle, replacement );
}

// ---------------------------------------------------------------- crown clustering

/**
 * Flood-fill a geometry's vertices into connected crowns on a CLUSTER_CELL grid in object-space XZ.
 * @returns {{ ids:Int32Array, centres:Float32Array, boxes:THREE.Box3[], count:number }}
 */
export function clusterCrowns( geometry, cell = CLUSTER_CELL ) {
	const pos = geometry.getAttribute( 'position' );
	const n = pos.count;
	const cells = new Map();                    // "i,k" -> cell index
	const cellOf = new Int32Array( n );
	const keys = [];
	for ( let v = 0; v < n; v ++ ) {
		const i = Math.floor( pos.getX( v ) / cell ), k = Math.floor( pos.getZ( v ) / cell );
		const key = `${i},${k}`;
		let c = cells.get( key );
		if ( c === undefined ) { c = keys.length; cells.set( key, c ); keys.push( [ i, k ] ); }
		cellOf[ v ] = c;
	}
	// 8-neighbour flood fill over the occupied cells
	const comp = new Int32Array( keys.length ).fill( - 1 );
	let count = 0;
	for ( let c = 0; c < keys.length; c ++ ) {
		if ( comp[ c ] >= 0 ) continue;
		const id = count ++;
		const stack = [ c ];
		comp[ c ] = id;
		while ( stack.length ) {
			const [ i, k ] = keys[ stack.pop() ];
			for ( let di = - 1; di <= 1; di ++ ) for ( let dk = - 1; dk <= 1; dk ++ ) {
				if ( ! di && ! dk ) continue;
				const nb = cells.get( `${i + di},${k + dk}` );
				if ( nb === undefined || comp[ nb ] >= 0 ) continue;
				comp[ nb ] = id; stack.push( nb );
			}
		}
	}
	const boxes = []; for ( let i = 0; i < count; i ++ ) boxes.push( new THREE.Box3() );
	const ids = new Int32Array( n );
	const v3 = new THREE.Vector3();
	for ( let v = 0; v < n; v ++ ) {
		const id = comp[ cellOf[ v ] ];
		ids[ v ] = id;
		boxes[ id ].expandByPoint( v3.set( pos.getX( v ), pos.getY( v ), pos.getZ( v ) ) );
	}
	const centres = new Float32Array( count * 3 );
	for ( let i = 0; i < count; i ++ ) {
		boxes[ i ].getCenter( v3 );
		centres[ i * 3 ] = v3.x; centres[ i * 3 + 1 ] = v3.y; centres[ i * 3 + 2 ] = v3.z;
	}
	// The mean of COLOR_0 per cluster, RAW (still gamma-2 coded).  On the near trees COLOR_0 is the
	// BAKED IRRADIANCE at the vertex (lightmaps.vertex_irradiance), so this is the one measurement of
	// "what light does this tree actually stand in" the viewer already owns - the impostor
	// modulation's E_placement until the bake ships the far trees' own values.
	const col = geometry.getAttribute( 'color' );
	let colourMean = null;
	if ( col && col.itemSize >= 3 ) {
		const sum = new Float64Array( count * 3 ), nv = new Float64Array( count );
		// The encode is gamma-2 (v = c*c*range), so the mean is taken on the DECODED value: the mean
		// of c and the mean of c*c are not the same number and only the second is an irradiance.
		for ( let v = 0; v < n; v ++ ) {
			const id = ids[ v ], x = col.getX( v ), y = col.getY( v ), z = col.getZ( v );
			sum[ id * 3 ] += x * x; sum[ id * 3 + 1 ] += y * y; sum[ id * 3 + 2 ] += z * z;
			nv[ id ] ++;
		}
		colourMean = new Float32Array( count * 3 );
		for ( let i = 0; i < count; i ++ ) for ( let k = 0; k < 3; k ++ )
			colourMean[ i * 3 + k ] = nv[ i ] ? sum[ i * 3 + k ] / nv[ i ] : 0;
	}
	return { ids, centres, boxes, count, colourMean };
}

/**
 * Write `pfaCrown` (the vertex's own crown centre, object space) and, for foliage geometry, replace
 * the normals with the crown-bent ones.  Idempotent per geometry.
 */
function prepareGeometry( geo, bend, cache ) {
	const hit = cache.get( geo.uuid );
	if ( hit ) return hit;
	const cl = clusterCrowns( geo );
	const pos = geo.getAttribute( 'position' );
	const n = pos.count;
	const crown = new Float32Array( n * 3 );
	for ( let v = 0; v < n; v ++ ) {
		const c = cl.ids[ v ] * 3;
		crown[ v * 3 ] = cl.centres[ c ]; crown[ v * 3 + 1 ] = cl.centres[ c + 1 ]; crown[ v * 3 + 2 ] = cl.centres[ c + 2 ];
	}
	geo.setAttribute( 'pfaCrown', new THREE.BufferAttribute( crown, 3 ) );
	if ( bend > 0 ) {
		const nrm = geo.getAttribute( 'normal' );
		const out = new Float32Array( n * 3 );
		const a = new THREE.Vector3(), r = new THREE.Vector3();
		for ( let v = 0; v < n; v ++ ) {
			a.set( nrm.getX( v ), nrm.getY( v ), nrm.getZ( v ) ).normalize();
			r.set( pos.getX( v ) - crown[ v * 3 ], pos.getY( v ) - crown[ v * 3 + 1 ], pos.getZ( v ) - crown[ v * 3 + 2 ] );
			// A vertex AT the centre has no radial direction: it keeps its card normal.
			if ( r.lengthSq() > 1e-8 ) { r.normalize(); a.lerp( r, bend ); if ( a.lengthSq() < 1e-8 ) a.copy( r ); a.normalize(); }
			out[ v * 3 ] = a.x; out[ v * 3 + 1 ] = a.y; out[ v * 3 + 2 ] = a.z;
		}
		geo.setAttribute( 'normal', new THREE.BufferAttribute( out, 3 ) );
	}
	cache.set( geo.uuid, cl );
	return cl;
}

// ---------------------------------------------------------------- the shader patch

const HASH_GLSL = /* glsl */`
	// Interleaved gradient noise: a purely SPATIAL hash, so the LOD dissolve is a fixed dither
	// pattern and a screenshot of the same frame is byte-identical twice running.
	float pfaHash( vec2 p ) { return fract( 52.9829189 * fract( dot( p, vec2( 0.06711056, 0.00583715 ) ) ) ); }
`;

/**
 * Patch one foliage / bark MeshStandardMaterial: the LOD dissolve (all tree materials) and the
 * translucent mix (materials with a Phase 5 constant and `frontSub` resolved by the caller).
 */
function patchFoliageMaterial( mat, { shared, trn, tint, frontSub, fade, dist, band, sign = 1 } ) {
	if ( mat.userData.pfaFoliage ) return false;
	const u = {
		pfaTrnFac: { value: trn },
		pfaTrnTint: { value: new THREE.Vector3( ...tint ) },
		pfaFrontSub: { value: frontSub },
		// Per MATERIAL, not shared: the trees switch at `treeMeshDist` and the shrub/reed cards at
		// `shrubLodDist`, and a LOD2 set is the same switch with the sign flipped.
		pfaSwitchDist: { value: Number.isFinite( dist ) ? dist : 1e9 },
		pfaSwitchBand: { value: Math.max( band, 1e-3 ) },
		pfaSwitchSign: { value: sign },
	};
	mat.userData.pfaFoliage = { trn, tint, frontSub, fade, dist, band, sign, uniforms: u };
	const prev = mat.onBeforeCompile;
	mat.onBeforeCompile = function ( shader, renderer ) {
		if ( prev ) prev.call( this, shader, renderer );
		Object.assign( shader.uniforms, u, shared.uniforms );
		if ( fade ) {
			shader.vertexShader = once( shader.vertexShader, '#include <common>',
				'#include <common>\nattribute vec3 pfaCrown;\nuniform float pfaSwitchDist;\nuniform float pfaSwitchBand;\n'
				+ 'uniform float pfaSwitchSign;\nvarying float vPfaFade;', 'fade attributes (vertex)' );
			shader.vertexShader = once( shader.vertexShader, '#include <worldpos_vertex>',
				'#include <worldpos_vertex>\n\t{\n\t\tvec4 pfaC = vec4( pfaCrown, 1.0 );\n'
				+ '\t\t#ifdef USE_INSTANCING\n\t\tpfaC = instanceMatrix * pfaC;\n\t\t#endif\n'
				+ '\t\tvec3 pfaCw = ( modelMatrix * pfaC ).xyz;\n'
				+ '\t\tfloat pfaT = smoothstep( pfaSwitchDist, pfaSwitchDist + pfaSwitchBand, distance( cameraPosition, pfaCw ) );\n'
				+ '\t\tvPfaFade = ( pfaSwitchSign > 0.0 ) ? 1.0 - pfaT : pfaT;\n\t}',
				'fade distance (vertex)' );
			shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
				`#include <common>\nvarying float vPfaFade;${HASH_GLSL}`, 'fade varying (fragment)' );
			// BEFORE the alpha test, so a dissolved fragment costs nothing further.  The dissolve is
			// stochastic rather than a coverage ramp because a card's alpha is a TEXTURE and three's
			// alphaToCoverage smoothstep would turn a constant per-tree factor back into a hard step.
			shader.fragmentShader = once( shader.fragmentShader, '#include <alphatest_fragment>',
				'if ( vPfaFade < 0.9995 && pfaHash( gl_FragCoord.xy ) > vPfaFade ) discard;\n\t#include <alphatest_fragment>',
				'LOD dissolve' );
		}
		if ( trn > 0 ) {
			shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
				'#include <common>\nuniform float pfaTrnFac;\nuniform vec3 pfaTrnTint;\nuniform float pfaFrontSub;\n'
				+ 'uniform vec3 pfaSunDir;\nuniform vec3 pfaSunIrr;', 'translucency uniforms' );
			shader.fragmentShader = once( shader.fragmentShader, '#include <lights_fragment_end>',
				'#include <lights_fragment_end>\n\t{\n'
				+ '\t\tvec3 pfaL = normalize( ( viewMatrix * vec4( pfaSunDir, 0.0 ) ).xyz );\n'
				+ '\t\tfloat pfaBack = max( dot( - normal, pfaL ), 0.0 );\n'
				+ '\t\tfloat pfaFront = max( dot( normal, pfaL ), 0.0 );\n'
				+ '\t\treflectedLight.directDiffuse += pfaSunIrr * RECIPROCAL_PI * diffuseColor.rgb * pfaTrnFac\n'
				+ '\t\t\t* ( pfaTrnTint * pfaBack - pfaFrontSub * pfaFront );\n\t}',
				'translucent mix' );
		}
	};
	const prevKey = mat.customProgramCacheKey;
	mat.customProgramCacheKey = function () {
		// `sign`, `dist` and `band` are UNIFORMS, so they do not belong in the program key.
		return `${prevKey ? prevKey.call( this ) : ''}|fol:${trn.toFixed( 3 )}:${frontSub}:${fade ? 1 : 0}`;
	};
	mat.needsUpdate = true;
	return true;
}

// ---------------------------------------------------------------- the pass

/**
 * @param {object} o
 * @param {THREE.Scene} o.scene
 * @param {THREE.DirectionalLight} o.sun
 * @param {boolean} o.msaa           the render target is multisampled (alphaToCoverage is worth it)
 * @param {number} o.normalBlend     0 = the card normals as exported, 1 = a pure crown sphere
 * @param {number} o.trnScale        multiplies every Phase 5 translucency constant (?leaftrn=)
 * @param {boolean} o.trnShrubs      also give the shrub/reed cards the directional back lobe
 * @param {number} o.meshDist        metres: within it a tree draws its mesh (Infinity = always mesh)
 * @param {number} o.fadeBand        metres of crossfade beyond meshDist
 */
export function applyFoliage( o ) {
	const { scene, sun, note = () => {} } = o;
	const bend = o.normalBlend ?? 0.5;
	const trnScale = o.trnScale ?? 1.0;
	const meshDist = o.meshDist ?? 40;
	const fadeBand = o.fadeBand ?? 5;
	// range x scale: the whole decode of COLOR_0 into scene-linear irradiance, from the manifest.
	const vertexIrrScale = o.vertexIrrScale ?? 0;
	const report = { geometries: 0, clusters: 0, leafMaterials: 0, cardMaterials: 0, barkMaterials: 0,
		bent: 0, softened: 0, units: [], normalBlend: bend, trnScale, meshDist, fadeBand,
		trnShrubs: !! o.trnShrubs, msaa: !! o.msaa, skipped: [], vertexIrrScale };
	const shared = { uniforms: {
		pfaMeshDist: { value: Number.isFinite( meshDist ) ? meshDist : 1e9 },
		pfaFadeBand: { value: Math.max( fadeBand, 1e-3 ) },
		pfaSunDir: { value: sun ? sun.position.clone().normalize() : new THREE.Vector3( 0, 1, 0 ) },
		// three folds a light's intensity into its colour uniform, so this is the same vector the
		// built-in direct term uses; the sun is the only analytic light in the scene.
		pfaSunIrr: { value: sun ? sun.color.clone().multiplyScalar( sun.intensity ) : new THREE.Color( 0, 0, 0 ) },
	} };
	report.shared = shared;

	const cache = new Map();          // geometry uuid -> its clustering
	const seenMat = new Set();
	const meshes = [];
	scene.updateMatrixWorld( true );  // the unit list is world space and is read once, here
	scene.traverse( ( m ) => {
		if ( ! m.isMesh || ! m.material ) return;
		const mats = Array.isArray( m.material ) ? m.material : [ m.material ];
		if ( ! mats.some( ( x ) => x && isTreeMat( x.name ) ) ) return;
		meshes.push( { mesh: m, mats } );
	} );

	for ( const { mesh, mats } of meshes ) {
		const foliage = mats.some( ( x ) => x && isFoliage( x.name ) );
		let cl;
		try { cl = prepareGeometry( mesh.geometry, foliage ? bend : 0, cache ); }
		catch ( e ) { report.skipped.push( `${mesh.name}: ${e.message}` ); continue; }
		if ( foliage && bend > 0 ) report.bent ++;
		for ( const mat of mats ) {
			if ( ! mat || ! mat.isMeshStandardMaterial || seenMat.has( mat.uuid ) ) continue;
			seenMat.add( mat.uuid );
			const p5 = PHASE5_LEAF[ mat.name ];
			const leaf = LEAF_RE.test( mat.name || '' );
			const card = CARD_RE.test( mat.name || '' );
			// The front sun diffuse is only there to be taken away where the material still HAS it:
			// `specularOnlySun` (the shrub/reed patch) has already removed it.
			const specOnly = !! ( mat.userData.pfaPatched && mat.userData.pfaPatched.specularOnlySun );
			const wantTrn = p5 && ( leaf || ( card && o.trnShrubs ) );
			const trn = wantTrn ? p5.trn * trnScale : 0;
			patchFoliageMaterial( mat, {
				shared, trn, tint: p5 ? p5.tint : [ 1, 1, 1 ],
				frontSub: specOnly ? 0 : 1, fade: true,
				// The trees switch to their impostor at `meshDist`; the shrub/reed cards have no
				// second LOD until export item E lands, so they are patched with the SAME shader and
				// an infinite distance, and `applyShrubLod` only has to move a uniform.
				dist: card ? Infinity : meshDist, band: fadeBand, sign: 1,
			} );
			// Soft edges: keep the export's MASK cutoff exactly, let three resolve the boundary texel
			// across the MSAA samples instead of cutting it binary.
			if ( o.msaa && mat.alphaTest > 0 ) { mat.alphaToCoverage = true; report.softened ++; }
			if ( leaf ) report.leafMaterials ++; else if ( card ) report.cardMaterials ++; else report.barkMaterials ++;
		}
	}
	report.geometries = cache.size;
	for ( const cl of cache.values() ) report.clusters += cl.count;

	// ---- the tree units: one per crown cluster per instance, in world space -----------------
	const box = new THREE.Box3(), mtx = new THREE.Matrix4();
	const crowns = [], trunks = [];
	for ( const { mesh, mats } of meshes ) {
		const cl = cache.get( mesh.geometry.uuid );
		if ( ! cl ) continue;
		const leafMat = mats.find( ( x ) => x && LEAF_RE.test( x.name || '' ) );
		const barkOnly = ! leafMat && mats.some( ( x ) => x && BARK_RE.test( x.name || '' ) );
		if ( ! leafMat && ! barkOnly ) continue;         // shrub / reed cards are not trees
		const n = mesh.isInstancedMesh ? mesh.count : 1;
		for ( let i = 0; i < n; i ++ ) {
			if ( mesh.isInstancedMesh ) mtx.fromArray( mesh.instanceMatrix.array, i * 16 ).premultiply( mesh.matrixWorld );
			else mtx.copy( mesh.matrixWorld );
			for ( let c = 0; c < cl.count; c ++ ) {
				box.copy( cl.boxes[ c ] ).applyMatrix4( mtx );
				const centre = box.getCenter( new THREE.Vector3() ), size = box.getSize( new THREE.Vector3() );
				const cm = cl.colourMean;
				const rec = { centre, minY: box.min.y, maxY: box.max.y, width: Math.max( size.x, size.z ),
					mesh: mesh.name, instance: i, material: leafMat ? leafMat.name : null,
					// decoded with the ONE global range the manifest declares x lightmaps.scale
					irradiance: ( cm && vertexIrrScale > 0 )
						? [ cm[ c * 3 ] * vertexIrrScale, cm[ c * 3 + 1 ] * vertexIrrScale, cm[ c * 3 + 2 ] * vertexIrrScale ]
						: null };
				( leafMat ? crowns : trunks ).push( rec );
			}
		}
	}
	// pair each crown with the nearest trunk cluster, so the impostor's height is the WHOLE tree
	for ( const c of crowns ) {
		let best = null, bestD = PAIR_MAX_M;
		for ( const t of trunks ) {
			const d = Math.hypot( t.centre.x - c.centre.x, t.centre.z - c.centre.z );
			if ( d < bestD ) { bestD = d; best = t; }
		}
		report.units.push( {
			centre: c.centre, crownY: c.centre.y, width: Math.max( c.width, best ? best.width : c.width ),
			baseY: best ? Math.min( best.minY, c.minY ) : c.minY,
			topY: Math.max( c.maxY, best ? best.maxY : c.maxY ),
			species: SPECIES_OF[ c.material ] || null, mesh: c.mesh, instance: c.instance,
			trunkDist_m: best ? bestD : null, irradiance: c.irradiance,
		} );
	}
	note( `foliage: ${report.geometries} geometr(ies) clustered into ${report.clusters} crown(s), `
		+ `normals bent ${bend.toFixed( 2 )} toward the crown centre on ${report.bent} mesh(es); `
		+ `${report.leafMaterials} leaf + ${report.cardMaterials} card + ${report.barkMaterials} bark material(s) patched, `
		+ `${report.softened} on alphaToCoverage (${o.msaa ? 'MSAA target' : 'no MSAA: hard cut kept'}); `
		+ `translucency x${trnScale} from the Phase 5 constants`
		+ ( o.trnShrubs ? ' (shrub/reed cards INCLUDED, ?leaftrn=shrubs)' : ' (shrub/reed cards excluded: their diffuse is the direction-independent baked placement irradiance)' )
		+ `; ${report.units.length} near-tree unit(s) found, LOD switch at ${Number.isFinite( meshDist ) ? `${meshDist} m + ${fadeBand} m fade` : 'never (mesh always)'}` );
	if ( report.skipped.length ) note( `foliage: ${report.skipped.length} mesh(es) skipped: ${report.skipped.slice( 0, 4 ).join( '; ' )}` );
	return report;
}

/**
 * C3 — shrub / reed LOD: LOD1 within `dist` metres of the walker, LOD2 beyond, both sharing the
 * placement's baked irradiance.  The meshes come from export item E; until they land this is a code
 * path with nothing to switch, and it says so rather than pretending.
 *
 * THE CONTRACT IT READS (gltfpack drops node names, so the manifest must name the nodes, never a
 * string in the glb).  Either of:
 *   `raw.shrub_lod = { dist_m?, lod1_nodes: [n, ...], lod2_nodes: [n, ...] }`   (glTF node indices
 *       into env.glb, the same index space as `lightmaps.instance_irradiance.nodes[].gltf_node`), or
 *   a `lod` field of "LOD1" / "LOD2" on each `lightmaps.instance_irradiance.nodes[]` entry.
 * Both are joined through `mesh.userData.pfaGltfNode`, exactly as the instance irradiance is, and a
 * node the scene does not present is reported, never silently skipped.
 */
export function applyShrubLod( { scene, manifest, note = () => {}, dist = 30 } ) {
	const out = { dist, lod1: 0, lod2: 0, missing: [], source: null };
	const raw = ( manifest && manifest.raw ) || {};
	const ii = ( manifest && manifest.gate3 && manifest.gate3.instanceIrradiance ) || null;
	const lod1 = new Set(), lod2 = new Set();
	if ( raw.shrub_lod && ( raw.shrub_lod.lod1_nodes || raw.shrub_lod.lod2_nodes ) ) {
		( raw.shrub_lod.lod1_nodes || [] ).forEach( ( n ) => lod1.add( n ) );
		( raw.shrub_lod.lod2_nodes || [] ).forEach( ( n ) => lod2.add( n ) );
		if ( typeof raw.shrub_lod.dist_m === 'number' && dist === 30 ) out.dist = dist = raw.shrub_lod.dist_m;
		out.source = 'shrub_lod';
	} else if ( ii && ii.nodes && ii.nodes.some( ( n ) => n.lod ) ) {
		for ( const n of ii.nodes ) {
			if ( String( n.lod ).toUpperCase() === 'LOD1' ) lod1.add( n.gltf_node );
			else if ( String( n.lod ).toUpperCase() === 'LOD2' ) lod2.add( n.gltf_node );
		}
		out.source = 'instance_irradiance.nodes[].lod';
	}
	if ( ! lod1.size && ! lod2.size ) {
		note( `shrub/reed LOD: no LOD1 set in the manifest (export item E) — every card stays on the shipped LOD2, `
			+ `switch distance ${dist} m is wired and idle (?shrublod=)` );
		return out;
	}
	const seen = new Set();
	scene.traverse( ( m ) => {
		if ( ! m.isMesh ) return;
		const gn = m.userData && m.userData.pfaGltfNode;
		if ( gn === undefined ) return;
		const sign = lod1.has( gn ) ? 1 : ( lod2.has( gn ) ? - 1 : 0 );
		if ( ! sign ) return;
		seen.add( gn );
		for ( const mat of Array.isArray( m.material ) ? m.material : [ m.material ] ) {
			const f = mat && mat.userData.pfaFoliage;
			if ( ! f ) continue;
			f.uniforms.pfaSwitchDist.value = dist;
			f.uniforms.pfaSwitchSign.value = sign;
			f.dist = dist; f.sign = sign;
			if ( sign > 0 ) out.lod1 ++; else out.lod2 ++;
		}
	} );
	for ( const n of [ ...lod1, ...lod2 ] ) if ( ! seen.has( n ) ) out.missing.push( String( n ) );
	note( `shrub/reed LOD (${out.source}): LOD1 within ${dist} m on ${out.lod1} material(s), LOD2 beyond on ${out.lod2}`
		+ ( out.missing.length ? `; node(s) NOT in the scene: ${out.missing.join( ', ' )}` : '' ) );
	return out;
}

/**
 * ∫ L dω over an equirectangular sky, as a Vector3 (scene-linear).  Used only for its CHROMATICITY:
 * it is the sky half of the irradiance the impostor atlases were baked under (`manifest.impostors.
 * lighting`: each prototype alone on a lawn under the whole open sky), and the bake's diagnosis
 * measured that light at hue 225 deg against the scene's 52 deg.
 */
export function equirectIntegral( texture ) {
	const img = texture && texture.image;
	if ( ! img || ! img.data || ! img.width || ! img.height ) return null;
	const { data, width: w, height: h } = img;
	const half = data.BYTES_PER_ELEMENT === 2;
	const ch = data.length / ( w * h );
	if ( ch < 3 ) return null;
	const get = ( i ) => ( half ? THREE.DataUtils.fromHalfFloat( data[ i ] ) : data[ i ] );
	const acc = new THREE.Vector3();
	const dTheta = Math.PI / h, dPhi = 2 * Math.PI / w;
	for ( let j = 0; j < h; j ++ ) {
		const sinT = Math.sin( ( j + 0.5 ) * dTheta ) * dTheta * dPhi;
		let r = 0, g = 0, b = 0;
		for ( let i = 0; i < w; i ++ ) {
			const k = ( j * w + i ) * ch;
			r += get( k ); g += get( k + 1 ); b += get( k + 2 );
		}
		acc.x += r * sinT; acc.y += g * sinT; acc.z += b * sinT;
	}
	return acc;
}

/**
 * C2 / the bake's impostor diagnosis: the per-placement modulation `E_placement / E_bake`.
 *
 * `mode`:
 *   'full'    the ratio as it stands - only correct once E_bake is a MEASURED value (the bake ships
 *             it per prototype in the far-tree irradiance JSON);
 *   'chroma'  the ratio normalised to unit luminance, so only the COLOUR of the light is corrected
 *             and the atlas keeps its own level.  This is the default while E_bake is the viewer's
 *             own estimate (sun + sky integral), because an estimate that is off by a factor would
 *             otherwise re-light every far tree by that factor.
 */
export function irradianceRatio( ePlacement, eBake, mode = 'chroma' ) {
	if ( ! ePlacement || ! eBake ) return null;
	const r = [ 0, 1, 2 ].map( ( i ) => ( eBake[ i ] > 1e-9 ? ePlacement[ i ] / eBake[ i ] : 1 ) );
	if ( ! r.every( ( x ) => isFinite( x ) && x > 0 ) ) return null;
	if ( mode !== 'chroma' ) return r;
	const lum = 0.2126 * r[ 0 ] + 0.7152 * r[ 1 ] + 0.0722 * r[ 2 ];
	return lum > 1e-9 ? r.map( ( x ) => x / lum ) : null;
}

/**
 * The far trees' own modulation, when the bake's JSON is in the manifest.  Contract (bake item 2 /
 * `trees.far_mesh.lighting`): `prototypes: { <name>: { E_bake: [r,g,b] } }` and a placement list
 * carrying a Blender location and an rgb, joined to `manifest.treesFar[i].base` BY LOCATION - the
 * same join the shrub irradiance uses, with the same refusal to guess when it does not land.
 */
export function farTreeIrradiance( treesFar, raw, mode, note = () => {} ) {
	const lit = raw && raw.trees && raw.trees.far_mesh && raw.trees.far_mesh.lighting;
	const rows = lit && ( lit.placements || lit.instances );
	if ( ! lit || ! Array.isArray( rows ) || ! rows.length || ! lit.prototypes ) {
		note( 'far-tree impostor modulation: the bake\'s trees.far_mesh.lighting is not in the manifest yet '
			+ '(E_placement per placement + E_bake per prototype); the far atlases draw unmodulated' );
		return { applied: 0, unmatched: 0, byIndex: new Map() };
	}
	const key = ( p ) => `${p[ 0 ].toFixed( 2 )},${p[ 1 ].toFixed( 2 )},${p[ 2 ].toFixed( 2 )}`;
	const byLoc = new Map();
	for ( const r of rows ) {
		const loc = r.location_blender || r.loc || r.location;
		if ( Array.isArray( loc ) && Array.isArray( r.rgb ) ) byLoc.set( key( loc ), r.rgb );
	}
	const byIndex = new Map();
	let unmatched = 0;
	treesFar.forEach( ( t, i ) => {
		const e = Array.isArray( t.base ) ? byLoc.get( key( t.base ) ) : null;
		const proto = lit.prototypes[ t.prototype ] || lit.prototypes[ ( raw.impostors && raw.impostors.prototype_map && raw.impostors.prototype_map[ t.prototype ] ) || t.prototype ];
		const eb = proto && ( proto.E_bake || proto.e_bake );
		const ratio = irradianceRatio( e, eb, mode );
		if ( ratio ) byIndex.set( i, ratio ); else unmatched ++;
	} );
	note( `far-tree impostor modulation: ${byIndex.size}/${treesFar.length} placement(s) joined by location `
		+ `(${unmatched} unmatched), mode ${mode}` );
	return { applied: byIndex.size, unmatched, byIndex };
}

/**
 * C2: turn the near-tree units into impostor entries in the shape `buildImpostors` reads, choosing
 * each one's prototype by SPECIES and then by the closest width/height aspect - the export dropped
 * the node names, so the material is the only species evidence in the glb, and the aspect is what
 * separates a columnar cypress from a spreading one.
 */
export function nearTreeImpostorEntries( units, impostors, note = () => {}, eBake = null, mode = 'chroma' ) {
	const out = [], chosen = {};
	if ( ! impostors || ! impostors.prototypes ) return out;
	const protos = Object.entries( impostors.prototypes );
	for ( const u of units ) {
		if ( ! u.species ) continue;
		const cands = protos.filter( ( [ k ] ) => k.toLowerCase().includes( u.species ) );
		if ( ! cands.length ) continue;
		const height = Math.max( u.topY - u.baseY, 0.1 );
		const aspect = u.width / height;
		let best = null, bestE = Infinity;
		for ( const [ k, p ] of cands ) {
			if ( ! ( p.heightAboveBase > 0 ) || ! ( p.radius > 0 ) ) continue;
			const e = Math.abs( Math.log( ( 2 * p.radius / p.heightAboveBase ) / aspect ) );
			if ( e < bestE ) { bestE = e; best = k; }
		}
		if ( ! best ) continue;
		chosen[ best ] = ( chosen[ best ] || 0 ) + 1;
		out.push( {
			prototype: best, id: `near_${u.mesh}_${u.instance}_${out.length}`, height,
			// `base` is BLENDER (x, y, z) as manifest.impostors.placement states, from the three-space
			// trunk base: three (x, y, z) -> Blender (x, -z, y).
			base: [ u.centre.x, - u.centre.z, u.baseY ],
			near: true, switchCentre: [ u.centre.x, u.centre.y, u.centre.z ],
			// E_placement is this crown's own mean COLOR_0 irradiance - the only measured "what light
			// does this tree stand in" the viewer owns until the bake ships the far trees' values.
			irr: ( mode === '0' || ! mode ) ? null : irradianceRatio( u.irradiance, eBake, mode ),
		} );
	}
	note( `near-tree impostors: ${out.length}/${units.length} unit(s) matched a prototype by species + aspect `
		+ `(${Object.entries( chosen ).map( ( [ k, v ] ) => `${k.replace( /^ENV_tree_|_LOD1$/g, '' )} x${v}` ).join( ', ' )})` );
	return out;
}
