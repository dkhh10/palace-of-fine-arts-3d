// Lagoon water: a planar Reflector at y = WATER_Z with a ripple normal map, murk tint and Fresnel.
// Not a mirror (attempts 1-2 failed on that): the reflection is broken up by the ripple normal and
// mixed toward a murky green by a Schlick Fresnel term, so only grazing angles read as reflective.
import * as THREE from 'three';
import { Reflector } from 'three/addons/objects/Reflector.js';

/**
 * QA-14-1 round 7 (i) + (ii).  THE RIPPLE, PROCEDURAL AND IN METRES.
 *
 * Round 6 drew the ripple into a 256 px 8-bit normal map tiled by `rippleTiling` 0.11, i.e. a 9.1 m
 * tile whose dominant wave was 1.8-9.1 m.  At the hero's near water a pixel is 2.76 cm, so those
 * crests were 40-80 px where the Phase 5 hero's are 5-10, and the open water away from the
 * reflection had no structure at all; and an 8-bit normal times a large displacement quantised the
 * reflection into visible stair-step contours.  Both defects are the texture, so the texture is
 * gone: the height field is now a sum of sine waves evaluated in the shader with ANALYTIC
 * derivatives - no quantisation, no mip level, and the wavelengths are set in METRES.
 *
 * The spectrum comes from docs/reference_sheet.md MAT_water_lagoon ("broken into 0.3-1 m streaks by
 * 2-5 cm ripples") and mat_build.py's own reading of ref 169 ("corrugated by 0.25-0.4 m ripples"):
 * eight waves geometrically spaced from LAMBDA_MAX 1.2 m (the swell that makes the streaks wander)
 * to LAMBDA_MIN 0.034 m (the capillary chop that makes the row-to-row grain QA measures as rowHF).
 *
 * Directions are concentrated about world Z with a cosine-power spread, as in round 6 and for the
 * same reason: `p = vWorld.xz`, the hero looks along world Z, so k along Z puts the crests ACROSS
 * the view and the reflection breaks into HORIZONTAL streaks rather than a grid.
 *
 * Amplitude is set by SLOPE, not by height, because slope is what displaces the reflection.  Each
 * wave carries the same slope amplitude `a`, so A_i = a * lambda_i / 2pi, and the rms of a sum of N
 * sines is a sqrt(N/2); `SLOPE_RMS` is therefore the whole surface's rms slope.  0.0131 rad (0.75
 * deg) is read back from the Phase 5 hero, not guessed: the reflection there wanders by ~30 px at
 * the near water, and the projection below turns a slope into exactly 2 * slope of reflected-ray
 * elevation, so 30 px of 1080 over a 53.7 deg frame is 0.0131 rad of surface slope.  It is also what
 * the reference sheet describes - "at golden hour the water is glassy with long warm reflections".
 *
 * Each wave also carries its own wavelength so the shader can FADE it out below ~1 pixel instead of
 * aliasing: a 3 cm wave is sub-pixel past ~25 m and would otherwise sizzle across the far lagoon.
 */
export const RIPPLE = {
	waves: 8,
	lambdaMax: 1.20,     // m
	lambdaMin: 0.034,    // m
	slopeRms: 0.0131,    // rad, the whole surface
	spreadDeg: 25,       // half-angle of the directional fan about world Z (crests across the view)
	gravity: 9.81,       // deep-water dispersion, omega = sqrt(g k), for the drift
};

/**
 * @returns {{a:number[][], b:number[][]}} per wave: a = [kx, kz, amplitude_m, omega], b = [phase, lambda_m, 0, 0]
 */
