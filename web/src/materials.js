// MeshStandardMaterial patches for the baked-lighting pipeline (Phase 6).
//
// DOUBLE-LIGHTING.  The UV2 lightmap is Blender's Cycles DIFFUSE pass (direct + indirect, colour off)
// at the frozen Phase 5 rig, so it ALREADY contains the sun's diffuse and the sky's diffuse.  The
// viewer therefore removes both diffuse sources that three would otherwise add on top:
//   1. the DirectionalLight's diffuse term  -> RE_Direct_Physical keeps only reflectedLight.directSpecular
//      (the `reflectedLight.directDiffuse += ...` line is deleted from lights_physical_pars_fragment),
//      so the sun contributes specular highlights only;
//   2. the PMREM environment's diffuse irradiance -> `iblIrradiance += getIBLIrradiance(...)` is deleted
//      from lights_fragment_maps, so the environment contributes specular radiance only.
// What is left: lightMap irradiance (diffuse) + sun specular + env specular.  No shadow maps are used:
// the shadowing is in the lightmap.
//
// LIGHTMAP ENCODING (manifest v4 `lightmaps.decode`, never guessed).  `encoding`:
//   'linear'  a float .hdr/.exr texture, no decode;
//   'rgbm' / 'rgbm8'   rgb = t.rgb * t.a * range        (lossless KTX2 only - the M channel cannot
//                      survive block compression);
//   'gamma2'  rgb = t.rgb * t.rgb * range               (UASTC/ASTC, the shipped default);
//   'srgb'    decoded by three itself from the texture colorSpace.
// `range` is PER TEXTURE and is not 64 by default.
//
// SLOT ATLASES (the user's ORN option (c)).  988 instances share 5 4096 px atlases of 256 px slots
// (248 usable, 4 px gutter).  Each instance carries its own UV2 window as an InstancedBufferAttribute
// `pfaSlot = (offset.u, offset.v, scale)`, and `pfaSlotB` selects the second atlas for the three
// meshes whose instances straddle two (colonnade astragals, rotunda columns, ORN drum band).
import * as THREE from 'three';

// SPECULAR GATE (Phase 9, docs/briefs/phase9_bake_analysis_report.md B.6, decisions.md 2026-09-20).
// The two terms above leave the DIFFUSE side correct and the SPECULAR side ungated: three.js has no
// specular occlusion, so a shaft deep inside the colonnade reflects the whole open sky, and this sun
// casts no shadow map, so the same shaft takes the full specular lobe.  Measured at station 3 that is
// the entire shade excess — an additive (+0.45, +0.35, +0.24) scene-linear veil, 63 % unshadowed sun
// specular / 37 % unoccluded sky specular, on a lightmap that is itself right to 0.3 %.
//
// The lightmap already carries both visibilities, because LIGHT_sun ships at (1, 0.607, 0) — ZERO
// blue — so a texel's blue channel IS the sky's own contribution at that point:
//     skyVis = lightmap.b / openSky.b                                  scales the IBL specular
//     sunVis = (lightmap.r - (openSky.r/openSky.b)*lightmap.b) / sunIrrOverPi   scales directSpecular
// UNITS, which is where this goes wrong if it goes wrong at all.  `lightMapIrradiance` in the chunk
// below is the decoded texel TIMES `lightMapIntensity` (= manifest `lightmaps.scale`, pi), because
// three divides by pi again in BRDF_Lambert.  The manifest's two constants are in the BAKE's units —
// Cycles' colour-off diffuse pass, irradiance/pi — so the scale is divided back out before either
// ratio is formed.  Dividing by the live uniform, rather than folding pi into the constants, is what
// keeps `?lmscale=` honest: the gate follows whatever scale the material actually got.
const SPEC_GATE_DECLS = 'float pfaSkyVis = 1.0;\n\tfloat pfaSunVis = 1.0;\n';
const IBL_RADIANCE_LINE = 'radiance += iblRadiance;';

