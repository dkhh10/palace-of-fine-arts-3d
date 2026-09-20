// phase8_viewer_r1_review finding 6, the half r3 left open: "**no test pins the new default**"
// (`?detailproj=` fell back to `objxy` in silence before Phase 8c item A made `dominant` the
// default, and `?impcov=`'s default IS pinned by its own test while this one was not).  So:
//
//     node test/detail_proj_test.mjs
//
// Three things, none of which a screenshot can show:
//   1. `dominant` is the DEFAULT that reaches `patchDetailMaterial` when nothing asks for anything,
//      and it is the value the shader define and the material's own userData record carry, so a
//      capture sidecar can never say `dominant` while `objxy` is compiled;
//   2. `objxy` still reaches it when it IS asked for - the A/B lever is real, not a dead switch;
//   3. an unrecognised value falls back to `dominant` AND says so in the boot note, which is the
//      round-1 review 7 rule the rest of the viewer's switches follow.
import * as THREE from 'three';
import { applyDetail, patchDetailMaterial } from '../src/detail.js';

let fails = 0;
const check = ( ok, msg ) => { if ( ! ok ) fails ++; console.log( `${ok ? 'PASS' : 'FAIL'}  ${msg}` ); };

// ---- 1 / 2. the define and the record follow the projection ------------------------------------
const RULE = { set: 's', scale: 1, tileM: 1 };
function patched( projection ) {
	const mat = new THREE.MeshStandardMaterial( { name: 'MAT_x' } );
	patchDetailMaterial( mat, { map: null, roughnessMap: null, normalMap: null }, RULE,
		projection === undefined ? {} : { projection } );
	// the four chunk anchors three's own chain gives it; `once()` throws if any is missing, which is
	// itself the guard that the patch still finds its place in r186.
	const shader = {
		vertexShader: 'void main() {\n#include <project_vertex>\n}',
		fragmentShader: 'void main() {\n#include <map_fragment>\n#include <roughnessmap_fragment>\n'
			+ '#include <normal_fragment_maps>\n}',
		uniforms: {},
	};
	mat.onBeforeCompile( shader, null );
	return { record: mat.userData.pfaDetail.projection, src: shader.fragmentShader,
		key: mat.customProgramCacheKey() };
}
const dom = patched( 'dominant' );
check( dom.record === 'dominant', 'dominant: the material records it' );
check( /#define PFA_DETAIL_PROJ 1/.test( dom.src ), 'dominant: and the shader compiles the dominant-axis plane' );
check( /pfadetail:1:/.test( dom.key ), 'dominant: and the program cache key carries it, so the two never share a program' );
const obj = patched( 'objxy' );
check( obj.record === 'objxy', 'objxy: the material records it' );
check( /#define PFA_DETAIL_PROJ 0/.test( obj.src ), 'objxy: and the shader compiles the manifest plane (the lever is real)' );
check( /pfadetail:0:/.test( obj.key ), 'objxy: and its own cache key' );

// ---- the DEFAULT, which is what r1 finding 6 asked for -----------------------------------------
// applyDetail's own signature default, with nothing passed at all.
const notes = [];
const scene = new THREE.Scene();
const matDef = new THREE.MeshStandardMaterial( { name: 'MAT_concrete_ochre' } );
scene.add( new THREE.Mesh( new THREE.BufferGeometry(), matDef ) );
const DETAIL = {
	sets: { s: { maps: {} } },
	perMaterial: { MAT_concrete_ochre: { set: 's', scale: 1, tileM: 1 } },
	perGroup: {},
};
const rDefault = await applyDetail( { scene, detail: DETAIL, loadTexture: async () => null,
	note: ( m ) => notes.push( m ) } );
check( rDefault.projection === 'dominant',
	`the DEFAULT projection is dominant, with nothing asked for (got ${rDefault.projection})` );
const rObjxy = await applyDetail( { scene: new THREE.Scene(), detail: DETAIL, loadTexture: async () => null,
	note: () => {}, projection: 'objxy' } );
check( rObjxy.projection === 'objxy', '?detailproj=objxy still reaches the report' );

// ---- 3. a typo falls back to the default AND says so --------------------------------------------
for ( const bad of [ 'dominent', 'triplanar', '1', '' ] ) {
	const n = [];
	const r = await applyDetail( { scene: new THREE.Scene(), detail: DETAIL, loadTexture: async () => null,
		note: ( m ) => n.push( m ), projection: bad } );
	check( r.projection === 'dominant', `?detailproj=${bad || '(empty)'}: falls back to dominant` );
	check( n.some( ( m ) => m.includes( `?detailproj=${bad}` ) && m.includes( 'dominant, the default' ) ),
		`?detailproj=${bad || '(empty)'}: and the boot note says which value was not understood` );
}
check( THREE.REVISION >= '186'.slice( 0, 3 ), `three r${THREE.REVISION}` );
console.log( fails ? `\n${fails} FAILED` : '\nall passed' );
process.exit( fails ? 1 : 0 );