export function makeWaveSet( o = {} ) {
	const c = { ...RIPPLE, ...o };
	const n = c.waves, freq = o.freqScale ?? 1;
	const rnd = ( s => () => ( s = ( s * 1664525 + 1013904223 ) >>> 0 ) / 4294967296 )( 12345 );   // phases only
	const slopeEach = c.slopeRms / Math.sqrt( n / 2 );
	const a = [], b = [];
	for ( let i = 0; i < n; i ++ ) {
		const t = n > 1 ? i / ( n - 1 ) : 0;
		const lambda = c.lambdaMax * Math.pow( c.lambdaMin / c.lambdaMax, t ) / freq;
		const k = 2 * Math.PI / lambda;
		// direction: tight about +Z, the same cosine-power draw round 6 used for the texture
		// A STRATIFIED fan, not a random draw: eight random draws from a cosine-power spread put two
		// waves at 51 and 73 deg off axis, which is a cross sea, not wind ripple.  The directions are
		// therefore spaced evenly across +/- spreadDeg and decorrelated from the wavelength by the
		// 5i mod n permutation, so the set is reproducible and has no outlier.
		const j = ( i * 5 ) % n;
		const th = ( c.spreadDeg * Math.PI / 180 ) * ( 2 * ( j + 0.5 ) / n - 1 );
		a.push( [ k * Math.sin( th ), k * Math.cos( th ), slopeEach / k, Math.sqrt( c.gravity * k ) ] );
		b.push( [ rnd() * Math.PI * 2, lambda, 0, 0 ] );
	}
	return { a, b };
}

/**
 * QA-14-1 item 1a.  THE UPWELLING TERM, DERIVED - not fitted to the metric.
 *
 * `murk` in the shader below is the radiance that leaves the water BODY toward the camera, before
 * the Fresnel mix; the mix already applies the (1 - F) transmittance of the view ray, so `murk` is
 * the emergent radiance at normal incidence.  The round-14 value (0.020, 0.035, 0.030) was a hand
 * number and is ~13x too dark: it made the near water essentially `F * reflection`, i.e. a dark
 * blue mirror, where the Phase 5 hero's open water inverts through the LUT to a near-neutral
 * scene-linear (1.226, 1.317, 1.262).
 *
 * The inputs are the Phase 5 material's and the scene's own, in this order:
 *   1. MAT_water_lagoon's WATER_VOLUME node (scripts/mat_build.py build_water):
 *        sigma_s = density * Colour            = 0.7 * (0.205, 0.250, 0.195)
 *        sigma_a = density * (1 - AbsorpColour) = 0.7 * (1 - (0.70, 0.80, 0.68))
 *      This is the reference sheet's "volume absorption ~ (0.04, 0.07, 0.04)" line in its shipped
 *      form: single-scatter albedo (0.41, 0.56, 0.38), i.e. the green-tea murk.
 *   2. docs/reference_sheet.md MAT_water_lagoon: depth 1.5 m to a muddy bottom (0.12, 0.10, 0.06).
 *   3. The scene's own downward irradiance: the cosine-weighted integral of the CAMERA-branch sky
 *      equirect (export/out/gate0/sky_camera_4096x2048.exr) over the upper hemisphere, plus the
 *      manifest's LIGHT_sun (67.319 W/m^2 * sin 7.357 deg * colour (1, 0.6073, 0)).
 *      The camera branch, not sky.diffuse: sky.diffuse carries lighting's artificial shade fill
 *      (B/R 5.1 against the real sky's 4.4 and sky+sun's 1.3), and the Phase 5 material suppresses
 *      its own diffuse murk lobe to 0.085 at the hero precisely because that fill "returns blue and
 *      fights the warm streaks" (mat_build.py round 8).  The water body is real light off a real
 *      sky, so it takes the real sky.
 *
 * The chain, all of it Beer-Lambert over the two-way depth plus the two interface crossings:
 *   b_b     = sigma_s * B(g),  B = (1-g)/(2g) * ((1+g)/sqrt(1+g^2) - 1)   backscatter fraction, HG
 *   R_col   = b_b/(a+b_b) * (1 - exp(-2 (a+b_b) d))      light turned round inside the column
 *   R_bot   = rho * exp(-2 a d)                          light off the bed and back up
 *   A_up    = R_col + R_bot                              sub-surface upwelling albedo
 *   E_in    = t_sky * E_sky + t_sun * E_sun              what crosses the surface downward
 *             (t_sun is the Fresnel transmittance at the sun's 82.6 deg incidence = 0.544, which
 *              is why a 7.4 deg sun contributes so much less than its horizontal irradiance)
 *   E_up    = A_up * E_in / (1 - r_int * A_up)           r_int = 0.48, the diffuse internal reflectance
 *   murk    = E_up / (pi * n^2)                          isotropic in-water radiance, out through n
 *
 * Result (0.2353, 0.3522, 0.3166): hue 162 deg, i.e. green, against the round-14 value's 160 deg but
 * 10x its level.  Cross-check on the derivation, not on the metric: A_up comes out (0.150, 0.180,
 * 0.112) and the Phase 5 material's own hand-set diffuse murk albedo is (0.165, 0.170, 0.1025) -
 * the same quantity to within 10 %, reached independently.
 *
 * `?watermurk=0.020,0.035,0.030` restores the round-14 / WIP value exactly; `?watermurkgain=k`
 * scales the derived one for an A/B without changing its hue.
 */
