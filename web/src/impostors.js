// Gate 4 item 2: the 127 far trees as octahedral impostors, replacing the grey placeholder quads.
//
// THE CONTRACT IS THE MANIFEST'S, read and never assumed (`manifest.impostors`):
//
//   mapping        octahedral, `grid` x `grid` frames on one `atlas_px` atlas, each frame `frame_px`
//                  with a `gutter_px` border, so `inner_px` is what may be sampled.
//   frame_lookup   d = normalize( camera_pos - billboard_pos ) in BLENDER Z-up (from a three.js dir
//                  with (x, -z, y)); n = d / (|d.x|+|d.y|+|d.z|); if n.z >= 0 { u = n.x; v = n.y }
//                  else { u = (1-|n.y|)*sign(n.x); v = (1-|n.x|)*sign(n.y) }; uv01 = (u,v)*0.5+0.5;
//                  col = uv01.x*(grid-1); row = uv01.y*(grid-1), counted from the BOTTOM.
//   frame_uv       u = (col*frame_px + gutter_px + f.x*inner_px) / atlas_px, v from the bottom
//                  likewise; f clamped to [0,1] and inset by half a texel.
//   encode.albedo  gamma2 on RGB at the prototype's OWN `range` (rgb = t.rgb * t.rgb * range, LINEAR
//                  oetf, NOT sRGB), STRAIGHT (un-premultiplied) alpha in A.
//   placement      s = tree_far[i].height_m / prototypes[p].height_above_base_m; a screen-facing
//                  square of side 2 * radius_m * s centred at trunk_base + (0, 0, centre_z_m * s),
//                  all in BLENDER coordinates, heights measured from the prototype's own z = 0.
//   instance_rotation  IGNORED on purpose: the lighting is baked in world space, so the frame comes
//                  from the world-space view direction. Two instances differ by scale, not silhouette.
//   unlit          the atlas already holds LIT RADIANCE: it goes straight into the linear buffer
//                  before the LUT, with no lightmap, no sun and no environment term.
//
// SO THE NORMAL+DEPTH ATLAS IS NOT LOADED.  The manifest says it is block compressed "on purpose
// while `unlit` holds and nothing samples the normal or the depth", and that shading from it would
// need it repacked lossless (+48 MB over the 16 prototypes).  Loading it to leave it unsampled would
// cost that memory for nothing, so `?impnd=1` is the switch that asks for it and the default is off.
// This is a deliberate reading of the manifest over the brief's "normal+depth for lighting": the
// radiance is already baked, and re-lighting it would double the sun.
//
// BLENDING.  The three frames around the view direction are blended with the barycentric weights of
// the octahedral cell's triangle.  The samples are STRAIGHT alpha, so they are combined the only way
// straight alpha may be: rgb = sum( w * rgb * a ) / sum( w * a ), a = sum( w * a ).  Blending the
// colour without the alpha weight would drag the silhouette's colour in from the transparent gutter.
import * as THREE from 'three';
import { b2t } from './blenderCamera.js';

export const ALPHA_TEST = 0.33;

const vertexShader = /* glsl */`
	attribute vec3 iCentre;          // billboard centre, three-space
	attribute float iSide;           // side of the square, metres
	attribute vec3 iSwitch;          // 6c C2: the tree's crown centre, for the mesh/impostor switch
	attribute float iNear;           // 1 where a MESH exists for this tree and may replace the card
	uniform float pfaMeshDist, pfaFadeBand;
	varying vec2 vQuadUv;
	varying vec3 vDirBlender;        // camera -> billboard, BLENDER Z-up, unnormalised
	varying float vPfaFade;          // 1 = the impostor is the LOD, 0 = the mesh is
	#ifdef PFA_FOG
	varying float vFogDepth;
	#endif
	void main() {
		vQuadUv = uv;
		// The SAME formula and the SAME uniforms as the mesh side (foliage.js), from the SAME crown
		// centre, so the two dissolves are exact complements and no tree is ever drawn twice or not
		// at all.  A tree with no mesh (the 127 far ones today) has iNear = 0 and never fades.
		vPfaFade = ( iNear > 0.5 )
			? smoothstep( pfaMeshDist, pfaMeshDist + pfaFadeBand, distance( cameraPosition, iSwitch ) )
			: 1.0;
		// Screen-facing quad: the camera's right and up in world space, from the view matrix's rows.
		vec3 right = vec3( viewMatrix[ 0 ][ 0 ], viewMatrix[ 1 ][ 0 ], viewMatrix[ 2 ][ 0 ] );
		vec3 up    = vec3( viewMatrix[ 0 ][ 1 ], viewMatrix[ 1 ][ 1 ], viewMatrix[ 2 ][ 1 ] );
		vec3 world = iCentre + ( right * position.x + up * position.y ) * iSide;
		vec3 d = cameraPosition - iCentre;
		vDirBlender = vec3( d.x, - d.z, d.y );         // three -> Blender Z-up
		vec4 mv = viewMatrix * vec4( world, 1.0 );
		#ifdef PFA_FOG
		vFogDepth = length( mv.xyz );          // along the VIEW RAY, as Blender's mist pass measures it
		#endif
		gl_Position = projectionMatrix * mv;
	}
`;

