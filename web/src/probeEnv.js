// QA-13-1: the baked hero probe as the irradiance for surfaces that have no baked light of their own.
//
// THE PROBLEM IT SOLVES.  In `baked` lighting every surface with a lightmap or COLOR_0 gets its diffuse
// from the bake, and `patchBakedMaterial` deletes the sun's diffuse and the environment's irradiance
// from those shaders.  Everything else - the ENV backdrop city blocks, the shrubs, the reeds - keeps
// three's ordinary path: DirectionalLight Lambert plus `scene.environment`, which is the sky's DIFFUSE
// branch.  Measured on the real frame, that is not enough: the backdrop wall at cam01 (48,567) has a
// world normal of [-0.908, 0, -0.419] and NdotL = -0.065 against the sun, so the sun contributes
// EXACTLY ZERO and the blue sky is all the light it has (65/84/127, and 55/97/205 with a neutral
// albedo).  `?lighting=direct` renders that pixel bit-identically, so no re-weighting of sun and sky
// can change it.  What Cycles gives it and the viewer does not is the warm INDIRECT bounce.
//
// WHAT THIS DOES.  `manifest.probe` is a 6-face 512 px HDR cube baked at the hero station with 64
// samples, and it contains that bounce: its `ny` face (looking down at the sunlit ground) has mean
// 0.38 and its `py` face (sky) 4.66, so convolving it gives a directional irradiance with the warm
// ground bounce in it rather than a uniform blue dome.  It is convolved ONCE at load with three's own
// PMREMGenerator and assigned as `material.envMap` on exactly those materials, which overrides
// `scene.environment` for them and leaves every other material alone.
//
// WHAT IT IS NOT.  Three honest caveats, all of which belong in any report that quotes a number:
//   * A SINGLE-POINT approximation.  The probe was rendered at CAM_qa_01_lagoon_hero
//     (Blender -14.1, 100.0, -3.9).  For the backdrop blocks 140-190 m away, and at stations other
//     than 1, it is the irradiance at the hero's position, not at the surface's.
//   * The manifest's own `probe.use` says "NOT the diffuse environment - see sky.diffuse".  This
//     deliberately departs from that, authorised by the lead after the direct-path prescription was
//     measured to be a no-op.  The departure is limited to surfaces that have no baked light at all.
//   * `probe.world_branch` is "glossy", so this is the glossy world branch convolved to irradiance,
//     not the diffuse branch the rest of the scene uses.
//
// `?probe=0` restores the sky-diffuse-only path for an A/B, and `?lighting=direct` is untouched.
import * as THREE from 'three';

/**
 * Build the PMREM of the probe cube.  Returns null when the manifest has no usable probe.
 * @param {{faces:string[]}} probe   manifest.gate3.probe (six urls, px nx py ny pz nz)
 */
export async function buildProbeEnv( probe, { renderer, loadHdr, note = () => {} } ) {
	if ( ! probe || ! Array.isArray( probe.faces ) || probe.faces.length !== 6 ) return null;
	const t0 = performance.now();
	const texs = await Promise.all( probe.faces.map( ( u ) => loadHdr( u ) ) );
	if ( texs.some( ( t ) => ! t || ! t.image ) ) { note( 'probe: a face failed to load; the sky-diffuse path stays' ); return null; }

	// THE CUBE MUST BE BUILT FROM THE DataTextureS THEMSELVES, NOT FROM THEIR `.image`.
	// three picks the data-upload path from `texture.image[0].isDataTexture`; RGBELoader's `.image` is
	// a bare {data,width,height}, so passing those makes all six faces take the DOM-source branch,
	// `texSubImage2D` throws, and WebGLState SWALLOWS the error - leaving a zero-filled cube whose
	// PMREM is BLACK.  A black envMap OVERRIDES scene.environment, so the materials lose their sky
	// irradiance instead of gaining the warm bounce.  That is exactly what shipped in round 14 and it
	// invalidated every probe measurement; see docs/reviews/phase6_viewer_gate4_r6_review.md finding 1.
	// Face order px nx py ny pz nz is three's own, and the manifest's `axes` already names the faces
	// for the three.js axes, so nothing is re-ordered.
	const cube = new THREE.CubeTexture( texs );
	cube.type = texs[ 0 ].type;
	cube.format = texs[ 0 ].format;
	cube.colorSpace = texs[ 0 ].colorSpace;
	cube.minFilter = cube.magFilter = THREE.LinearFilter;
	cube.generateMipmaps = false;
	cube.needsUpdate = true;

	// The faces decoded on the CPU: a zero face means the HDR never loaded, before the GPU is involved.
	const faceMeans = texs.map( ( t ) => {
		const d = t.image && t.image.data;
		if ( ! d || ! d.length ) return 0;
		let sum = 0;
		for ( let i = 0; i < d.length; i += Math.max( 4, Math.floor( d.length / 4096 ) * 4 ) ) sum += Math.abs( d[ i ] );
		return sum;
	} );
	if ( faceMeans.some( ( m ) => ! ( m > 0 ) ) ) {
		note( `probe REFUSED: ${faceMeans.filter( ( m ) => ! ( m > 0 ) ).length} of 6 faces decoded to all zero` );
		texs.forEach( ( t ) => t.dispose() );
		return null;
	}

	const pmrem = new THREE.PMREMGenerator( renderer );
	pmrem.compileCubemapShader();
	const rt = pmrem.fromCubemap( cube );
	pmrem.dispose();

	// And the PMREM read back off the GPU: this is what caught nothing in round 14 because nothing
	// looked at it.  A black convolution means the upload silently failed again.
	// The PMREM is an ATLAS of mip levels with unused padding, so ONE texel proves nothing - the
	// centre of the atlas is legitimately blank.  Sample a spread of points and require any to carry
	// energy; that distinguishes "black cube" from "sampled the padding".
	let probeSample = null, sampled = 0;
	try {
		const Buf = rt.texture.type === THREE.HalfFloatType ? Uint16Array : Float32Array;
		const pts = [ [ 2, 2 ], [ Math.floor( rt.width / 4 ), 2 ], [ 2, Math.floor( rt.height / 4 ) ],
			[ Math.floor( rt.width / 4 ), Math.floor( rt.height / 4 ) ], [ Math.floor( rt.width / 2 ), Math.floor( rt.height / 2 ) ] ];
		const seen = [];
		for ( const [ x, y ] of pts ) {
			const buf = new Buf( 4 );
			renderer.readRenderTargetPixels( rt, x, y, 1, 1, buf );
			seen.push( { at: [ x, y ], rgba: Array.from( buf ) } );
			if ( buf[ 0 ] || buf[ 1 ] || buf[ 2 ] ) sampled ++;
		}
		probeSample = seen;
	} catch ( e ) { note( `probe: could not read the PMREM back (${e.message}); the cube is unverified` ); }
	const nonBlack = probeSample ? sampled > 0 : null;
	if ( nonBlack === false ) {
		note( 'probe REFUSED: the convolved PMREM reads BLACK at its centre texel - the cube did not upload. '
			+ 'A black envMap would OVERRIDE scene.environment and delete the sky irradiance (review finding 1).' );
		cube.dispose(); texs.forEach( ( t ) => t.dispose() ); rt.dispose();
		return null;
	}
	cube.dispose();
	texs.forEach( ( t ) => t.dispose() );
	rt.userData = { probeSample, nonBlack, faceMeans };
	note( `probe env: 6 x ${probe.sizePx || '?'} px HDR cube from ${probe.station || 'the hero station'} `
		+ `convolved to irradiance in ${( ( performance.now() - t0 ) / 1000 ).toFixed( 2 )} s; `
		+ `PMREM read back at ${probeSample ? probeSample.length : 0} point(s), ${sampled} carrying energy `
		+ `(${nonBlack === null ? 'UNVERIFIED' : 'verified non-black'}); faces ${faceMeans.map( ( m ) => m.toFixed( 1 ) ).join( '/' )}` );
	return rt;
}