export const MURK_INPUTS = {
	volumeDensity: 0.7,
	scatterColour: [ 0.205, 0.250, 0.195 ],      // WATER_VOLUME "Color"
	absorptionColour: [ 0.70, 0.80, 0.68 ],      // WATER_VOLUME "Absorption Color"
	anisotropy: 0.3,                             // WATER_VOLUME "Anisotropy" (Henyey-Greenstein g)
	depth_m: 1.5,                                // docs/reference_sheet.md
	bottomAlbedo: [ 0.12, 0.10, 0.06 ],          // docs/reference_sheet.md, the muddy bed
	skyIrradiance: [ 3.651, 7.626, 16.040 ],     // W/m^2, sky_camera_4096x2048.exr, upper hemisphere
	sunIrradiance: [ 8.622, 5.236, 0.0 ],        // W/m^2 on the horizontal, manifest LIGHT_sun
	skyTransmittance: 0.934,                     // Fresnel-averaged, diffuse sky into water
	sunTransmittance: 0.544,                     // unpolarised Fresnel at 82.643 deg incidence
	internalReflectance: 0.48,                   // diffuse upwelling reflected back down at the surface
	ior: 1.333,
};

/** @returns {number[]} the emergent upwelling radiance (scene-linear RGB); see MURK_INPUTS. */
export function derivedMurk( i = MURK_INPUTS ) {
	const g = i.anisotropy;
	const B = ( 1 - g ) / ( 2 * g ) * ( ( 1 + g ) / Math.sqrt( 1 + g * g ) - 1 );
	const n2 = i.ior * i.ior, d = i.depth_m;
	return [ 0, 1, 2 ].map( ( c ) => {
		const sa = i.volumeDensity * ( 1 - i.absorptionColour[ c ] );
		const ss = i.volumeDensity * i.scatterColour[ c ];
		const bb = ss * B, k = sa + bb;
		const rCol = bb / k * ( 1 - Math.exp( - 2 * k * d ) );
		const rBot = i.bottomAlbedo[ c ] * Math.exp( - 2 * sa * d );
		const aUp = rCol + rBot;
		const eIn = i.skyTransmittance * i.skyIrradiance[ c ] + i.sunTransmittance * i.sunIrradiance[ c ];
		return aUp * eIn / ( 1 - i.internalReflectance * aUp ) / ( Math.PI * n2 );
	} );
}

