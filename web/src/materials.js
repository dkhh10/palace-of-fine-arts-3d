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
 *           rgbmMaxRange?:number, range?:number, slot?:boolean, atlasB?:THREE.Texture|null }} opts
 */
export function patchBakedMaterial( mat, opts = {} ) {
	const specularOnlySun = opts.specularOnlySun !== false;
	const noEnvDiffuse = opts.noEnvDiffuse !== false;
	const enc = opts.lightMapEncoding || 'linear';
	// `range` is the v4 per-texture value; `rgbmMaxRange` is the Gate 0/2 name for the same thing.
	const maxRange = opts.range ?? opts.rgbmMaxRange ?? 7.0;
	const slot = !! opts.slot;
	if ( mat.userData.pfaPatched ) return mat;
	mat.userData.pfaPatched = { specularOnlySun, noEnvDiffuse, enc, maxRange, slot };

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
		const decode = decodeGlsl( enc, maxRange );
		if ( noEnvDiffuse || decode !== LM_DECODE_LINE || slot ) {
			let maps = THREE.ShaderChunk.lights_fragment_maps;
			if ( noEnvDiffuse ) {
				maps = once( maps, IBL_IRRADIANCE_LINE,
					'// PFA: env diffuse irradiance removed - the lightmap already carries the sky diffuse',
					'no env diffuse' );
			}
			if ( slot ) {
				// The instance's own window into the 4K slot atlas.  vLightMapUv is the mesh's [0,1]
				// UV2; clamping it keeps a wrapped or slightly out-of-range texel inside the slot's
				// 248 usable px instead of bleeding into the neighbour's.
				maps = once( maps, LM_FETCH_LINE,
					'vec2 pfaSlotUv = clamp( vLightMapUv, 0.0, 1.0 ) * vPfaSlot.z + vPfaSlot.xy;\n'
					+ '\t\tvec4 lightMapTexel = mix( texture2D( lightMap, pfaSlotUv ), texture2D( pfaLmAtlasB, pfaSlotUv ), vPfaSlotB );',
					'slot atlas lightmap fetch' );
			}
			if ( decode !== LM_DECODE_LINE ) maps = once( maps, LM_DECODE_LINE, decode, `${enc} lightmap decode` );
			shader.fragmentShader = once( shader.fragmentShader,
				'#include <lights_fragment_maps>', maps, 'lights_fragment_maps include' );
		}
		if ( slot ) {
			shader.uniforms.pfaLmAtlasB = { value: opts.atlasB || mat.lightMap };
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
		return `${prevKey ? prevKey.call( this ) : ''}|pfa:${specularOnlySun ? 1 : 0}${noEnvDiffuse ? 1 : 0}:${enc}:${maxRange}:${slot ? 1 : 0}`;
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
