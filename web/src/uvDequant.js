// gltfpack's texcoord quantisation, undone on the attribute.
//
// THE BUG THIS FIXES (Gate 4 step 0, measured 2026-09-16).  `gltfpack` quantises TEXCOORD_n to 12 bits
// and stores them as NORMALISED unsigned shorts, so the values that reach the shader sit in
// [0, 4095/65535] = [0, 0.0625] - one sixteenth of the real UV.  The dequantisation (scale ~16 and the
// island's min as an offset) is not in the accessor: gltfpack writes it into `KHR_texture_transform`
// on the material's baseColorTexture, and three applies a texture transform ONLY to the texture that
// carries it, on ITS uv channel.  Consequences, both measured on the real glbs:
//   * TEXCOORD_1 has no texture of its own in the glb, so the Gate 3 lightmap sampled the bottom-left
//     1/16 x 1/16 corner of its own map - mostly empty margin.  That is the "~1 stop dark, wall bands
//     dark/blue" hero: mean luma 117.5 against the Cycles hero's 140.0, and no decode or V-flip could
//     reach it because the texels being read were the wrong ones.
//   * The Gate 2 PBR and detail passes REPLACE `material.map` with their own texture, whose transform
//     is the identity, so every albedo / roughness / normal has been sampling the same 1/16 window
//     (the tile magnified ~16x) since Gate 2.
// Evidence that the layout itself is sound (so nothing is owed by the export): applying the material's
// transform to TEXCOORD_1 and flipping V reproduces the bake's own UV2 islands from
// export/out/gate3/lightmap_uv2.npz at IoU 0.994-0.999 on all seven re-laid assets, each matched to
// the right mesh.  `web/tools/uv2_debug.mjs` is that measurement.
//
// THE FIX.  Undo the transform once, on the attribute, right after the glb is parsed and before any
// other pass: uv := uv * repeat + offset, written back as float32, and every texture on the material
// reset to the identity transform.  From then on every pass - PBR, detail, lightmap, slot atlas - sees
// plain [0,1] UVs and needs to know nothing about quantisation.
import * as THREE from 'three';

const EPS = 1e-6;

/** The quantisation transform a material carries, from the first texture that has a non-identity one. */
function transformOf( mat ) {
	if ( ! mat ) return null;
	const order = [ 'map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap', 'lightMap' ];
	for ( const slot of order ) {
		const t = mat[ slot ];
		if ( ! t || ! t.isTexture ) continue;
		const sx = t.repeat.x, sy = t.repeat.y, ox = t.offset.x, oy = t.offset.y;
		if ( Math.abs( sx - 1 ) < EPS && Math.abs( sy - 1 ) < EPS && Math.abs( ox ) < EPS && Math.abs( oy ) < EPS ) continue;
		return { scale: [ sx, sy ], offset: [ ox, oy ], rotation: t.rotation, from: slot };
	}
	return null;
}

function textures( mat ) {
	const out = [];
	for ( const k in mat ) {
		const v = mat[ k ];
		if ( v && v.isTexture ) out.push( v );
	}
	return out;
}

/** uv := uv * scale + offset, written back as a plain float32 attribute. Returns bytes added. */
function applyToAttribute( geo, name, xf ) {
	const a = geo.getAttribute( name );
	if ( ! a ) return 0;
	const n = a.count;
	const arr = new Float32Array( n * 2 );
	const [ sx, sy ] = xf.scale, [ ox, oy ] = xf.offset;
	for ( let i = 0; i < n; i ++ ) {
		arr[ i * 2 ] = a.getX( i ) * sx + ox;
		arr[ i * 2 + 1 ] = a.getY( i ) * sy + oy;
	}
	geo.setAttribute( name, new THREE.BufferAttribute( arr, 2 ) );
	return arr.byteLength;
}

/**
 * Undo gltfpack's texcoord quantisation on every mesh under `root`.
 * @param {THREE.Object3D} root
 * @param {{ note?:function, enabled?:boolean }} opts
 * @returns {{ meshes:number, geometries:number, sets:number, materials:number, skipped:number,
 *             bytes:number, rotated:number, scales:number[] }}
 */
export function dequantizeUvs( root, opts = {} ) {
	const report = { meshes: 0, geometries: 0, sets: 0, materials: 0, skipped: 0, bytes: 0, rotated: 0, scales: [] };
	if ( opts.enabled === false ) return report;

	// 1. Record each material's transform BEFORE anything resets it: two primitives can share one
	//    material, and the second must not read an already-neutralised transform.
	root.traverse( ( o ) => {
		if ( ! o.isMesh || ! o.material ) return;
		for ( const m of Array.isArray( o.material ) ? o.material : [ o.material ] ) {
			if ( m.userData.pfaUvXf !== undefined ) continue;
			m.userData.pfaUvXf = transformOf( m );
		}
	} );

	// 2. Bake it into the uv attributes, once per geometry.
	const doneGeo = new Set(), doneMat = new Set();
	root.traverse( ( o ) => {
		if ( ! o.isMesh || ! o.geometry ) return;
		report.meshes ++;
		const mats = Array.isArray( o.material ) ? o.material : [ o.material ];
		const xf = mats.map( ( m ) => m && m.userData.pfaUvXf ).find( Boolean ) || null;
		// Idempotent: the recorded transform survives on the material, so without this a second call
		// would scale an already-dequantised attribute a second time.
		if ( ! xf || o.geometry.userData.pfaUvDequantized ) { report.skipped ++; return; }
		if ( Math.abs( xf.rotation ) > EPS ) report.rotated ++;
		if ( ! doneGeo.has( o.geometry.uuid ) ) {
			doneGeo.add( o.geometry.uuid );
			report.geometries ++;
			report.scales.push( xf.scale[ 0 ] );
			for ( const name of [ 'uv', 'uv1', 'uv2', 'uv3' ] ) {
				const b = applyToAttribute( o.geometry, name, xf );
				if ( b ) { report.bytes += b; report.sets ++; }
			}
			o.geometry.userData.pfaUvDequantized = xf;
		}
		// 3. Neutralise the transform on the material's own textures: the attribute now carries it.
		for ( const m of mats ) {
			if ( ! m || doneMat.has( m.uuid ) ) continue;
			doneMat.add( m.uuid );
			report.materials ++;
			for ( const t of textures( m ) ) { t.offset.set( 0, 0 ); t.repeat.set( 1, 1 ); t.rotation = 0; t.needsUpdate = true; }
			m.needsUpdate = true;
		}
	} );

	if ( opts.note && report.geometries ) {
		const s = report.scales;
		const lo = Math.min( ...s ), hi = Math.max( ...s );
		opts.note( `uv dequantisation (gltfpack KHR_texture_transform -> attribute): ${report.sets} uv set(s) on `
			+ `${report.geometries} geometr(ies), ${report.materials} material transform(s) neutralised, `
			+ `scale ${lo.toFixed( 3 )}..${hi.toFixed( 3 )}, +${( report.bytes / 1048576 ).toFixed( 2 )} MB`
			+ ( report.skipped ? `, ${report.skipped} mesh(es) with no transform left alone` : '' )
			+ ( report.rotated ? `, ${report.rotated} ROTATED (unsupported)` : '' ) );
	}
	return report;
}