const WaterShader = {
	uniforms: {
		color: { value: null }, tDiffuse: { value: null }, textureMatrix: { value: null },
		// the procedural ripple: 8 waves, a = (kx, kz, amplitude_m, omega), b = (phase, lambda_m, -, -)
		waveA: { value: [] }, waveB: { value: [] },
		time: { value: 0 }, distortion: { value: 1.0 },
		murk: { value: new THREE.Color( 0.020, 0.035, 0.030 ) },
		// A water-air Fresnel reflection is SPECTRALLY FLAT - see reflSat below.
		reflectTint: { value: new THREE.Color( 1.0, 1.0, 1.0 ) },
		normalScale: { value: 1.0 },          // gain on the derived slope; 1.0 = RIPPLE.slopeRms exactly
		rippleTiling: { value: 1.0 },         // frequency scale on the whole wave set; 1.0 = the metres above
		distortAniso: { value: 1.0 },
		// A ROUGH surface at a grazing angle does not reflect a point - its lobe is stretched toward
		// the HORIZON, so the near water carries the bright near-horizon band rather than the dark
		// zenith a mirror gives it.  That, not the murk, is why the reference's open water is bright
		// (lum 118) and nearly neutral (sat 0.041) while a mirror reads dark blue (66.8, sat 0.326).
		horizonBias: { value: 0.0 },
		// grazingGain 0 reproduces the round14 surface EXACTLY (the displacement is then n.xy *
		// distortion, as it was).  Every term added for QA-14-1 is opt-in until one is agreed, so the
		// shipped look cannot drift while the fix is still being searched for.
		grazingGain: { value: 0.0 },
		// THE WATER MUST RECEIVE THE COMPOSITOR'S AIRLIGHT LIKE EVERYTHING ELSE.  postChain.js adds the
		// haze through three's fog chunk, which a ShaderMaterial does not compile, and applyMist
		// explicitly skips WATER_*, so the one surface that spans 5-600 m at the hero was the only one
		// getting no haze at all.  Cycles' compositor hazes the whole frame including the water, which
		// is part of why the reference's open water is brighter (118 vs 67) and far less blue
		// (hue 145 vs 200).  Same airlight form as postChain and impostors: cap * (1 - exp(-k * mist)).
		fogColor: { value: new THREE.Color( 0, 0, 0 ) },
		fogNear: { value: 0.0 }, fogFar: { value: 1.0 },
		fogCap: { value: 0.0 }, fogK: { value: 1.0 }, fogIntensity: { value: 0.0 },
		// A real lagoon is a ROUGH, murky surface, not a mirror.  Two terms carry that, both
		// calibrated against the Phase 5 Cycles hero's water box (docs/qa_round_10b.md
		// 900 760 1020 840: lum 128.6, std 34.2, sat 0.33, R-B +34.4) - see makeWater().
		//   reflBlur   the slope distribution of the ripples: the reflection is gathered over a
		//              small disc instead of a point, which is what takes the edge off `std`.
		//   reflSat    ROUND 7: ships at 1.0.  It was 0.66 on the argument that "the murk scatters
		//              light back out through the reflected ray, washing its colour toward neutral",
		//              but that is the BODY term, which the derived murk now carries explicitly
		//              through the same mix - counting it twice drained 34 % of the chroma out of
		//              the reflected radiance and turned the golden ochre olive (round 7 (iii)).
		//              A dielectric's Fresnel reflection is spectrally flat, so 1.0 is the derived
		//              value and reflectTint is (1, 1, 1); ?watersat=0.66 is the A/B back.
		reflBlur: { value: 0.0 }, reflSat: { value: 1.0 },
		// QA-14-1 diagnostics: 1 = Fresnel F, 2 = the projected reflection uv (blue = out of range),
		// 3 = the perturbed normal's xy, 4 = the UNPERTURBED reflection sample, 5 = the murk term
		// alone, 6 = the gathered (perturbed, clamped, blurred) reflection alone.
		debugMode: { value: 0 },
		// Round 7 review FIX-NOW 1: the ceiling on the grazing multiplier; see the shader.
		grazingMax: { value: 6.0 },
	},
	vertexShader: /* glsl */`
		uniform mat4 textureMatrix;
		varying vec4 vProjUv;
		varying vec3 vWorld;
		void main() {
			vec4 wp = modelMatrix * vec4( position, 1.0 );
			vWorld = wp.xyz;
			vProjUv = textureMatrix * vec4( position, 1.0 );
			gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
		}
	`,
	fragmentShader: /* glsl */`
		uniform sampler2D tDiffuse;
		uniform vec4 waveA[ 8 ], waveB[ 8 ];
		uniform mat4 projectionMatrix;   // not injected into the fragment stage by three; set by the renderer
		uniform float time, distortion, normalScale, rippleTiling, reflBlur, reflSat, distortAniso, horizonBias, grazingGain, grazingMax;
		uniform vec3 fogColor;
		uniform float fogNear, fogFar, fogCap, fogK, fogIntensity;
		uniform int debugMode;
		uniform vec3 murk, reflectTint;
		varying vec4 vProjUv;
		varying vec3 vWorld;
		void main() {
			vec2 p = vWorld.xz;
			// The pixel's footprint on the water, in metres.  A wave shorter than about one footprint
			// cannot be resolved and would alias into a sizzle across the far lagoon, so it is faded
			// out instead - this is the viewer's equivalent of MAT_water_lagoon's Toksvig depth ramp.
			float px = max( fwidth( p.x ), fwidth( p.y ) );
			vec2 slope = vec2( 0.0 );
			for ( int i = 0; i < 8; i ++ ) {
				vec2 k = waveA[ i ].xy * rippleTiling;
				float fade = 1.0 - smoothstep( 0.5, 1.2, px / ( waveB[ i ].y / rippleTiling ) );
				slope += k * ( waveA[ i ].z * fade ) * cos( dot( k, p ) + waveA[ i ].w * time + waveB[ i ].x );
			}
			slope *= normalScale;
			vec3 n = normalize( vec3( - slope.x, - slope.y, 1.0 ) );
			vec3 N = normalize( vec3( n.x, n.z, n.y ) );                       // tangent -> world (plane is +Y up)
			vec4 uv = vProjUv;
			// THE DISPLACEMENT IS NOW DERIVED, not a dial.  A surface slope s tips the reflected ray by
			// 2s of direction, and the projection turns a direction change into an ndc change of P00 /
			// P11 times it; uv is half of ndc, so the screen-space offset is exactly P * slope.  Reading
			// projectionMatrix makes it right at every station instead of only at the hero's 20 mm lens.
			// distortion and distortAniso are therefore both 1.0 by default and are A/B dials only.
			// The round-6 grazing multiplier was NOT physical (the reflected ray tips by 2s whatever the
			// incidence) and ships at 0; grazingMax caps it for anyone who turns it back on, and the uv
			// is clamped so no sample can reach a ClampToEdge border texel (round 7 review FIX-NOW 1).
			float grazingRaw = clamp( 1.0 / max( dot( normalize( cameraPosition - vWorld ), N ), 0.02 ), 1.0, grazingMax );
			float grazing = mix( 1.0, grazingRaw, grazingGain );
			vec2 quv = uv.xy / max( uv.w, 1e-6 );
			quv.x += projectionMatrix[ 0 ][ 0 ] * slope.x * distortion * grazing;
			quv.y += ( projectionMatrix[ 1 ][ 1 ] * slope.y * distortAniso + horizonBias ) * distortion * grazing;
			quv = clamp( quv, 0.0, 1.0 );
			// A rough surface at a grazing angle has a lobe STRETCHED TOWARD THE HORIZON, not a disc.
			// Gathering only VERTICALLY (in screen space) is that stretch, and it is also what keeps
			// the horizontal structure the ripple just created: a disc gather would average the
			// streaks away, which is what the round14 water did.
			vec3 refl = texture2D( tDiffuse, quv ).rgb;
			if ( reflBlur > 0.0 ) {
				float b = reflBlur * grazing;
				refl += texture2D( tDiffuse, clamp( quv + vec2( 0.0,  b       ), 0.0, 1.0 ) ).rgb;
				refl += texture2D( tDiffuse, clamp( quv + vec2( 0.0, -b       ), 0.0, 1.0 ) ).rgb;
				refl += texture2D( tDiffuse, clamp( quv + vec2( 0.0,  b * 2.0 ), 0.0, 1.0 ) ).rgb;
				refl += texture2D( tDiffuse, clamp( quv + vec2( 0.0, -b * 2.0 ), 0.0, 1.0 ) ).rgb;
				refl *= 0.2;
			}
			refl *= reflectTint;
			// the murk scatters the reflection's colour toward neutral
			refl = mix( vec3( dot( refl, vec3( 0.2126, 0.7152, 0.0722 ) ) ), refl, reflSat );
			vec3 V = normalize( cameraPosition - vWorld );
			float c = clamp( dot( V, N ), 0.0, 1.0 );
			float F = 0.02 + 0.98 * pow( 1.0 - c, 5.0 );                        // water, IOR 1.33
			if ( debugMode == 1 ) { gl_FragColor = vec4( vec3( F ), 1.0 ); return; }
			if ( debugMode == 2 ) { vec2 q = uv.xy / max( uv.w, 1e-6 ); gl_FragColor = vec4( fract( q ), float( q.x < 0.0 || q.x > 1.0 || q.y < 0.0 || q.y > 1.0 ), 1.0 ); return; }
			if ( debugMode == 5 ) { gl_FragColor = vec4( murk, 1.0 ); return; }          // the upwelling term alone
			if ( debugMode == 6 ) { gl_FragColor = vec4( refl, 1.0 ); return; }          // the gathered reflection alone
			if ( debugMode == 3 ) { gl_FragColor = vec4( slope * 20.0 + 0.5, 0.0, 1.0 ); return; }
			if ( debugMode == 4 ) { gl_FragColor = vec4( texture2DProj( tDiffuse, vProjUv ).rgb, 1.0 ); return; }
			vec3 surf = mix( murk, refl, F );
			if ( fogCap > 0.0 ) {
				float fd = length( vWorld - cameraPosition );          // along the view ray, as Blender's mist
				float t = clamp( ( fd - fogNear ) / max( fogFar - fogNear, 1e-6 ), 0.0, 1.0 );
				float mist = fogIntensity + ( 1.0 - fogIntensity ) * t;
				surf = mix( surf, fogColor, clamp( fogCap * ( 1.0 - exp( - fogK * mist ) ), 0.0, 1.0 ) );
			}
			gl_FragColor = vec4( surf, 1.0 );
		}
	`,
};

