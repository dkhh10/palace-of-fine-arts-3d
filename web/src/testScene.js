// Stand-in slice used before export/out/gate0 exists (and afterwards with ?test=1) to verify the
// camera conversion and the display pass without any baked asset:
//   - a 3.5 m wide, 12 m tall column-proxy box centred on the Blender origin (the rotunda floor),
//   - a ground plane at GROUND_Z, a 0.18 grey card facing the hero camera (LUT probe),
//   - metre posts at 10 m spacing along +Y (the lagoon axis) to check scale and the horizon line.
// The 0.18 card is an unlit MeshBasicMaterial so its pixel value is exactly 0.18 * exposure through
// the LUT: that is the number checked in tools/lut_check.mjs.
import * as THREE from 'three';
import { b2t } from './blenderCamera.js';

export const GREY_CARD_NAME = 'TEST_grey_card_018';

export function buildTestScene( scene, { groundZ = - 0.4 } = {} ) {
	const g = new THREE.Group();
	g.name = 'TEST_slice';

	const col = new THREE.Mesh(
		new THREE.CylinderGeometry( 1.75, 1.9, 12, 24 ),
		new THREE.MeshStandardMaterial( { color: 0x9a6a58, roughness: 0.85, metalness: 0 } ) );
	col.position.copy( b2t( 0, 0, 6 ) );
	col.name = 'TEST_column_proxy';
	g.add( col );

	// The ground sits BEHIND the origin only, so the lagoon water plane fills the foreground the way
	// it does at the hero station (the camera stands at Blender +Y 100 m over the water).
	const ground = new THREE.Mesh(
		new THREE.PlaneGeometry( 300, 300 ),
		new THREE.MeshStandardMaterial( { color: 0x6b6f50, roughness: 1 } ) );
	ground.rotation.x = - Math.PI / 2;
	ground.position.copy( b2t( 0, - 130, groundZ ) );
	ground.name = 'TEST_ground';
	g.add( ground );

	// 0.18 grey card, unlit, 6 m wide, 20 m in front of the hero camera, facing it
	const card = new THREE.Mesh(
		new THREE.PlaneGeometry( 6, 4 ),
		new THREE.MeshBasicMaterial( { color: new THREE.Color( 0.18, 0.18, 0.18 ), toneMapped: false } ) );
	card.material.color.setRGB( 0.18, 0.18, 0.18, THREE.LinearSRGBColorSpace );
	card.position.copy( b2t( - 6.0, 78, 4 ) );        // off the camera axis so it never hides the column
	card.lookAt( b2t( - 14.1, 100, 4 ) );
	card.name = GREY_CARD_NAME;
	g.add( card );

	for ( let i = 1; i <= 9; i ++ ) {
		const post = new THREE.Mesh(
			new THREE.BoxGeometry( 0.3, 2, 0.3 ),
			new THREE.MeshStandardMaterial( { color: i % 2 ? 0xdddddd : 0x333333, roughness: 0.9 } ) );
		post.position.copy( b2t( - 4, - i * 10, groundZ + 1 ) );
		post.name = `TEST_post_${i * 10}m`;
		g.add( post );
	}
	scene.add( g );
	return g;
}
