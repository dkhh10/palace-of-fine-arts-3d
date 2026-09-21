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
//     skyVis = lightmap.b / E0(n).b                                        scales the IBL specular
//     sunVis = (lightmap.r - (E0(n).r/E0(n).b)*lightmap.b)
//              / (sunIrrOverPi * max(dotNL, 0.05))                         scales directSpecular
// UNITS, which is where this goes wrong if it goes wrong at all.  `lightMapIrradiance` in the chunk
// below is the decoded texel TIMES `lightMapIntensity` (= manifest `lightmaps.scale`, pi), because
// three divides by pi again in BRDF_Lambert.  The manifest's constants are in the BAKE's units —
// Cycles' colour-off diffuse pass, irradiance/pi — so the scale is divided back out before either
// ratio is formed.  The division is by the live uniform rather than a folded-in pi, so the gate
// follows whatever scale the material actually got.
//
// ROUND 2 (decisions.md 2026-09-21), after the six-station capture measured round 1:
//   1. `E0(n)` REPLACES the constant `openSky`.  Round 1 divided every texel's blue by the open-sky
//      irradiance of an UPWARD-facing surface (11.256).  A vertical wall never sees more than half the
//      sky and an east wall under this sky much less, so fully unoccluded walls read skyVis 0.14-0.5
//      and lost most of their IBL specular, which Cycles keeps: the 0.5 % parity budget outside shade
//      was missed at all six stations (0.67-6.59 %) and cam05 regressed (p10 64.3 -> 55.2 against
//      Cycles' 64.9).  `E0(n)` is the same sky resolved for the surface's OWN world normal, so an
//      unoccluded surface of any orientation reads exactly 1.0.  It is evaluated from the manifest's
//      `sky.diffuse_lobes` (40 delta lobes; the brief's SH9 is 23-58 % high on this near-horizon sky
//      and is written to the manifest for the record only — manifest_v4.py says why, with numbers).
//   2. `sunVis` is DIVIDED BY dotNL.  (lm.r - k*lm.b)/sunIrrOverPi is sunVis*dotNL, and it multiplied
//      `reflectedLight.directSpecular`, which already carries dotNL (three's RE_Direct: irradiance =
//      dotNL * lightColor) — so the sun's specular was darkened by dotNL twice.  dotNL is taken from
//      the same geometry normal against the manifest's own sun direction, and floored at 0.05 so a
//      grazing face cannot amplify.
//   3. The sky's red share removed from lm.r is `E0(n).r / E0(n).b`, not the constant 0.195: under
//      this sky an east wall's unoccluded sky is 2.5x RED-over-blue, and subtracting 0.195 there would
//      leave the sky's own warmth in the sun's channel.
// `?specgate=1` keeps round 1 reachable for the A/B; `?specgate=0` is the Phase 8 path.
const SPEC_GATE_DECLS = 'float pfaSkyVis = 1.0;\n\tfloat pfaSunVis = 1.0;\n';
const IBL_RADIANCE_LINE = 'radiance += iblRadiance;';

const cl01 = ( v ) => Math.min( 1, Math.max( 0, v ) );

/**
 * The compiled-in constants, or null when the manifest does not carry them (then nothing is gated and
 * the viewer keeps the Phase 8 path).  NEVER defaulted to a guess: a wrong denominator here is a
 * wrong specular everywhere, and silently.
 * @param {number[]} openSky manifest `sky.open_irradiance_over_pi`, scene-linear irradiance/pi
 * @param {number} sunIrrOverPi manifest `sun.irradiance_over_pi`
 * @param {{lobes?:number[][], floorFrac?:number, sunDir?:number[]}} [opts] manifest
 *        `sky.diffuse_lobes` + the unit direction TOWARD the sun in three world axes.  Absent (or
 *        `mode: 'r1'`) builds the ROUND 1 gate, which is only right for an upward-facing surface.
 */