/**
 * @param {number} waterY  WATER_Z in three space (y)
 * @param {{size?:number, resolution?:number, murk?:number[], tint?:number[], distortion?:number}} o
 */
export function makeWater( waterY, o = {} ) {
	const size = o.size ?? 1200;
	// Item 6: the Reflector renders the WHOLE SCENE a second time into this target - 6.3 ms at the
	// hero, 8.6 ms at the aerial, and it doubles the draw calls.  Halving it is nearly free visually
	// because `reflBlur` already gathers the reflection over a disc.
	// The plane is rotated on the OBJECT, not baked into the geometry: Reflector derives the mirror
	// normal from the object's world rotation (normal = +Z rotated by matrixWorld), so a geometry-baked
	// rotation leaves it reflecting about a vertical plane.
	const geo = new THREE.PlaneGeometry( size, size );
	const reflector = new Reflector( geo, {
		textureWidth: o.resolution ?? 1024,
		textureHeight: o.resolution ?? 1024,
		color: 0xffffff,
		shader: WaterShader,
		clipBias: 0.003,
	} );
	reflector.rotation.x = - Math.PI / 2;
	reflector.position.y = waterY;
	reflector.name = 'WATER_lagoon';
	const u = reflector.material.uniforms;
	const ws = makeWaveSet( { ...( o.waves ? { waves: o.waves } : {} ), ...( o.spread ? { spreadDeg: o.spread } : {} ),
		...( o.slopeRms !== undefined ? { slopeRms: o.slopeRms } : {} ) } );
	u.waveA.value = ws.a.map( ( v ) => new THREE.Vector4( ...v ) );
	u.waveB.value = ws.b.map( ( v ) => new THREE.Vector4( ...v ) );
	reflector.userData.waveSet = ws;
	// QA-14-1 item 1a: the DERIVED upwelling term is the default (see MURK_INPUTS / derivedMurk).
	// `o.murk` (?watermurk=r,g,b) overrides it outright; `o.murkGain` (?watermurkgain=k) scales it.
	reflector.userData.murkDerived = derivedMurk();
	u.murk.value.setRGB( ...reflector.userData.murkDerived.map( ( v ) => v * ( o.murkGain ?? 1 ) ) );
	if ( o.murk ) u.murk.value.setRGB( ...o.murk );
	if ( o.tint ) u.reflectTint.value.setRGB( ...o.tint );
	if ( o.distortion !== undefined ) u.distortion.value = o.distortion;
	if ( o.normalScale !== undefined ) u.normalScale.value = o.normalScale;
	if ( o.rippleTiling !== undefined ) u.rippleTiling.value = o.rippleTiling;
	if ( o.distortAniso !== undefined ) u.distortAniso.value = o.distortAniso;
	if ( o.horizonBias !== undefined ) u.horizonBias.value = o.horizonBias;
	if ( o.grazingGain !== undefined ) u.grazingGain.value = o.grazingGain;
	if ( o.grazingMax !== undefined ) u.grazingMax.value = o.grazingMax;
	reflector.userData.applyFog = ( fog ) => {
		if ( ! fog ) { u.fogCap.value = 0; return false; }
		u.fogColor.value.copy( fog.color );
		u.fogNear.value = fog.near; u.fogFar.value = fog.far;
		u.fogCap.value = fog.cap; u.fogK.value = fog.k; u.fogIntensity.value = fog.intensity || 0;
		return true;
	};
	// reflBlur stays the ripples' slope-distribution gather (0.003 of a screen, ~3 px at 1080).
	// reflSat is 1.0 from round 7: see the uniform's note - the desaturation double-counted the murk.
	u.reflBlur.value = o.reflBlur ?? 0.003;
	u.reflSat.value = o.reflSat ?? 1.0;
	// QA-14-1 round 6.  Measured at the hero against the Phase 5 reference: these take the open-water
	// row-to-row energy from 0.97 to 4.60 (reference 13.23) and the row/column ratio - the streaks
	// against a blur - from 0.72 to 2.23 (reference 3.24).  The level and the hue are NOT fixed by
	// them and are reported as still open.
	// All four are DERIVED-UNITY now: the wavelengths are in metres in makeWaveSet, the slope is
	// RIPPLE.slopeRms, and the screen displacement is projectionMatrix x slope.  They stay as A/B dials.
	u.distortion.value = o.distortion ?? 1.0;
	u.normalScale.value = o.normalScale ?? 1.0;
	u.rippleTiling.value = o.rippleTiling ?? 1.0;
	u.distortAniso.value = o.distortAniso ?? 1.0;
	u.grazingGain.value = o.grazingGain ?? 0.0;
	if ( o.debug ) u.debugMode.value = o.debug;
	reflector.userData.tick = ( t ) => { u.time.value = t; };
	return reflector;
}


