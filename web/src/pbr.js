// Gate 2 PBR materials: the baked albedo / roughness / normal KTX2 sets from manifest v3.
//
// The Gate 1 geometry is FROZEN (export a9b2d3d), so the textures do not travel inside the glbs:
// the manifest names one texture set per material and the viewer attaches them to the materials the
// glbs already carry.  Two things matter for the capture:
//   1. MATCHING.  A glb material is named `MAT_EXP_<zone>__<source material>` (the exporter's UV1
//      atlas group), the bake may key its sets by either half; every material that finds no set is
//      listed by name in the report rather than silently left grey.
//   2. ORDER.  KTX2 files are whole-file loads (no progressive mips), so the ONLY lever on what the
//      viewer shows first is the order of the requests: nearest material to the station camera
//      first, so the hero's foreground is textured before the far shore.
//
// Colour space: the manifest states it per map; albedo is sRGB-encoded, roughness/normal/AO are
// linear data.  Compressed textures cannot be flipped by three, so flipY stays false (the glTF
// convention the bake writes to).
import * as THREE from 'three';

/** Names a bake may have used for a glb material: the full name, the part after `__`, the stem. */
export function candidateKeys( name ) {
	if ( ! name ) return [];
	const out = [ name ];
	if ( name.includes( '__' ) ) {
		out.push( name.split( '__' ).pop() );
		out.push( name.split( '__' )[ 0 ] );
	}
	const noExp = name.replace( /^MAT_EXP_/, '' );
	if ( noExp !== name ) out.push( noExp, `MAT_${noExp}` );
	return [ ...new Set( out.filter( Boolean ) ) ];
}

/** Index the manifest's sets by every key a material could match on (own name + declared aliases). */
function indexSets( sets ) {
	const byKey = new Map();
	for ( const [ name, set ] of Object.entries( sets ) ) {
		for ( const k of [ name, ...( set.aliases || [] ), ...candidateKeys( name ) ] ) if ( ! byKey.has( k ) ) byKey.set( k, set );
	}
	return byKey;
}

const _sphere = new THREE.Sphere(), _v = new THREE.Vector3(), _m4 = new THREE.Matrix4(), _c = new THREE.Vector3();

/** Nearest surface distance from `eye` to any INSTANCE of an InstancedMesh.  The whole-batch
 *  bounding sphere is useless here: a batch that spans the site contains the camera, so its
 *  distance is 0 and the load order collapses.  Per instance it is the real distance. */
function instanceDistance( o, eye ) {
	const gs = o.geometry.boundingSphere;
	if ( ! gs ) return 0;
	const arr = o.instanceMatrix.array;
	const step = o.count > 4096 ? Math.ceil( o.count / 4096 ) : 1;   // sample very large batches
	let best = Infinity;
	for ( let i = 0; i < o.count; i += step ) {
		_m4.fromArray( arr, i * 16 ).premultiply( o.matrixWorld );
		_c.copy( gs.center ).applyMatrix4( _m4 );
		const e = _m4.elements;
		const sx = Math.hypot( e[ 0 ], e[ 1 ], e[ 2 ] ), sy = Math.hypot( e[ 4 ], e[ 5 ], e[ 6 ] ), sz = Math.hypot( e[ 8 ], e[ 9 ], e[ 10 ] );
		const d = eye.distanceTo( _c ) - gs.radius * Math.max( sx, sy, sz );
		if ( d < best ) best = d;
	}
	return Math.max( 0, best );
}

/**
 * Every MeshStandardMaterial in the scene with the distance from `camera` to the nearest mesh that
 * uses it (surface distance: centre distance minus the bounding-sphere radius, never below 0).
 */
export function materialsByDistance( scene, camera ) {
	const rows = new Map();
	camera.getWorldPosition( _v );
	const eye = _v.clone();
	scene.traverse( ( o ) => {
		if ( ! o.isMesh || o.visible === false ) return;
		if ( ! o.geometry.boundingSphere ) o.geometry.computeBoundingSphere();
		let d;
		if ( o.isInstancedMesh ) {
			d = instanceDistance( o, eye );
		} else {
			_sphere.copy( o.geometry.boundingSphere ).applyMatrix4( o.matrixWorld );
			d = Math.max( 0, eye.distanceTo( _sphere.center ) - _sphere.radius );
		}
		for ( const m of ( Array.isArray( o.material ) ? o.material : [ o.material ] ) ) {
			if ( ! m || ! m.isMeshStandardMaterial ) continue;
			const row = rows.get( m );
			if ( ! row ) rows.set( m, { material: m, distance: d, meshes: 1 } );
			else { row.meshes ++; if ( d < row.distance ) row.distance = d; }
		}
	} );
	return [ ...rows.values() ].sort( ( a, b ) => a.distance - b.distance );
}