const fragmentShader = /* glsl */`
	uniform sampler2D atlas;
	uniform float range;             // the prototype's own gamma-2 range
	uniform float grid, framePx, innerPx, gutterPx, atlasPx;
	uniform float alphaTest;
	uniform int debugMode;           // 0 off, 1 raw sample, 2 alpha, 3 frame cell, 4 quad uv
	#ifdef PFA_FOG
	uniform vec3 fogColor;
	uniform float fogNear, fogFar, fogCap, fogK, fogIntensity;
	varying float vFogDepth;
	#endif
	varying vec2 vQuadUv;
	varying vec3 vDirBlender;
	varying float vPfaFade;

	// The mesh side's dither, verbatim (foliage.js): a purely spatial hash, so the crossfade is a
	// fixed pattern and a screenshot is byte-identical twice running.
	float pfaHash( vec2 p ) { return fract( 52.9829189 * fract( dot( p, vec2( 0.06711056, 0.00583715 ) ) ) ); }

	// manifest.impostors.frame_uv, with f clamped and sampled at texel centres.
	//
	// THE V FLIP.  The manifest counts the row "from the BOTTOM" and f.y likewise, but the atlases
	// are written KTXorientation: rd (right, DOWN) - measured with ktx info on every one of the 16 -
	// so data row 0 is the TOP.  Without this flip the lookup lands on the mirrored elevation, which
	// is the tree's shaded side: the hero read the far trees as dark blue (raw code 0.25/0.29/0.49)
	// because 49-101 of each atlas's 144 frames are sky-lit back sides, and it was picking those.
	vec2 frameUv( vec2 cell, vec2 f ) {
		vec2 g = clamp( f, 0.0, 1.0 );
		float px = cell.x * framePx + gutterPx + g.x * innerPx;
		float pyFromBottom = cell.y * framePx + gutterPx + g.y * innerPx;
		return vec2( ( px + 0.5 ) / atlasPx, 1.0 - ( pyFromBottom + 0.5 ) / atlasPx );
	}

	vec4 sampleFrame( vec2 cell, vec2 f ) { return texture2D( atlas, frameUv( cell, f ) ); }

	void main() {
		if ( vPfaFade < 0.9995 && pfaHash( gl_FragCoord.xy ) > vPfaFade ) discard;
		// manifest.impostors.frame_lookup, verbatim
		vec3 d = normalize( vDirBlender );
		vec3 n = d / ( abs( d.x ) + abs( d.y ) + abs( d.z ) );
		vec2 o = ( n.z >= 0.0 )
			? vec2( n.x, n.y )
			: vec2( ( 1.0 - abs( n.y ) ) * ( n.x >= 0.0 ? 1.0 : - 1.0 ),
			        ( 1.0 - abs( n.x ) ) * ( n.y >= 0.0 ? 1.0 : - 1.0 ) );
		vec2 uv01 = clamp( o * 0.5 + 0.5, 0.0, 1.0 );
		vec2 g = uv01 * ( grid - 1.0 );
		vec2 gi = floor( g );
		vec2 fr = g - gi;
		gi = min( gi, vec2( grid - 2.0 ) );

		// the three frames around the direction: the cell's triangle, barycentric
		vec2 c0, c1, c2;
		vec3 w;
		if ( fr.x + fr.y < 1.0 ) {
			c0 = gi; c1 = gi + vec2( 1.0, 0.0 ); c2 = gi + vec2( 0.0, 1.0 );
			w = vec3( 1.0 - fr.x - fr.y, fr.x, fr.y );
		} else {
			// Vertices (1,1), (0,1), (1,0).  At (fx,fy) = (0,1) the weight of (0,1) must be 1, so it
			// is 1 - fx, and (1,0) gets 1 - fy.  Having these two swapped leaned the blend on the
			// wrong neighbour by up to a cell off the diagonal and was discontinuous at the cell edge.
			c0 = gi + vec2( 1.0, 1.0 ); c1 = gi + vec2( 0.0, 1.0 ); c2 = gi + vec2( 1.0, 0.0 );
			w = vec3( fr.x + fr.y - 1.0, 1.0 - fr.x, 1.0 - fr.y );
		}

		vec4 s0 = sampleFrame( c0, vQuadUv );
		vec4 s1 = sampleFrame( c1, vQuadUv );
		vec4 s2 = sampleFrame( c2, vQuadUv );

		// STRAIGHT alpha: weight the colour by its own alpha or the gutter bleeds into the silhouette
		float a = w.x * s0.a + w.y * s1.a + w.z * s2.a;
		if ( a < alphaTest ) discard;
		vec3 rgb = ( w.x * s0.a * s0.rgb + w.y * s1.a * s1.rgb + w.z * s2.a * s2.rgb ) / max( a, 1e-4 );

		// manifest.impostors.encode.albedo: gamma2 at the prototype's own range, LINEAR oetf
		vec3 lin = rgb * rgb * range;

		if ( debugMode == 1 ) { gl_FragColor = vec4( s0.rgb, 1.0 ); return; }
		if ( debugMode == 2 ) { gl_FragColor = vec4( vec3( a ), 1.0 ); return; }
		if ( debugMode == 3 ) { gl_FragColor = vec4( c0 / ( grid - 1.0 ), 0.0, 1.0 ); return; }
		if ( debugMode == 4 ) { gl_FragColor = vec4( vQuadUv, 0.0, 1.0 ); return; }

		#ifdef PFA_FOG
		// COMP_golden_hour's airlight, the same form postChain.js patches into three's fog chunk:
		// cap * ( 1 - exp( -k * mist ) ), NOT a power curve.  fogK is the extinction coefficient.
		float t = clamp( ( vFogDepth - fogNear ) / max( fogFar - fogNear, 1e-6 ), 0.0, 1.0 );
		float mist = fogIntensity + ( 1.0 - fogIntensity ) * t;
		lin = mix( lin, fogColor, clamp( fogCap * ( 1.0 - exp( - fogK * mist ) ), 0.0, 1.0 ) );
		#endif

		gl_FragColor = vec4( lin, 1.0 );
	}
`;