/** Layer the reflection camera does NOT test; everything on it is excluded from the reflection. */
export const REFLECT_EXCLUDE_LAYER = 2;

/**
 * Item 6: cut the Reflector's DRAW SET, not its resolution.
 *
 * The planar Reflector renders the whole scene a second time - measured at 6.3 ms (hero) and 8.6 ms
 * (aerial), and it doubles the draw calls, 151 -> 301.  Halving its target recovered almost none of
 * that, because the cost is the second scene TRAVERSAL and the submit, not the fill: at half
 * resolution it still submitted all 314 draws.  Cutting what it traverses is the only lever that
 * touches the real cost.
 *
 * three's Reflector clones the MAIN camera to make its reflection camera, so the clone inherits the
 * main camera's layer mask.  This puts the excluded objects on their own layer, enables every layer
 * on the main camera so they still draw normally, and restricts each reflection camera to layer 0.
 *
 * What is cut and why: the 436 ORN instances (sub-pixel in a reflection that `reflBlur` gathers over
 * a disc, at hero distance) and the far backdrop city blocks (140-190 m away and behind the camera's
 * own reflected frustum at the lagoon stations).  ARCH, the ground, the water-adjacent ENV, the
 * impostors and the sky all stay.
 *
 * @returns {{excluded:number, orn:number, backdrop:number, kept:number}}
 */
