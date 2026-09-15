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

const _sphere = new THREE.Sphere(), _v = new THREE.Vector3();

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
			if ( ! o.boundingSphere ) o.computeBoundingSphere();
			_sphere.copy( o.boundingSphere ).applyMatrix4( o.matrixWorld );
		} else {
			_sphere.copy( o.geometry.boundingSphere ).applyMatrix4( o.matrixWorld );
		}
		d = Math.max( 0, eye.distanceTo( _sphere.center ) - _sphere.radius );
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
export async function applyPbrSets( { scene, camera, sets, loadTexture, note, onLoaded, concurrency = 3 } ) {
	const byKey = indexSets( sets );
	const rows = materialsByDistance( scene, camera );
	const work = [], unmatched = [], matchedKeys = new Set();
	for ( const row of rows ) {
		const keys = candidateKeys( row.material.name );
		const key = keys.find( k => byKey.has( k ) );
		if ( ! key ) { unmatched.push( { material: row.material.name || '(unnamed)', distance_m: Math.round( row.distance ) } ); continue; }
		matchedKeys.add( byKey.get( key ).name );
		work.push( { ...row, set: byKey.get( key ), matchedOn: key } );
	}
	const report = {
		materials_in_scene: rows.length, matched: work.length, unmatched,
		sets_in_manifest: Object.keys( sets ).length, sets_used: matchedKeys.size,
		sets_unused: Object.keys( sets ).filter( n => ! matchedKeys.has( n ) ),
		order: [], textures: 0, unique_files: 0, bytes: 0, kept_glb_normal: 0, replaced_glb_normal: 0, kept_glb_ao: 0,
		colourspace_conflicts: [], failed: [],
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
		for ( const [ slot, entry ] of Object.entries( set.maps ) ) {
			// The ORN hi->lo normal and the AO baked into the glb stay unless the manifest replaces them.
			if ( slot === 'aoMap' && m.aoMap ) { report.kept_glb_ao ++; continue; }
			try {
				const t = await get( entry.url );
				const want = entry.srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
				if ( csOf.has( entry.url ) && csOf.get( entry.url ) !== want )
					report.colourspace_conflicts.push( { url: entry.url, first: csOf.get( entry.url ), then: want } );
				else if ( ! csOf.has( entry.url ) ) { csOf.set( entry.url, want ); t.colorSpace = want; }
				t.channel = 0;                            // UV1 = glTF TEXCOORD_0
				if ( set.wrap === 'repeat' ) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
				t.anisotropy = Math.max( t.anisotropy || 1, 8 );
				t.needsUpdate = true;
				if ( slot === 'normalMap' && m.normalMap ) report.replaced_glb_normal ++;
				m[ slot ] = t;
				if ( slot === 'map' ) m.color.setRGB( 1, 1, 1 );                        // the map IS the albedo
				if ( slot === 'roughnessMap' ) m.roughness = set.roughnessFactor ?? 1.0;
				if ( slot === 'metalnessMap' ) m.metalness = set.metalnessFactor ?? 1.0;
				if ( slot === 'normalMap' && set.normalScale ) m.normalScale.set( set.normalScale, set.normalScale );
				applied.push( slot );
				report.textures ++;
						report.bytes += texBytes( t );
			} catch ( e ) { report.failed.push( { url: entry.url, error: e.message } ); }
		}
		if ( set.metalnessFactor !== undefined && ! set.maps.metalnessMap ) m.metalness = set.metalnessFactor;
		if ( m.normalMap && ! set.maps.normalMap ) report.kept_glb_normal ++;    // ORN hi->lo normal kept
		if ( applied.length ) { m.needsUpdate = true; }
		report.order.push( { material: m.name, set: set.name, matched_on: job.matchedOn,
			distance_m: Math.round( job.distance * 10 ) / 10, maps: applied } );
		if ( onLoaded ) onLoaded( m, applied, report.order.length, work.length );
	};
	const worker = async () => { while ( cursor < work.length ) await runOne( work[ cursor ++ ] ); };
	await Promise.all( Array.from( { length: Math.max( 1, concurrency ) }, worker ) );

	if ( note ) {
		note( `pbr: ${report.matched} of ${report.materials_in_scene} scene materials textured from `
			+ `${report.sets_used} of ${report.sets_in_manifest} manifest sets, ${report.textures} maps, `
			+ `${( report.bytes / 1e6 ).toFixed( 1 )} MB resident, nearest first `
			+ `(${report.order.slice( 0, 3 ).map( r => `${r.material} ${r.distance_m} m` ).join( ', ' )} …)` );
		if ( unmatched.length ) note( `pbr: ${unmatched.length} material(s) with NO texture set, left as exported: `
			+ unmatched.slice( 0, 12 ).map( u => u.material ).join( ', ' ) + ( unmatched.length > 12 ? ' …' : '' ) );
		if ( report.failed.length ) note( `pbr: ${report.failed.length} texture(s) FAILED: ${report.failed.slice( 0, 4 ).map( f => `${f.url.split( '/' ).pop()} ${f.error}` ).join( '; ' )}` );
	}
	return report;
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

/** Every texture file the PBR sets reference, for the byte plan (deduplicated). */
export function pbrPlan( sets ) {
	const seen = new Set(), files = [];
	for ( const set of Object.values( sets ) ) {
		for ( const [ slot, e ] of Object.entries( set.maps ) ) {
			if ( seen.has( e.url ) ) continue;
			seen.add( e.url );
			files.push( { url: e.url, kind: `tex:${slot.replace( 'Map', '' )}`, bytes: e.bytes || 0 } );
		}
	}
	return files;
}