/**
 * One InstancedMesh per prototype, built from `manifest.gate3.impostors` and `manifest.trees.far`.
 * @returns {{ group:THREE.Group|null, report:object }}
 */
export function buildImpostors( { impostors, far, near = [], loadTexture, note = () => {}, fog = null,
	normalDepth = false, debug = 0, atlas2k = false, switchUniforms = null } ) {
	const report = { prototypes: 0, instances: 0, nearInstances: 0, drawCalls: 0, skipped: [], bytes: 0,
		unmappedPrototypes: [], missingPrototypes: [], textures: 0, normalDepthLoaded: 0,
		atlas2k: false, atlas2kMissing: [] };
	if ( ! impostors || ! impostors.count ) return { group: null, report };
	far = [ ...( Array.isArray( far ) ? far : [] ), ...( Array.isArray( near ) ? near : [] ) ];
	if ( ! far.length ) return { group: null, report };
	// 6c C2: the 2K variant on desktop.  `variant_2k` re-states the geometry of the atlas (frame,
	// gutter, inner), so it is READ from the manifest exactly as the 1K block is and never scaled by
	// hand; a prototype missing a 2K texture keeps its 1K one AND its 1K geometry.
	const v2k = atlas2k ? impostors.variant2k : null;

	// tree_far[i].prototype joins through prototype_map: 46 of the 127 were exported against an LOD2
	// blob and every impostor is baked from the LOD1 mesh, which is why the map exists.
	const byProto = new Map();
	for ( const t of far ) {
		// `far` is manifest.treesFar: { prototype, id, height, width, base } - the normalised shape,
		// so tree_far's own key names live in manifest.js and nowhere else.
		const key = impostors.prototypeMap[ t.prototype ] || t.prototype;
		const p = impostors.prototypes[ key ];
		if ( ! p ) {
			if ( ! report.missingPrototypes.includes( key ) ) report.missingPrototypes.push( key );
			report.skipped.push( t.id || t.prototype );
			continue;
		}
		if ( ! ( p.heightAboveBase > 0 ) || ! ( p.radius > 0 ) || ! ( p.range > 0 )
			|| ! Array.isArray( t.base ) || ! ( t.height > 0 ) ) {
			report.skipped.push( t.id || t.prototype );
			continue;
		}
		if ( ! byProto.has( key ) ) byProto.set( key, [] );
		byProto.get( key ).push( t );
	}

	const group = new THREE.Group();
	group.name = 'WEB_impostors';
	const geo = new THREE.PlaneGeometry( 1, 1 );      // unit square, expanded in the vertex shader
	const IDENTITY = new THREE.Matrix4();
	const pending = [];

	for ( const [ key, list ] of byProto ) {
		const p = impostors.prototypes[ key ];
		const defines = fog ? { PFA_FOG: '' } : {};
		// 2K only where BOTH the variant geometry and this prototype's 2K texture exist.
		const use2k = !! ( v2k && p.albedo2k );
		if ( atlas2k && ! use2k && ! report.atlas2kMissing.includes( key ) ) report.atlas2kMissing.push( key );
		const geom = use2k ? v2k : impostors;
		const uniforms = {
			atlas: { value: null },
			range: { value: p.range },
			grid: { value: impostors.grid },
			framePx: { value: geom.framePx },
			innerPx: { value: geom.innerPx },
			gutterPx: { value: geom.gutterPx },
			atlasPx: { value: geom.atlasPx },
			alphaTest: { value: ALPHA_TEST },
			debugMode: { value: debug },
			pfaMeshDist: switchUniforms ? switchUniforms.pfaMeshDist : { value: 1e9 },
			pfaFadeBand: switchUniforms ? switchUniforms.pfaFadeBand : { value: 1 },
		};
		if ( fog ) Object.assign( uniforms, {
			fogColor: { value: fog.color }, fogNear: { value: fog.near }, fogFar: { value: fog.far },
			fogCap: { value: fog.cap }, fogK: { value: fog.k }, fogIntensity: { value: fog.intensity || 0 },
		} );
		const mat = new THREE.ShaderMaterial( {
			name: `MAT_WEB_impostor_${key}`,
			vertexShader, fragmentShader, uniforms, defines,
			transparent: false,            // alpha TEST, so they write depth and need no sorting
			depthWrite: true, depthTest: true, side: THREE.DoubleSide,
		} );
		const g = geo.clone();
		const im = new THREE.InstancedMesh( g, mat, list.length );
		im.name = `WEB_impostor_${key}`;
		im.frustumCulled = false;          // the quad is built in the shader; the bbox is not the geometry's
		im.instanceMatrix.setUsage( THREE.StaticDrawUsage );
		const centre = new Float32Array( list.length * 3 );
		const side = new Float32Array( list.length );
		const swtch = new Float32Array( list.length * 3 );
		const nearFlag = new Float32Array( list.length );
		let nearHere = 0;
		list.forEach( ( t, i ) => {
			// placement, in BLENDER coordinates, then converted once
			const s = t.height / p.heightAboveBase;
			const [ bx, by, bz ] = t.base;
			const c = b2t( bx, by, bz + p.centreZ * s );
			centre[ i * 3 ] = c.x; centre[ i * 3 + 1 ] = c.y; centre[ i * 3 + 2 ] = c.z;
			side[ i ] = 2 * p.radius * s;
			// 6c C2: a tree that also has a MESH fades between the two; one that does not is always
			// the impostor.  The switch distance is measured to the CROWN centre the mesh side uses,
			// never to the billboard centre, or the two dissolves would cross at different metres.
			const sw = ( t.near && Array.isArray( t.switchCentre ) ) ? t.switchCentre : null;
			if ( sw ) { swtch[ i * 3 ] = sw[ 0 ]; swtch[ i * 3 + 1 ] = sw[ 1 ]; swtch[ i * 3 + 2 ] = sw[ 2 ]; nearFlag[ i ] = 1; nearHere ++; }
			else { swtch[ i * 3 ] = c.x; swtch[ i * 3 + 1 ] = c.y; swtch[ i * 3 + 2 ] = c.z; }
			im.setMatrixAt( i, IDENTITY );              // identity: the shader does the placing
		} );
		report.nearInstances += nearHere;
		g.setAttribute( 'iCentre', new THREE.InstancedBufferAttribute( centre, 3 ) );
		g.setAttribute( 'iSide', new THREE.InstancedBufferAttribute( side, 1 ) );
		g.setAttribute( 'iSwitch', new THREE.InstancedBufferAttribute( swtch, 3 ) );
		g.setAttribute( 'iNear', new THREE.InstancedBufferAttribute( nearFlag, 1 ) );
		im.userData.pfaImpostor = { prototype: key, instances: list.length, near: nearHere, range: p.range,
			radius_m: p.radius, height_above_base_m: p.heightAboveBase, centre_z_m: p.centreZ, atlas2k: use2k };
		group.add( im );
		report.prototypes ++;
		report.instances += list.length;
		report.drawCalls ++;
		report.bytes += p.bytes || 0;

		if ( use2k ) { report.atlas2k = true; report.bytes += ( p.bytes2k || 0 ) - ( p.bytes || 0 ); }
		pending.push( loadTexture( use2k ? p.albedo2k : p.albedo ).then( ( tex ) => {
			if ( ! tex ) { note( `impostor ${key}: albedo atlas failed to load` ); return; }
			// The atlas holds LINEAR radiance behind a gamma-2 code, not sRGB: the decode is in the
			// shader, so the sampler must not decode anything.
			tex.colorSpace = THREE.NoColorSpace;
			tex.flipY = false;
			tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
			tex.minFilter = THREE.LinearFilter;         // NO mips: a mip would blend across frames
			tex.magFilter = THREE.LinearFilter;
			tex.generateMipmaps = false;
			tex.anisotropy = 1;
			tex.needsUpdate = true;
			mat.uniforms.atlas.value = tex;
			mat.needsUpdate = true;
			report.textures ++;
		} ).catch( ( e ) => note( `impostor ${key}: ${e.message}` ) ) );

		if ( normalDepth && p.normalDepth ) {
			pending.push( loadTexture( p.normalDepth ).then( () => { report.normalDepthLoaded ++; } ).catch( () => {} ) );
		}
	}

	report.promise = Promise.all( pending ).then( () => {
		if ( report.nearInstances ) note( `impostors: ${report.nearInstances} of them are NEAR trees that also have a mesh `
			+ `(6c C2): they dissolve into their mesh inside the switch distance and the mesh dissolves into them beyond it` );
		if ( atlas2k ) note( `impostor atlas: 2K variant on ${report.atlas2k ? report.prototypes - report.atlas2kMissing.length : 0}/${report.prototypes} prototype(s)`
			+ ( report.atlas2kMissing.length ? `; 1K kept on ${report.atlas2kMissing.join( ', ' )} (no albedo_2k in the manifest)` : '' ) );
		note( `impostors: ${report.instances} far tree(s) over ${report.prototypes} prototype(s), `
			+ `${report.drawCalls} draw call(s), ${impostors.grid}x${impostors.grid} octahedral frames `
			+ `at ${impostors.framePx} px on a ${impostors.atlasPx} px atlas, 3-frame barycentric blend, `
			+ `alpha test ${ALPHA_TEST}, unlit (the atlas is baked radiance); ${report.textures}/${report.prototypes} atlas(es) loaded, `
			+ `${( report.bytes / 1048576 ).toFixed( 1 )} MB declared`
			+ ( report.normalDepthLoaded ? `, ${report.normalDepthLoaded} normal+depth atlas(es) loaded (?impnd=1)`
				: ', normal+depth NOT loaded (the manifest says nothing samples it while unlit holds)' ) );
		if ( report.missingPrototypes.length )
			note( `impostors: ${report.missingPrototypes.length} prototype(s) in trees.far have no atlas: ${report.missingPrototypes.join( ', ' )}` );
		if ( report.skipped.length ) note( `impostors: ${report.skipped.length} far tree(s) skipped` );
		return report;
	} );
	return { group, report };
}