export function reduceReflectionSet( scene, water, camera, { orn = true, backdrop = true, all = false, note = () => {} } = {} ) {
	const out = { excluded: 0, orn: 0, backdrop: 0, kept: 0, all };
	if ( ! water || ! water.getReflectionCamera ) return out;
	// v5 may ship several GROUPS of one class, so a root is `WEB_glb_orn` or `WEB_glb_orn_<group>`.
	const rootOf = ( o ) => { let p = o; while ( p && ! /^WEB_glb_/.test( p.name || '' ) ) p = p.parent; return p ? p.name : ''; };
	scene.traverse( ( o ) => {
		if ( ! o.isMesh ) return;
		const mats = Array.isArray( o.material ) ? o.material : [ o.material ];
		const name = mats.map( ( m ) => ( m && m.name ) || '' ).join( ' ' );
		// `all` is the MOBILE tier (device.js): every mesh leaves the reflection, so the Reflector's
		// second pass draws the background sphere alone.  The water still ripples and still reflects
		// the sky with the right Fresnel; it no longer reflects the building, which is the mobile
		// compromise the 6b plan asks for ("water without the planar Reflector") without giving the
		// lagoon a black surface or needing a second water shader.
		const isOrn = ! all && orn && /^WEB_glb_orn(_|$)/.test( rootOf( o ) );
		// Phase 8d renamed the far-ground slot-0 material MAT_lawn -> MAT_backdrop_lawn; the far ground stays IN the
		// reflection as it was before the rename (else a sky strip shows at the reflected horizon). Only the
		// vertical backdrop masses, roofs, glazing and the backdrop forest leave it, exactly the pre-8d set.
		const isBackdrop = ! all && backdrop && /MAT_EXP_ENVBD__MAT_backdrop_(?!lawn)/.test( name );
		if ( all && o !== water ) { o.layers.set( REFLECT_EXCLUDE_LAYER ); out.excluded ++; return; }
		if ( ! isOrn && ! isBackdrop ) { out.kept ++; return; }
		o.layers.set( REFLECT_EXCLUDE_LAYER );        // off layer 0, so the reflection camera misses it
		out.excluded ++;
		if ( isOrn ) out.orn ++; else out.backdrop ++;
	} );
	if ( camera ) camera.layers.enableAll();          // the MAIN camera still draws everything

	// Every reflection camera is a clone of a main camera, made lazily and cached per camera, so the
	// restriction has to be applied to each one as it appears - a station change makes a new camera.
	if ( ! water.userData.pfaReflectionLayersPatched ) {
		water.userData.pfaReflectionLayersPatched = true;
		const base = water.getReflectionCamera.bind( water );
		water.getReflectionCamera = ( cam ) => { const c = base( cam ); c.layers.set( 0 ); return c; };
	}
	note( all
		? `reflection draw set: EVERY mesh excluded (${out.excluded}); the Reflector draws the sky alone (mobile tier / ?reflset=all)`
		: `reflection draw set reduced: ${out.excluded} mesh(es) excluded (${out.orn} ORN, ${out.backdrop} backdrop), `
			+ `${out.kept} kept (ARCH, ground, water-adjacent ENV, impostors, sky). ?reflset=full restores them.` );
	return out;
}
