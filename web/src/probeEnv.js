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

	// three's CubeTexture takes the six images directly; the faces are already named for the three.js
	// axes (the manifest says so: "face `px` looks along three.js +X"), and px nx py ny pz nz is
	// three's own face order, so nothing is re-ordered here.
	const cube = new THREE.CubeTexture( texs.map( ( t ) => t.image ) );
	cube.type = texs[ 0 ].type;
	cube.format = texs[ 0 ].format;
	cube.colorSpace = texs[ 0 ].colorSpace;
	cube.minFilter = cube.magFilter = THREE.LinearFilter;
	cube.generateMipmaps = false;
	cube.needsUpdate = true;

	const pmrem = new THREE.PMREMGenerator( renderer );
	pmrem.compileCubemapShader();
	const rt = pmrem.fromCubemap( cube );
	pmrem.dispose();
	cube.dispose();
	texs.forEach( ( t ) => t.dispose() );
	note( `probe env: 6 x ${probe.sizePx || '?'} px HDR cube from ${probe.station || 'the hero station'} `
		+ `convolved to irradiance in ${( ( performance.now() - t0 ) / 1000 ).toFixed( 2 )} s` );
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
export function applyProbeEnv( scene, envTexture, { note = () => {}, intensity = 1.0 } = {} ) {
	const out = { materials: 0, meshes: 0, skippedPatched: 0, skippedHasEnv: 0, skippedNonStandard: 0, names: [] };
	if ( ! envTexture ) return out;
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