/**
 * Give the probe's irradiance to every material that has NO baked light of its own.
 *
 * "No baked light" means: a MeshStandardMaterial that `patchBakedMaterial` never touched (so it still
 * has three's sun diffuse and env irradiance) and that carries no lightMap.  A material that already
 * owns an envMap is left alone - `setBakedEnvMaps` puts the GLOSSY sky on the baked ones for their
 * specular, and overwriting that would change a surface this is not meant to touch.
 *
 * @returns {{materials:number, meshes:number, skippedPatched:number, skippedHasEnv:number, names:string[]}}
 */
export function applyProbeEnv( scene, envTexture, { note = () => {}, intensity = 1.0, gate3Report = null } = {} ) {
	const out = { materials: 0, meshes: 0, skippedPatched: 0, skippedHasEnv: 0, skippedNonStandard: 0,
		refused: null, names: [] };
	if ( ! envTexture ) return out;
	// THE PROBE MUST NOT MASK A FAILED LIGHTMAP.  For the 988 instance SLOTS, patchBakedMaterial runs
	// inside the texture .then, so a failed atlas - or a mesh with no UV2 - leaves the material with
	// neither `pfaPatched` nor a lightMap.  It would then look plausibly lit with the probe instead of
	// black, hiding the failure (review finding 5).  If any lightmap failed, the pass refuses outright.
	if ( gate3Report ) {
		const failed = ( gate3Report.texturesFailed || [] ).length;
		const slotsShort = ( gate3Report.slots && gate3Report.slots.matched > gate3Report.slots.applied )
			? gate3Report.slots.matched - gate3Report.slots.applied : 0;
		const noUv2 = ( gate3Report.slots && gate3Report.slots.noUv2Attribute ) || 0;
		if ( failed || slotsShort || noUv2 ) {
			out.refused = `${failed} lightmap texture(s) failed, ${slotsShort} slot(s) matched but not applied, `
				+ `${noUv2} slot instance(s) with no UV2 - the probe would make them look lit instead of black`;
			note( `probe env REFUSED: ${out.refused}. Fix the lightmaps first; ?probe=0 is not the answer.` );
			return out;
		}
	}
	const seen = new Set();
	scene.traverse( ( o ) => {
		if ( ! o.isMesh || ! o.material ) return;
		for ( const m of Array.isArray( o.material ) ? o.material : [ o.material ] ) {
			if ( ! m || seen.has( m.uuid ) ) continue;
			seen.add( m.uuid );
			if ( ! m.isMeshStandardMaterial ) { out.skippedNonStandard ++; continue; }   // impostors, water
			if ( m.userData.pfaPatched ) { out.skippedPatched ++; continue; }            // lightmap or COLOR_0
			if ( m.lightMap ) { out.skippedPatched ++; continue; }
			if ( m.envMap ) { out.skippedHasEnv ++; continue; }
			m.envMap = envTexture;
			m.envMapIntensity = intensity;
			m.needsUpdate = true;
			out.materials ++;
			if ( out.names.length < 12 ) out.names.push( m.name || '(unnamed)' );
		}
		out.meshes ++;
	} );
	note( `probe env applied to ${out.materials} material(s) with no baked light of their own `
		+ `(${out.skippedPatched} lightmapped or vertex-lit, ${out.skippedHasEnv} already had an envMap, `
		+ `${out.skippedNonStandard} not MeshStandard): ${out.names.slice( 0, 8 ).join( ', ' )}`
		+ ( out.materials > 8 ? ' …' : '' ) );
	return out;
}
