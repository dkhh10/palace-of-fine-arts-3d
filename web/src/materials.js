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
// LIGHTMAP ENCODING.  `encoding` 'linear' (float .hdr/.exr texture) needs no decode; 'rgbm' multiplies
// rgb by a * maxRange; 'srgb' is decoded by three itself when the texture colorSpace is set.
import * as THREE from 'three';

const DIRECT_DIFFUSE_LINE =
	'reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseContribution ) * ( 1.0 - F );';
const IBL_IRRADIANCE_LINE = 'iblIrradiance += getIBLIrradiance( geometryNormal );';

function once( src, needle, replacement, what ) {
	const n = src.split( needle ).length - 1;
	if ( n !== 1 ) throw new Error( `shader patch "${what}": expected 1 occurrence, found ${n} (three version drift)` );
	return src.replace( needle, replacement );
}

/**
 * @param {THREE.MeshStandardMaterial} mat
 * @param {{ specularOnlySun?:boolean, noEnvDiffuse?:boolean, lightMapEncoding?:string, rgbmMaxRange?:number }} opts
 */
export function patchBakedMaterial( mat, opts = {} ) {
	const specularOnlySun = opts.specularOnlySun !== false;
	const noEnvDiffuse = opts.noEnvDiffuse !== false;
	const enc = opts.lightMapEncoding || 'linear';
	const maxRange = opts.rgbmMaxRange ?? 7.0;
	if ( mat.userData.pfaPatched ) return mat;
	mat.userData.pfaPatched = { specularOnlySun, noEnvDiffuse, enc, maxRange };

	mat.onBeforeCompile = ( shader ) => {
		if ( specularOnlySun ) {
			let chunk = THREE.ShaderChunk.lights_physical_pars_fragment;
			chunk = once( chunk, DIRECT_DIFFUSE_LINE,
				'// PFA: direct diffuse removed - the lightmap already carries the sun diffuse (specular-only sun)',
				'specular-only sun' );
			shader.fragmentShader = once( shader.fragmentShader,
				'#include <lights_physical_pars_fragment>', chunk, 'lights_physical_pars_fragment include' );
		}
		if ( noEnvDiffuse || enc === 'rgbm' ) {
			let maps = THREE.ShaderChunk.lights_fragment_maps;
			if ( noEnvDiffuse ) {
				maps = once( maps, IBL_IRRADIANCE_LINE,
					'// PFA: env diffuse irradiance removed - the lightmap already carries the sky diffuse',
					'no env diffuse' );
			}
			if ( enc === 'rgbm' ) {
				maps = once( maps, 'vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;',
					`vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapTexel.a * ${maxRange.toFixed( 1 )} * lightMapIntensity;`,
					'rgbm lightmap decode' );
			}
			shader.fragmentShader = once( shader.fragmentShader,
				'#include <lights_fragment_maps>', maps, 'lights_fragment_maps include' );
		}
		mat.userData.pfaShaderPatched = true;
	};
	mat.customProgramCacheKey = () => `pfa:${specularOnlySun ? 1 : 0}${noEnvDiffuse ? 1 : 0}:${enc}:${maxRange}`;
	mat.needsUpdate = true;
	return mat;
}

/** Attach a lightmap on UV2 (glTF TEXCOORD_1 -> three attribute `uv1`, selected by channel 1). */
export function attachLightMap( mat, texture, intensity = 1.0 ) {
	texture.flipY = false;                 // glTF UV convention
	texture.channel = 1;                   // UV2
	texture.needsUpdate = true;
	mat.lightMap = texture;
	mat.lightMapIntensity = intensity;
	mat.needsUpdate = true;
	return mat;
}