export function specGateFrom( openSky, sunIrrOverPi, opts = null ) {
	const s = Array.isArray( openSky ) ? openSky.map( Number ) : null;
	const n = Number( sunIrrOverPi );
	if ( ! s || s.length !== 3 || ! s.every( v => Number.isFinite( v ) && v > 0 ) ) return null;
	if ( ! Number.isFinite( n ) || n <= 0 ) return null;
	const r1 = { mode: 'r1', openSky: s, openSkyB: s[ 2 ], skyRedOverBlue: s[ 0 ] / s[ 2 ], sunIrrOverPi: n };
	if ( ! opts || opts.mode === 'r1' ) return r1;
	// round 2 needs BOTH halves of its own inputs; without them it is not round 1 by default, because
	// round 1's sunlit end is the defect this round exists to fix.  Gate OFF is the stated fallback.
	const lobes = Array.isArray( opts.lobes ) ? opts.lobes.map( l => Array.from( l, Number ) ) : null;
	const sun = Array.isArray( opts.sunDir ) ? Array.from( opts.sunDir, Number ) : null;
	const ff = Number( opts.floorFrac );
	if ( ! lobes || lobes.length < 8
		|| ! lobes.every( l => l.length === 6 && l.every( Number.isFinite )
			&& Math.abs( Math.hypot( l[ 0 ], l[ 1 ], l[ 2 ] ) - 1 ) < 1e-3
			&& l[ 3 ] >= 0 && l[ 4 ] >= 0 && l[ 5 ] >= 0 ) ) return null;
	if ( ! sun || sun.length !== 3 || ! sun.every( Number.isFinite )
		|| Math.abs( Math.hypot( ...sun ) - 1 ) > 1e-3 ) return null;
	if ( ! Number.isFinite( ff ) || ! ( ff > 0 ) || ff >= 0.5 ) return null;
	const zenithB = skyE0OverPi( lobes, [ 0, 1, 0 ] )[ 1 ];
	if ( ! ( zenithB > 0 ) ) return null;
	return { ...r1, mode: 'r2', lobes, sunDir: sun, floorFrac: ff, floor: ff * zenithB, zenithB };
}

/** `E0(n)/pi` — the UNOCCLUDED sky irradiance/pi for a world normal (three axes), as (r, b).  The
 *  shader's `pfaSkyE0` is generated to compute exactly this. */
export function skyE0OverPi( lobes, n ) {
	let r = 0, b = 0;
	for ( let i = 0; i < lobes.length; i ++ ) {
		const l = lobes[ i ];
		const c = l[ 0 ] * n[ 0 ] + l[ 1 ] * n[ 1 ] + l[ 2 ] * n[ 2 ];
		if ( c > 0 ) { r += c * l[ 3 ]; b += c * l[ 5 ]; }
	}
	return [ r, b ];
}

/** The reference implementation of the gate, in the BAKE's units (irradiance/pi).  `specGateGlsl`
 *  below is generated to compute exactly this; web/test/spec_gate_test.mjs checks both against the
 *  B.6 decile table and checks that the emitted GLSL carries these same constants.
 *  @param {number[]} lmOverPi the decoded texel divided by lightMapIntensity
 *  @param {number[]} [normal] the surface's WORLD normal (three axes) — required by round 2 */
export function specGateEval( lmOverPi, g, normal = null ) {
	if ( ! g ) return { skyVis: 1, sunVis: 1 };
	const [ r, , b ] = lmOverPi;
	if ( g.mode !== 'r2' )
		return { skyVis: cl01( b / g.openSkyB ), sunVis: cl01( ( r - g.skyRedOverBlue * b ) / g.sunIrrOverPi ) };
	const n = normal || [ 0, 1, 0 ];
	const [ e0r, e0b ] = skyE0OverPi( g.lobes, n );
	const den = Math.max( e0b, g.floor );
	const nl = Math.max( g.sunDir[ 0 ] * n[ 0 ] + g.sunDir[ 1 ] * n[ 1 ] + g.sunDir[ 2 ] * n[ 2 ], 0.05 );
	return { skyVis: cl01( b / den ), sunVis: cl01( ( r - ( e0r / den ) * b ) / ( g.sunIrrOverPi * nl ) ),
		e0: [ e0r, e0b ], dotNL: nl };
}

/** GLSL for `pfaSkyE0`, inserted after `#include <common>` in the fragment shader (round 2 only). */
export function specGateCommonGlsl( g ) {
	if ( ! g || g.mode !== 'r2' ) return '';
	const f = ( v ) => v.toFixed( 6 );
	return '\n// PFA specular gate (round 2): the UNOCCLUDED sky irradiance/pi for a world normal, as\n'
		+ '// (r, b).  40 delta lobes from the manifest\'s sky.diffuse_lobes — the same sky_diffuse\n'
		+ '// equirect the PMREM is built from, resolved per normal instead of per scene.\n'
		+ `const vec3 pfaSunDirW = vec3( ${g.sunDir.map( f ).join( ', ' )} );   // TOWARD the sun, three axes\n`
		+ 'vec2 pfaSkyE0( const in vec3 n ) {\n\tvec2 e = vec2( 0.0 );\n'
		+ g.lobes.map( l => `\te += max( dot( n, vec3( ${f( l[ 0 ] )}, ${f( l[ 1 ] )}, ${f( l[ 2 ] )} ) ), 0.0 )`
			+ ` * vec2( ${f( l[ 3 ] )}, ${f( l[ 5 ] )} );\n` ).join( '' )
		+ '\treturn e;\n}\n';
}