/**
 * Attach the manifest's texture sets, nearest material first.
 * @param {object} args
 *   scene, camera, sets (manifest.materials.sets), loadTexture(url) -> Promise<THREE.Texture>,
 *   note(string), onTexture(material, slot, texture, bytes) optional, concurrency
 * @returns {Promise<object>} report
 */
export async function applyPbrSets( { scene, camera, sets, loadTexture, note, onLoaded, concurrency = 3, maxTier = Infinity } ) {
	const byKey = indexSets( sets );
	const rows = materialsByDistance( scene, camera );
	const work = [], unmatched = [], matchedKeys = new Set();
	for ( const row of rows ) {
		const keys = candidateKeys( row.material.name );
		const key = keys.find( k => byKey.has( k ) );
		if ( ! key ) { unmatched.push( { material: row.material.name || '(unnamed)', distance_m: Math.round( row.distance ) } ); continue; }
		matchedKeys.add( byKey.get( key ).name );
		work.push( { ...row, set: byKey.get( key ), matchedOn: key, rank: work.length + 1 } );
	}
	// PASS 1, no network: every matched material takes its FACTORS immediately (v3 rule 3 — the
	// factor is the baked map's mean, the right value before the texture streams in and the right
	// multiplier, 1.0 / white, afterwards).  A `texture: null, constant: true` map is finished here.
	let factored = 0, constantOnly = 0;
	for ( const job of work ) {
		const n = applyFactors( job.material, job.set );
		if ( n ) factored ++;
		if ( n && ! Object.keys( job.set.maps ).length ) constantOnly ++;
	}
	const report = {
		materials_in_scene: rows.length, matched: work.length, unmatched,
		sets_in_manifest: Object.keys( sets ).length, sets_used: matchedKeys.size,
		sets_unused: Object.keys( sets ).filter( n => ! matchedKeys.has( n ) ),
		order: [], textures: 0, unique_files: 0, bytes: 0, kept_glb_normal: 0, replaced_glb_normal: 0, kept_glb_ao: 0,
		colourspace_conflicts: [], formats: {}, failed: [],
		factored, constant_only: constantOnly, flat_normal_constant: [],
		without_uv1: work.filter( j => j.set.uv1InGlb === false ).map( j => j.material.name ),
	};
	// One GPU upload per file: a texture used by several materials is SHARED, never cloned (a clone
	// of a CompressedTexture has its own uuid and three uploads the mips a second time).
	const cache = new Map();                      // url -> Promise<THREE.Texture>
	const csOf = new Map();                       // url -> the colour space the first user set
	const counted = new Set();                    // url -> counted once in report.bytes
	const get = ( url ) => {
		if ( ! cache.has( url ) ) cache.set( url, loadTexture( url ) );
		return cache.get( url );
	};

	let cursor = 0;
	const runOne = async ( job ) => {
		const { material: m, set } = job;
		const applied = [];
		// Phase 6b: what this material is wearing, so the tier upgrade knows what to replace and a
		// second pass never re-downloads a file the material already has.
		const state = m.userData.pfaPbr = m.userData.pfaPbr || { set, variants: {} };
		state.set = set;
		for ( const [ slot, full ] of Object.entries( set.maps ) ) {
			// The ORN hi->lo normal and the AO baked into the glb stay unless the manifest replaces them.
			if ( slot === 'aoMap' && m.aoMap ) { report.kept_glb_ao ++; continue; }
			// Which FILE of this entry belongs to the tier that has arrived (null: the factor stands).
			const entry = mapForTier( full, maxTier );
			if ( ! entry ) { report.deferred = ( report.deferred || 0 ) + 1; continue; }
			if ( entry.variant === 'lo' ) report.lo_variants = ( report.lo_variants || 0 ) + 1;
			try {
				// Claimed before the await: at concurrency > 1 two workers would otherwise both find
				// the url unclaimed and the last write would win silently (review finding 8).
				const claimed = csOf.has( entry.url );
				if ( ! claimed ) csOf.set( entry.url, entry.srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace );
				const t = await get( entry.url );
				const want = entry.srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
				if ( claimed && csOf.get( entry.url ) !== want )
					report.colourspace_conflicts.push( { url: entry.url, first: csOf.get( entry.url ), then: want } );
				if ( ! claimed ) t.colorSpace = want;
				t.channel = 0;                            // UV1 = glTF TEXCOORD_0
				if ( set.wrap === 'repeat' ) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
				t.anisotropy = Math.max( t.anisotropy || 1, 8 );
				t.needsUpdate = true;
				if ( slot === 'normalMap' && m.normalMap ) report.replaced_glb_normal ++;
				m[ slot ] = t;
				// v3 rule 3: never multiply the texture by the factor — the factor was the stand-in.
				if ( slot === 'map' ) m.color.setRGB( 1, 1, 1 );
				if ( slot === 'roughnessMap' ) m.roughness = 1.0;
				if ( slot === 'metalnessMap' ) m.metalness = 1.0;
				if ( slot === 'normalMap' && set.normalScale ) m.normalScale.set( set.normalScale, set.normalScale );
				state.variants[ slot ] = entry.url;
				applied.push( slot );
				report.textures ++;
					if ( ! counted.has( entry.url ) ) {
						counted.add( entry.url );
						report.unique_files ++;
						report.bytes += texBytes( t );
						const f = formatName( t );
						report.formats[ f ] = ( report.formats[ f ] || 0 ) + 1;
					}
			} catch ( e ) { report.failed.push( { url: entry.url, error: e.message } ); }
		}
		if ( m.normalMap && ! set.maps.normalMap ) {
			report.kept_glb_normal ++;                                          // ORN hi->lo normal kept
			if ( set.flatNormalConstant ) report.flat_normal_constant.push( m.name );
		}
		if ( applied.length ) { m.needsUpdate = true; }
		report.order.push( { rank: job.rank, material: m.name, set: set.name, matched_on: job.matchedOn,
			distance_m: Math.round( job.distance * 10 ) / 10, maps: applied } );
		if ( onLoaded ) onLoaded( m, applied, report.order.length, work.length );
	};
	const worker = async () => { while ( cursor < work.length ) await runOne( work[ cursor ++ ] ); };
	await Promise.all( Array.from( { length: Math.max( 1, concurrency ) }, worker ) );

	if ( note ) {
		note( `pbr: ${report.matched} of ${report.materials_in_scene} scene materials textured from `
			+ `${report.sets_used} of ${report.sets_in_manifest} manifest sets, ${report.textures} maps, `
			+ `${( report.bytes / 1e6 ).toFixed( 1 )} MB resident in ${report.unique_files} file(s) `
			+ `[${Object.entries( report.formats ).map( ( [ f, n ] ) => `${n} ${f}` ).join( ', ' )}], requested nearest first `
			+ `(${report.order.slice( 0, 3 ).map( r => `${r.material} ${r.distance_m} m` ).join( ', ' )} …)` );
		note( `pbr: factors applied to ${factored} material(s) before any download, `
			+ `${constantOnly} of them finished by their factors alone (constant maps)`
			+ ( report.without_uv1.length ? `; ${report.without_uv1.length} set(s) have no UV1 in the glb and take factors only: ${report.without_uv1.slice( 0, 4 ).join( ', ' )}` : '' ) );
		if ( unmatched.length ) note( `pbr: ${unmatched.length} material(s) with NO texture set, left as exported: `
			+ unmatched.slice( 0, 12 ).map( u => u.material ).join( ', ' ) + ( unmatched.length > 12 ? ' …' : '' ) );
		if ( report.failed.length ) note( `pbr: ${report.failed.length} texture(s) FAILED: ${report.failed.slice( 0, 4 ).map( f => `${f.url.split( '/' ).pop()} ${f.error}` ).join( '; ' )}` );
	}
	return report;
}

