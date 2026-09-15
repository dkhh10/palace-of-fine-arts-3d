// Display transform: exposure multiplier -> 3D LUT (Blender's AgX High Contrast at -2.833 EV),
// applied as the last post pass with three.js tone mapping OFF.
//
// The LUT is baked by export/bake_lut.py from Blender's own OCIO, so it maps SCENE-LINEAR input to
// DISPLAY-REFERRED sRGB output.  The pass therefore writes its result straight to the drawing buffer
// with no further colour-space conversion (a ShaderPass does not include <colorspace_fragment>).
//
// Domain: a .cube may declare DOMAIN_MIN/DOMAIN_MAX; anything outside is clamped.  If the bake uses a
// log shaper (scene-linear values above 1.0 folded into 0..1), set shaper:'log2' with shaperMin/Max in
// stops and shaperPivot (AgX: 0.18), and the pass applies
//     t = (log2(c / pivot) - min_ev) / (max_ev - min_ev)
// to the POST-exposure linear value before the lookup.  Gate 0's LUT is AgX High Contrast at
// min_ev -12.47393, max_ev 4.026069, pivot 0.18, 65^3, with the -2.833 EV exposure applied here.
import * as THREE from 'three';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

export const LUTDisplayShader = {
	name: 'PFALUTDisplayShader',
	uniforms: {
		tDiffuse: { value: null },
		lut: { value: null },
		lutSize: { value: 0 },
		exposure: { value: 1.0 },
		domainMin: { value: new THREE.Vector3( 0, 0, 0 ) },
		domainMax: { value: new THREE.Vector3( 1, 1, 1 ) },
		useShaper: { value: 0 },
		shaperMin: { value: - 10.0 },
		shaperMax: { value: 6.0 },
		shaperPivot: { value: 0.18 },
		lutEnabled: { value: 1 },
		// Diagnostic only (Gate 4 implements the real depth-dependent mist): a constant airlight mix
		// standing in for COMP_golden_hour's haze, applied to the SCENE-LINEAR value before exposure,
		// exactly where Blender's compositor sits relative to the view transform.
		hazeColor: { value: new THREE.Vector3( 5.320881, 3.739, 1.960339 ) },
		hazeStrength: { value: 0.0 },
	},
	vertexShader: /* glsl */`
		varying vec2 vUv;
		void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 ); }
	`,
	fragmentShader: /* glsl */`
		uniform sampler2D tDiffuse;
		uniform sampler3D lut;
		uniform float lutSize, exposure, shaperMin, shaperMax, shaperPivot;
		uniform vec3 domainMin, domainMax;
		uniform int useShaper, lutEnabled;
		uniform vec3 hazeColor;
		uniform float hazeStrength;
		varying vec2 vUv;
		void main() {
			vec4 src = texture2D( tDiffuse, vUv );
			vec3 lin = max( src.rgb, vec3( 0.0 ) );
			if ( hazeStrength > 0.0 ) lin = mix( lin, hazeColor, hazeStrength );
			vec3 c = lin * exposure;
			if ( lutEnabled == 0 ) { gl_FragColor = vec4( pow( c, vec3( 1.0 / 2.2 ) ), src.a ); return; }
			vec3 t;
			if ( useShaper == 1 ) {
				vec3 l = log2( max( c, vec3( 1e-9 ) ) / shaperPivot );   // AgX: EV relative to mid grey
				t = ( l - vec3( shaperMin ) ) / vec3( shaperMax - shaperMin );
			} else {
				t = ( c - domainMin ) / ( domainMax - domainMin );
			}
			t = clamp( t, vec3( 0.0 ), vec3( 1.0 ) );
			// sample at texel centres so the LUT end points are hit exactly
			float px = 1.0 / lutSize;
			vec3 uvw = vec3( 0.5 * px ) + t * ( 1.0 - px );
			gl_FragColor = vec4( texture( lut, uvw ).rgb, src.a );
		}
	`,
};

export class LUTDisplayPass extends ShaderPass {
	constructor( options = {} ) {
		super( LUTDisplayShader );
		this.setLUT( options.lut || null );
		this.uniforms.exposure.value = options.exposure ?? 1.0;
	}
	/** @param {{texture3D:THREE.Data3DTexture,size:number,domainMin?:THREE.Vector3,domainMax?:THREE.Vector3,shaper?:string,shaperMin?:number,shaperMax?:number}|null} lut */
	setLUT( lut ) {
		if ( ! lut ) { this.uniforms.lut.value = null; this.uniforms.lutEnabled.value = 0; return; }
		const tex = lut.texture3D || lut;
		this.uniforms.lut.value = tex;
		this.uniforms.lutSize.value = lut.size || tex.image.width;
		this.uniforms.lutEnabled.value = 1;
		if ( lut.domainMin ) this.uniforms.domainMin.value.copy( lut.domainMin );
		if ( lut.domainMax ) this.uniforms.domainMax.value.copy( lut.domainMax );
		this.uniforms.useShaper.value = lut.shaper === 'log2' ? 1 : 0;
		if ( lut.shaperMin !== undefined ) this.uniforms.shaperMin.value = lut.shaperMin;
		if ( lut.shaperMax !== undefined ) this.uniforms.shaperMax.value = lut.shaperMax;
		if ( lut.shaperPivot !== undefined ) this.uniforms.shaperPivot.value = lut.shaperPivot;
	}
	set exposure( v ) { this.uniforms.exposure.value = v; }
	get exposure() { return this.uniforms.exposure.value; }
}

/** Build a Data3DTexture from a callback f(r,g,b)->[r,g,b] over the unit cube (test LUTs). */
export function makeLUT( size, f ) {
	const data = new Uint8Array( size * size * size * 4 );
	let i = 0;
	for ( let b = 0; b < size; b ++ ) for ( let g = 0; g < size; g ++ ) for ( let r = 0; r < size; r ++ ) {
		const o = f( r / ( size - 1 ), g / ( size - 1 ), b / ( size - 1 ) );
		data[ i ++ ] = Math.round( 255 * Math.min( 1, Math.max( 0, o[ 0 ] ) ) );
		data[ i ++ ] = Math.round( 255 * Math.min( 1, Math.max( 0, o[ 1 ] ) ) );
		data[ i ++ ] = Math.round( 255 * Math.min( 1, Math.max( 0, o[ 2 ] ) ) );
		data[ i ++ ] = 255;
	}
	const tex = new THREE.Data3DTexture( data, size, size, size );
	tex.format = THREE.RGBAFormat;
	tex.type = THREE.UnsignedByteType;
	tex.minFilter = tex.magFilter = THREE.LinearFilter;
	tex.wrapS = tex.wrapT = tex.wrapR = THREE.ClampToEdgeWrapping;
	tex.needsUpdate = true;
	return { texture3D: tex, size };
}