/** GLSL for the gate, to be inserted directly after the lightmap decode line. */
export function specGateGlsl( g ) {
	if ( g.mode !== 'r2' )
		return '\n\t\tif ( lightMapIntensity > 1e-6 ) {                      // PFA specular gate (B.6)\n'
			+ '\t\t\tvec3 pfaLmPi = lightMapIrradiance / lightMapIntensity;   // back to the bake\'s irradiance/pi\n'
			+ `\t\t\tpfaSkyVis = clamp( pfaLmPi.b / ${g.openSkyB.toFixed( 6 )}, 0.0, 1.0 );\n`
			+ `\t\t\tpfaSunVis = clamp( ( pfaLmPi.r - ${g.skyRedOverBlue.toFixed( 6 )} * pfaLmPi.b ) `
			+ `/ ${g.sunIrrOverPi.toFixed( 6 )}, 0.0, 1.0 );\n\t\t}`;
	return '\n\t\tif ( lightMapIntensity > 1e-6 ) {                      // PFA specular gate (round 2)\n'
		+ '\t\t\tvec3 pfaLmPi = lightMapIrradiance / lightMapIntensity;   // back to the bake\'s irradiance/pi\n'
		+ '\t\t\tvec3 pfaWN = inverseTransformDirection( geometryNormal, viewMatrix );\n'
		+ '\t\t\tvec2 pfaE0 = pfaSkyE0( pfaWN );                          // the open sky for THIS normal\n'
		+ `\t\t\tfloat pfaDen = max( pfaE0.y, ${g.floor.toFixed( 6 )} );        // a soffit's E0.b is ~0\n`
		+ '\t\t\tpfaSkyVis = clamp( pfaLmPi.b / pfaDen, 0.0, 1.0 );\n'
		+ '\t\t\tfloat pfaNL = max( dot( pfaWN, pfaSunDirW ), 0.05 );     // directSpecular already has dotNL\n'
		+ '\t\t\tpfaSunVis = clamp( ( pfaLmPi.r - ( pfaE0.x / pfaDen ) * pfaLmPi.b ) '
		+ `/ ( ${g.sunIrrOverPi.toFixed( 6 )} * pfaNL ), 0.0, 1.0 );\n\t\t}`;
}

/** A short, stable digest of the round-2 constants, for the program cache key. */
export function specGateKey( g ) {
	if ( ! g ) return '';
	if ( g.mode !== 'r2' )
		return `|sg:${g.openSkyB.toFixed( 6 )}:${g.skyRedOverBlue.toFixed( 6 )}:${g.sunIrrOverPi.toFixed( 6 )}`;
	let h = 0x811c9dc5;
	for ( const c of `${g.lobes.map( l => l.map( v => v.toFixed( 6 ) ).join( ',' ) ).join( ';' )}` ) {
		h ^= c.charCodeAt( 0 ); h = Math.imul( h, 0x01000193 ) >>> 0;
	}
	return `|sg2:${g.floor.toFixed( 6 )}:${g.sunIrrOverPi.toFixed( 6 )}:${g.sunDir.map( v => v.toFixed( 4 ) ).join( ',' )}`
		+ `:${g.lobes.length}:${h.toString( 16 )}`;
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
		specGate: gate ? { mode: gate.mode, openSkyB: gate.openSkyB, skyRedOverBlue: gate.skyRedOverBlue,
			sunIrrOverPi: gate.sunIrrOverPi,
			...( gate.mode === 'r2' ? { lobes: gate.lobes.length, floor: gate.floor, sunDir: gate.sunDir } : {} ) } : null };
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
			if ( gate && gate.mode === 'r2' ) {
				// `pfaSkyE0` and the sun direction are file-scope in the fragment shader, so they are
				// declared once beside `inverseTransformDirection`'s own chunk and not per call site.
				shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
					`#include <common>${specGateCommonGlsl( gate )}`, 'spec gate: E0(n) lobes' );
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
			+ specGateKey( gate );
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