/** v3 factors, applied without any download: albedo -> material.color (linear RGB), roughness and
 *  metallic -> the scalars, normal.scale -> normalScale.  Returns how many were applied. */
export function applyFactors( m, set ) {
	let n = 0;
	const f = set.factors || {};
	if ( Array.isArray( f.map ) && f.map.length >= 3 ) { m.color.setRGB( f.map[ 0 ], f.map[ 1 ], f.map[ 2 ], THREE.LinearSRGBColorSpace ); n ++; }
	if ( typeof f.roughnessMap === 'number' ) { m.roughness = f.roughnessMap; n ++; }
	if ( typeof f.metalnessMap === 'number' ) { m.metalness = f.metalnessMap; n ++; }
	if ( typeof set.normalScale === 'number' && m.normalScale && set.maps.normalMap ) {
		m.normalScale.set( set.normalScale, set.normalScale ); n ++;
	}
	// A CONSTANT normal factor is the flat normal [0.5, 0.5, 1]: it means "this bake found no relief",
	// not "throw the relief away".  The glb's own normal map (the Gate 1 ORN hi->lo bake) is kept.
	if ( Array.isArray( f.normalMap ) && ! set.maps.normalMap ) set.flatNormalConstant = true;
	if ( n ) m.needsUpdate = true;
	return n;
}