/**
 * The compiled-in constants, or null when the manifest does not carry them (then nothing is gated and
 * the viewer keeps the Phase 8 path).  NEVER defaulted to a guess: a wrong denominator here is a
 * wrong specular everywhere, and silently.
 * @param {number[]} openSky manifest `sky.open_irradiance_over_pi`, scene-linear irradiance/pi
 * @param {number} sunIrrOverPi manifest `sun.irradiance_over_pi`
 */
export function specGateFrom( openSky, sunIrrOverPi ) {
	const s = Array.isArray( openSky ) ? openSky.map( Number ) : null;
	const n = Number( sunIrrOverPi );
	if ( ! s || s.length !== 3 || ! s.every( v => Number.isFinite( v ) && v > 0 ) ) return null;
	if ( ! Number.isFinite( n ) || n <= 0 ) return null;
	return { openSky: s, openSkyB: s[ 2 ], skyRedOverBlue: s[ 0 ] / s[ 2 ], sunIrrOverPi: n };
}

/** The reference implementation of the gate, in the BAKE's units (irradiance/pi).  `specGateGlsl`
 *  below is generated to compute exactly this; web/test/spec_gate_test.mjs checks both against the
 *  B.6 decile table and checks that the emitted GLSL carries these same three constants. */
export function specGateEval( lmOverPi, g ) {
	if ( ! g ) return { skyVis: 1, sunVis: 1 };
	const [ r, , b ] = lmOverPi;
	const cl = ( v ) => Math.min( 1, Math.max( 0, v ) );
	return { skyVis: cl( b / g.openSkyB ), sunVis: cl( ( r - g.skyRedOverBlue * b ) / g.sunIrrOverPi ) };
}

/** GLSL for the gate, to be inserted directly after the lightmap decode line. */
export function specGateGlsl( g ) {
	return '\n\t\tif ( lightMapIntensity > 1e-6 ) {                      // PFA specular gate (B.6)\n'
		+ '\t\t\tvec3 pfaLmPi = lightMapIrradiance / lightMapIntensity;   // back to the bake\'s irradiance/pi\n'
		+ `\t\t\tpfaSkyVis = clamp( pfaLmPi.b / ${g.openSkyB.toFixed( 6 )}, 0.0, 1.0 );\n`
		+ `\t\t\tpfaSunVis = clamp( ( pfaLmPi.r - ${g.skyRedOverBlue.toFixed( 6 )} * pfaLmPi.b ) `
		+ `/ ${g.sunIrrOverPi.toFixed( 6 )}, 0.0, 1.0 );\n\t\t}`;
}

const DIRECT_DIFFUSE_LINE =
	'reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseContribution ) * ( 1.0 - F );';
const IBL_IRRADIANCE_LINE = 'iblIrradiance += getIBLIrradiance( geometryNormal );';
const LM_FETCH_LINE = 'vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );';
const LM_DECODE_LINE = 'vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;';

/** GLSL for `lightMapIrradiance` given the manifest's encode string. */
export function decodeGlsl( enc, range ) {
	const r = Number( range );
	if ( enc === 'rgbm' || enc === 'rgbm8' )
		return `vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapTexel.a * ${r.toFixed( 6 )} * lightMapIntensity;`;
	if ( enc === 'gamma2' )
		return `vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapTexel.rgb * ${r.toFixed( 6 )} * lightMapIntensity;`;
	return LM_DECODE_LINE;                    // 'linear' / 'srgb': three's own path is already right
}

function once( src, needle, replacement, what ) {
	const n = src.split( needle ).length - 1;
	if ( n !== 1 ) throw new Error( `shader patch "${what}": expected 1 occurrence, found ${n} (three version drift)` );
	return src.replace( needle, replacement );
}

/**
 * @param {THREE.MeshStandardMaterial} mat
 * @param {{ specularOnlySun?:boolean, noEnvDiffuse?:boolean, lightMapEncoding?:string,
 *           rgbmMaxRange?:number, range?:number, slot?:boolean, atlasB?:THREE.Texture|null,
 *           flipV?:boolean, vertexIrradiance?:number, instanceIrradiance?:number,
 *           specGate?:{openSkyB:number,skyRedOverBlue:number,sunIrrOverPi:number}|null }} opts
 */