/** three's numeric texture format as its constant name: RGBA_ASTC_4x4_Format, RGBAFormat, … .
 *  The name matters for the memory budget: a KTX2 the device cannot keep compressed is transcoded to
 *  RGBA8 and costs w*h*4 (x4/3 with mips) instead of the bytes the file ships. */
let _formats = null;
export function formatName( t ) {
	if ( ! t ) return 'none';
	if ( ! _formats ) {
		_formats = new Map();
		for ( const [ k, v ] of Object.entries( THREE ) ) if ( /Format$/.test( k ) && typeof v === 'number' && ! _formats.has( v ) ) _formats.set( v, k );
	}
	const n = _formats.get( t.format ) || `format_${t.format}`;
	return t.isCompressedTexture ? n : `${n} (uncompressed)`;
}

/** Bytes a loaded texture occupies: compressed mips as shipped, uncompressed as w*h*4 (+mips). */
export function texBytes( t ) {
	if ( ! t ) return 0;
	if ( t.mipmaps && t.mipmaps.length && t.mipmaps[ 0 ].data ) {
		let b = 0;
		for ( const m of t.mipmaps ) b += m.data.byteLength;
		return b;
	}
	if ( t.image && t.image.width ) return t.image.width * t.image.height * 4 * ( t.generateMipmaps ? 4 / 3 : 1 );
	return 0;
}

const MAT_SLOTS = [ 'map', 'lightMap', 'aoMap', 'normalMap', 'roughnessMap', 'metalnessMap', 'emissiveMap',
	'alphaMap', 'envMap', 'bumpMap', 'displacementMap', 'specularMap', 'clearcoatMap', 'clearcoatNormalMap',
	'clearcoatRoughnessMap', 'sheenColorMap', 'sheenRoughnessMap', 'transmissionMap', 'thicknessMap',
	'iridescenceMap', 'iridescenceThicknessMap', 'anisotropyMap', 'specularIntensityMap', 'specularColorMap' ];

/** Every texture reachable from a mesh material in the scene. */
export function collectTextures( scene ) {
	const out = new Map();                       // texture -> the slots it was found in
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		for ( const m of ( Array.isArray( o.material ) ? o.material : [ o.material ] ) ) {
			if ( ! m ) continue;
			for ( const k of MAT_SLOTS ) {
				if ( ! m[ k ] ) continue;
				const at = out.get( m[ k ] );
				if ( at ) at.add( k ); else out.set( m[ k ], new Set( [ k ] ) );
			}
		}
	} );
	return out;
}

/** A Gate 2 map REPLACES the Gate 1 one it supersedes (the ORN hi->lo normals), and the replaced
 *  texture stays on the GPU until something disposes it — it is simply no longer reachable from any
 *  material.  Dispose exactly those: in `before` and not reachable now. */
export function disposeOrphans( scene, before ) {
	const live = collectTextures( scene );
	let freed = 0; const names = [], bySlot = {};
	for ( const [ t, slots ] of before ) {
		if ( live.has( t ) ) continue;
		freed += texBytes( t );
		for ( const k of slots ) bySlot[ k ] = ( bySlot[ k ] || 0 ) + 1;
		names.push( t.name || t.userData?.url || t.uuid.slice( 0, 8 ) );
		t.dispose();
	}
	return { disposed: names.length, freed_bytes: freed, by_slot: bySlot, names: names.slice( 0, 12 ) };
}

/**
 * Phase 6b: WHICH FILE of a map entry this tier gets.
 *   - the full file, when its own tier has arrived;
 *   - its `lo` low-resolution stand-in, when that has arrived and the full file has not;
 *   - null, when neither has: the material keeps the manifest's FACTOR (v3 rule 3 — the factor is the
 *     map's baked mean), which is exactly the right value to show before a texture exists.
 * At v4, where every entry is tier 0 and carries no `lo`, this always returns the full file.
 */
export function mapForTier( entry, maxTier = Infinity ) {
	if ( ! entry ) return null;
	// Not in THIS variant's plan: the file is not published here (the mobile sets name the desktop
	// keys), so the stand-in that IS in the plan is the only honest answer.
	if ( entry.inPlan === false && entry.lo && entry.lo.url )
		return { url: entry.lo.url, srgb: entry.srgb, bytes: entry.lo.bytes, variant: 'lo',
			tier: entry.lo.tier ?? 0, standIn: !! entry.lo.standIn, onlyFile: true };
	const tier = Number.isFinite( entry.tier ) ? entry.tier : 0;
	if ( tier <= maxTier ) return { url: entry.url, srgb: entry.srgb, bytes: entry.bytes, variant: 'full', tier };
	const lo = entry.lo;
	if ( lo && lo.url && ( Number.isFinite( lo.tier ) ? lo.tier : 0 ) <= maxTier )
		return { url: lo.url, srgb: entry.srgb, bytes: lo.bytes, variant: 'lo', tier: lo.tier ?? 0, standIn: !! lo.standIn };
	return null;
}

/** Every texture file the PBR sets reference AT THIS TIER, for the byte plan (deduplicated). */
export function pbrPlan( sets, maxTier = Infinity ) {
	const seen = new Set(), files = [];
	for ( const set of Object.values( sets ) ) {
		for ( const [ slot, e ] of Object.entries( set.maps ) ) {
			const pick = mapForTier( e, maxTier );
			if ( ! pick || seen.has( pick.url ) ) continue;
			seen.add( pick.url );
			files.push( { url: pick.url, kind: `tex:${slot.replace( 'Map', '' )}${pick.variant === 'lo' ? ':lo' : ''}`, bytes: pick.bytes || 0 } );
		}
	}
	return files;
}

/**
 * Phase 6b, the OTHER half of the tier upgrade: the textures the GLB references itself.
 *
 * With `gltfpack -tr` the leaf, bark and ORN occlusion maps are external files named inside the glb
 * and nowhere in the manifest, so `upgradePbrSets` (which walks manifest material sets) cannot see
 * them.  When tier 0 ships a glb pointing at the low-resolution `tex_lo` encode, the only identity
 * those maps have is the URL they were loaded from — stamped on `texture.userData.pfaUrl` by the
 * viewer's shared texture cache — and `manifest.tiers.upgradeOf` says which url supersedes it and
 * when.  This swaps them on the same material, exactly like a manifest map.
 *
 * `remaining` is the assertion the boot log carries: after the last tier nothing in the scene may
 * still be wearing a low-resolution file.
 */
export async function upgradeGlbTextures( { scene, maxTier, upgradeOf, loadTexture, note, concurrency = 3 } ) {
	const report = { candidates: 0, upgraded: 0, bytes: 0, failed: [], remaining: [], maxTier };
	if ( ! upgradeOf || ! upgradeOf.size ) return report;
	const jobs = [], seen = new Set();
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		for ( const m of ( Array.isArray( o.material ) ? o.material : [ o.material ] ) ) {
			if ( ! m ) continue;
			for ( const slot of MAT_SLOTS ) {
				const t = m[ slot ];
				const url = t && t.userData && t.userData.pfaUrl;
				if ( ! url ) continue;
				const up = upgradeOf.get( url );
				if ( ! up ) continue;
				report.candidates ++;
				if ( up.tier > maxTier ) { report.remaining.push( url ); continue; }
				const key = `${m.uuid}:${slot}`;
				if ( seen.has( key ) ) continue;
				seen.add( key );
				jobs.push( { material: m, slot, from: t, to: up } );
			}
		}
	} );
	const counted = new Set();
	let cursor = 0;
	const worker = async () => {
		while ( cursor < jobs.length ) {
			const j = jobs[ cursor ++ ];
			try {
				const t = await loadTexture( j.to.url );
				// the glb's own sampler state is the right one: only the pixels change
				t.colorSpace = j.from.colorSpace;
				t.wrapS = j.from.wrapS; t.wrapT = j.from.wrapT;
				t.channel = j.from.channel;
				t.flipY = j.from.flipY;
				t.anisotropy = Math.max( t.anisotropy || 1, j.from.anisotropy || 1 );
				t.needsUpdate = true;
				j.material[ j.slot ] = t;
				j.material.needsUpdate = true;
				report.upgraded ++;
				if ( ! counted.has( j.to.url ) ) { counted.add( j.to.url ); report.bytes += texBytes( t ); }
			} catch ( e ) { report.failed.push( { url: j.to.url, error: e.message } ); }
		}
	};
	await Promise.all( Array.from( { length: Math.max( 1, concurrency ) }, worker ) );
	report.remaining = [ ...new Set( report.remaining ) ];
	if ( note && ( report.upgraded || report.remaining.length ) )
		note( `glb textures tier ${maxTier}: ${report.upgraded} map(s) swapped to their full-resolution file `
			+ `(${( report.bytes / 1e6 ).toFixed( 1 )} MB)`
			+ ( report.remaining.length ? `, ${report.remaining.length} still low-resolution (their tier has not landed)` : '' )
			+ ( report.failed.length ? `; ${report.failed.length} FAILED` : '' ) );
	return report;
}