export function patchBakedMaterial( mat, opts = {} ) {
	const specularOnlySun = opts.specularOnlySun !== false;
	const noEnvDiffuse = opts.noEnvDiffuse !== false;
	const enc = opts.lightMapEncoding || 'linear';
	// `range` is the v4 per-texture value; `rgbmMaxRange` is the Gate 0/2 name for the same thing.
	const maxRange = opts.range ?? opts.rgbmMaxRange ?? 7.0;
	const slot = !! opts.slot;
	// Diagnostic only (?lmflip=1).  glTF UVs have their origin at the TOP left and Blender's at the
	// bottom left; whether the baked map needs the flip is a property of how the encoder wrote the
	// image, so it is measured against the Cycles frame rather than assumed either way.
	const flipV = !! opts.flipV;
	// Vertex irradiance (the 14 near trees): COLOR_0 carries the BAKED irradiance, gamma-2 at a
	// per-mesh range.  glTF would multiply it into base colour; here it is light, so the tint is
	// removed from color_fragment and the decoded value is added to `irradiance` instead.  The value
	// passed in is range * lightmaps.scale, so the shader constant is the whole decode.
	const vertexIrr = typeof opts.vertexIrradiance === 'number' ? opts.vertexIrradiance : null;
	// Gate 4 item 1c: one baked irradiance per shrub/reed PLACEMENT, uploaded as an
	// InstancedBufferAttribute exactly like the ORN slot offsets.  `pfaInstOn` is 1 where the bake
	// measured the placement (cov > 0) and 0 for the 7 fully enclosed cards, and it switches BOTH
	// halves at once: where it is 1 the env (probe) diffuse is removed and the baked value is the
	// irradiance; where it is 0 the probe path is untouched, which is the contract the manifest states.
	// The value passed in is lightmaps.scale (pi), so the shader constant is the whole decode.
	const instIrr = typeof opts.instanceIrradiance === 'number' ? opts.instanceIrradiance : null;
	// The B.6 specular gate.  Only the two LIGHTMAP call sites in lightmaps.js pass it: a material with
	// no lightmap (impostors, water, backdrop, foliage cards, the vertex/instance irradiance paths) has
	// no `lightMapIrradiance` to read a visibility from, so it is left exactly as it was.  `null` (the
	// default, and what `?specgate=0` forces) emits no GLSL and no cache-key term at all, so the Phase 8
	// program is reproduced character for character.
	const gate = opts.specGate || null;
	if ( mat.userData.pfaPatched ) return mat;
	mat.userData.pfaPatched = { specularOnlySun, noEnvDiffuse, enc, maxRange, slot, flipV, vertexIrr, instIrr,
		specGate: gate ? { openSkyB: gate.openSkyB, skyRedOverBlue: gate.skyRedOverBlue, sunIrrOverPi: gate.sunIrrOverPi } : null };
	// PHASE 8b ITEM B, review r3 finding 2.  The SLOT path writes `pfaLmAtlasB` straight into
	// `shader.uniforms` inside onBeforeCompile, where nothing can reach it: a MeshStandardMaterial has
	// no `.uniforms` of its own, so `residentBytes()` walked past the second lightmap atlas exactly as
	// it used to walk past the impostor atlases.  Every texture a patch binds is recorded here instead,
	// at patch time and again at compile time with the value the shader actually got.
	mat.userData.pfaUniformTextures = mat.userData.pfaUniformTextures || [];
	if ( slot && opts.atlasB ) mat.userData.pfaUniformTextures.push( opts.atlasB );
	if ( vertexIrr !== null ) mat.vertexColors = true;         // so three declares vColor for us

	const prevCompile = mat.onBeforeCompile;
	mat.onBeforeCompile = function ( shader, renderer ) {
		if ( prevCompile ) prevCompile.call( this, shader, renderer );
		if ( specularOnlySun ) {
			let chunk = THREE.ShaderChunk.lights_physical_pars_fragment;
			chunk = once( chunk, DIRECT_DIFFUSE_LINE,
				'// PFA: direct diffuse removed - the lightmap already carries the sun diffuse (specular-only sun)',
				'specular-only sun' );
			shader.fragmentShader = once( shader.fragmentShader,
				'#include <lights_physical_pars_fragment>', chunk, 'lights_physical_pars_fragment include' );
		}
		if ( vertexIrr !== null ) {
			// glTF's own use of COLOR_0 is a base-colour tint; these meshes carry light, not colour.
			shader.fragmentShader = once( shader.fragmentShader, '#include <color_fragment>',
				'// PFA: COLOR_0 is BAKED IRRADIANCE on this mesh, not a vertex tint - see below',
				'vertex-irradiance colour tint removed' );
		}
		const decode = decodeGlsl( enc, maxRange );
		if ( noEnvDiffuse || decode !== LM_DECODE_LINE || slot || flipV || vertexIrr !== null || instIrr !== null || gate ) {
			let maps = THREE.ShaderChunk.lights_fragment_maps;
			if ( instIrr !== null ) {
				maps = once( maps, IBL_IRRADIANCE_LINE,
					'iblIrradiance += ( 1.0 - vPfaInstOn ) * getIBLIrradiance( geometryNormal );   // PFA: the probe only where the bake measured nothing',
					'instance-irradiance env gate' );
				maps += `\n\tirradiance += vPfaInstIrr * ${instIrr.toFixed( 6 )};`;
			}
			if ( noEnvDiffuse ) {
				maps = once( maps, IBL_IRRADIANCE_LINE,
					'// PFA: env diffuse irradiance removed - the lightmap already carries the sky diffuse',
					'no env diffuse' );
			}
			if ( flipV && ! slot ) {
				maps = once( maps, LM_FETCH_LINE,
					'vec4 lightMapTexel = texture2D( lightMap, vec2( vLightMapUv.x, 1.0 - vLightMapUv.y ) );',
					'lightmap V flip' );
			}
			if ( slot ) {
				// The instance's own window into the 4K slot atlas.  vLightMapUv is the mesh's [0,1]
				// UV2; clamping it keeps a wrapped or slightly out-of-range texel inside the slot's
				// 248 usable px instead of bleeding into the neighbour's.
				maps = once( maps, LM_FETCH_LINE,
					`vec2 pfaSlotUv0 = clamp( vLightMapUv, 0.0, 1.0 );${flipV ? '\n\t\tpfaSlotUv0.y = 1.0 - pfaSlotUv0.y;' : ''}\n`
					+ '\t\tvec2 pfaSlotUv = pfaSlotUv0 * vPfaSlot.z + vPfaSlot.xy;\n'
					+ '\t\tvec4 lightMapTexel = mix( texture2D( lightMap, pfaSlotUv ), texture2D( pfaLmAtlasB, pfaSlotUv ), vPfaSlotB );',
					'slot atlas lightmap fetch' );
			}
			if ( decode !== LM_DECODE_LINE ) maps = once( maps, LM_DECODE_LINE, decode, `${enc} lightmap decode` );
			if ( vertexIrr !== null ) {
				// gamma2 per mesh: v = c*c*range, then irradiance = v * lightmaps.scale (pi).
				// Both factors are folded into the constant below.
				maps += `\n\tirradiance += vColor.rgb * vColor.rgb * ${vertexIrr.toFixed( 6 )};`;
			}
			if ( gate ) {
				// The two visibilities are computed where the decoded texel is in scope (inside the
				// chunk's `#ifdef USE_LIGHTMAP`), and applied where each term is: `radiance` is the IBL
				// specular, accumulated a few lines below inside the env block, and
				// `reflectedLight.directSpecular` is already complete here — lights_fragment_begin ran
				// every RE_Direct before this chunk, and lights_fragment_end only adds INDIRECT specular
				// afterwards, from `radiance`.  Both declarations sit outside every #if, so a program
				// compiled without USE_LIGHTMAP or without USE_ENVMAP keeps 1.0 and is unchanged.
				maps = SPEC_GATE_DECLS + once( maps, decode, decode + specGateGlsl( gate ), 'spec gate' );
				maps = once( maps, IBL_RADIANCE_LINE, 'radiance += iblRadiance * pfaSkyVis;',
					'spec gate: IBL specular occlusion' );
				maps += '\n\treflectedLight.directSpecular *= pfaSunVis;   // PFA: the sun casts no shadow map';
			}
			shader.fragmentShader = once( shader.fragmentShader,
				'#include <lights_fragment_maps>', maps, 'lights_fragment_maps include' );
		}
		if ( instIrr !== null ) {
			shader.vertexShader = once( shader.vertexShader, '#include <common>',
				'#include <common>\nattribute vec3 pfaInstIrr;\nattribute float pfaInstOn;\n'
				+ 'varying vec3 vPfaInstIrr;\nvarying float vPfaInstOn;', 'instance-irradiance attributes' );
			shader.vertexShader = once( shader.vertexShader, '#include <uv_vertex>',
				'#include <uv_vertex>\n\tvPfaInstIrr = pfaInstIrr;\n\tvPfaInstOn = pfaInstOn;',
				'instance-irradiance varying write' );
			shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
				'#include <common>\nvarying vec3 vPfaInstIrr;\nvarying float vPfaInstOn;',
				'instance-irradiance varyings (fragment)' );
		}
		if ( slot ) {
			const atlasB = opts.atlasB || mat.lightMap;
			shader.uniforms.pfaLmAtlasB = { value: atlasB };
			// ... and again with what the shader actually got: `mat.lightMap` may have been attached
			// after the patch, and a texture that is never recorded is a texture that is never billed.
			const rec = mat.userData.pfaUniformTextures || ( mat.userData.pfaUniformTextures = [] );
			if ( atlasB && ! rec.includes( atlasB ) ) rec.push( atlasB );
			shader.vertexShader = once( shader.vertexShader, '#include <common>',
				'#include <common>\nattribute vec3 pfaSlot;\nattribute float pfaSlotB;\n'
				+ 'varying vec3 vPfaSlot;\nvarying float vPfaSlotB;', 'slot attributes' );
			shader.vertexShader = once( shader.vertexShader, '#include <uv_vertex>',
				'#include <uv_vertex>\n\tvPfaSlot = pfaSlot;\n\tvPfaSlotB = pfaSlotB;', 'slot varying write' );
			shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
				'#include <common>\nuniform sampler2D pfaLmAtlasB;\nvarying vec3 vPfaSlot;\nvarying float vPfaSlotB;',
				'slot varyings (fragment)' );
		}
		mat.userData.pfaShaderPatched = true;
	};
	const prevKey = mat.customProgramCacheKey;
	mat.customProgramCacheKey = function () {
		// The gate's term is APPENDED only when the gate is on, so `?specgate=0` reproduces the Phase 8
		// key character for character and shares its program.
		return `${prevKey ? prevKey.call( this ) : ''}|pfa:${specularOnlySun ? 1 : 0}${noEnvDiffuse ? 1 : 0}:${enc}:${maxRange}:${slot ? 1 : 0}:${flipV ? 1 : 0}:${vertexIrr === null ? 'n' : vertexIrr.toFixed( 6 )}:${instIrr === null ? 'n' : instIrr.toFixed( 6 )}`
			+ ( gate ? `|sg:${gate.openSkyB.toFixed( 6 )}:${gate.skyRedOverBlue.toFixed( 6 )}:${gate.sunIrrOverPi.toFixed( 6 )}` : '' );
	};
	mat.needsUpdate = true;
	return mat;
}

/** Attach a lightmap on UV2 (glTF TEXCOORD_1 -> three attribute `uv1`, selected by channel 1). */
export function attachLightMap( mat, texture, intensity = 1.0 ) {
	texture.flipY = false;                 // glTF UV convention
	texture.channel = 1;                   // UV2
	texture.colorSpace = THREE.NoColorSpace;   // every lightmap variant is LINEAR data
	texture.needsUpdate = true;
	mat.lightMap = texture;
	mat.lightMapIntensity = intensity;
	mat.needsUpdate = true;
	return mat;
}