/**
 * Phase 6b tier upgrade: every material that is wearing a `lo` stand-in (or no map at all, only its
 * factor) takes the file its entry names, now that `maxTier` has arrived.  The swap is on the SAME
 * material, so nothing is rebuilt and no program is recompiled; the superseded stand-ins are disposed
 * by the caller's `disposeOrphans` sweep, exactly like the Gate 1 maps the Gate 2 set replaced.
 */
export async function upgradePbrSets( { scene, maxTier, loadTexture, note, concurrency = 3 } ) {
	const jobs = [];
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		for ( const m of ( Array.isArray( o.material ) ? o.material : [ o.material ] ) ) {
			const st = m && m.userData && m.userData.pfaPbr;
			if ( ! st || jobs.some( ( j ) => j.material === m ) ) continue;
			for ( const [ slot, e ] of Object.entries( st.set.maps ) ) {
				const pick = mapForTier( e, maxTier );
				if ( ! pick ) continue;
				if ( st.variants[ slot ] === pick.url ) continue;         // already wearing this file
				jobs.push( { material: m, set: st.set, slot, pick, from: st.variants[ slot ] || '(factor only)' } );
			}
		}
	} );
	const report = { candidates: jobs.length, upgraded: 0, from_lo: 0, from_factor: 0, bytes: 0, failed: [], maxTier };
	const cache = new Map();
	const get = ( url ) => { if ( ! cache.has( url ) ) cache.set( url, loadTexture( url ) ); return cache.get( url ); };
	let cursor = 0;
	const counted = new Set();
	const worker = async () => {
		while ( cursor < jobs.length ) {
			const j = jobs[ cursor ++ ];
			try {
				const t = await get( j.pick.url );
				t.colorSpace = j.pick.srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
				t.channel = 0;
				if ( j.set.wrap === 'repeat' ) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
				t.anisotropy = Math.max( t.anisotropy || 1, 8 );
				t.needsUpdate = true;
				j.material[ j.slot ] = t;
				if ( j.slot === 'map' ) j.material.color.setRGB( 1, 1, 1 );
				if ( j.slot === 'roughnessMap' ) j.material.roughness = 1.0;
				if ( j.slot === 'metalnessMap' ) j.material.metalness = 1.0;
				if ( j.slot === 'normalMap' && j.set.normalScale ) j.material.normalScale.set( j.set.normalScale, j.set.normalScale );
				j.material.needsUpdate = true;
				j.material.userData.pfaPbr.variants[ j.slot ] = j.pick.url;
				report.upgraded ++;
				if ( j.from === '(factor only)' ) report.from_factor ++; else report.from_lo ++;
				if ( ! counted.has( j.pick.url ) ) { counted.add( j.pick.url ); report.bytes += texBytes( t ); }
			} catch ( e ) { report.failed.push( { url: j.pick.url, error: e.message } ); }
		}
	};
	await Promise.all( Array.from( { length: Math.max( 1, concurrency ) }, worker ) );
	if ( note && report.candidates ) note( `pbr tier ${maxTier}: ${report.upgraded}/${report.candidates} map(s) upgraded `
		+ `(${report.from_factor} from the factor alone, ${report.from_lo} from a low-resolution stand-in), `
		+ `${( report.bytes / 1e6 ).toFixed( 1 )} MB`
		+ ( report.failed.length ? `; ${report.failed.length} FAILED: ${report.failed.slice( 0, 3 ).map( f => f.url.split( '/' ).pop() ).join( ', ' )}` : '' ) );
	return report;
}
