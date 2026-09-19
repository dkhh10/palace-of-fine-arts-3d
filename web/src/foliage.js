// Phase 6c item C — the leaf shader, the crown-bent normals and the runtime tree LOD.
//
// WHAT THE ROUND-15 FRAME LOOKED LIKE, and why each piece is here (docs/briefs/phase6c_foliage.md):
//   * the near trees read as FLAT CARDS.  Each leaf card carries its own card normal, so a crown is a
//     pile of randomly-facing quads and the whole canopy shades to one average: no light side, no
//     shaded side, no silhouette.  Real canopies shade roughly like a sphere, which is what the
//     CROWN-BENT NORMAL gives: N = normalize( mix( cardNormal, radial, blend ) ), radial being the
//     direction from the crown's centre to the vertex.  `blend` is a look control, `?leafnormal=`.
//   * no light came THROUGH a leaf.  The Phase 5 material is a Mix Shader between a Principled BSDF
//     and a Translucent BSDF at a per-material factor (scripts/mat_build.py `leaf_material`), i.e. a
//     fraction of the leaf's diffuse response is moved to the BACK hemisphere.  The viewer reproduces
//     exactly that mix and nothing more - no forward-scatter phase function, no rim boost - because
//     the acceptance reference is a Cycles frame of that same mix, and anything extra would be light
//     the reference does not have.
//   * the card EDGES were a hard binary cut at the manifest's alphaTest.  `alphaToCoverage` keeps the
//     cutoff and lets three's own alphatest chunk resolve the boundary texel across the MSAA samples
//     (the composer's target and the Reflector's are both `samples: 4`).
//
// THE TRANSLUCENT TERM, derived.  Blender: surface = (1-t)*Principled + t*Translucent(colour = base *
// `translucent`).  Cycles' Translucent BSDF is a Lambert lobe on -N.  three's direct diffuse is
//     dotNL * lightColour * RECIPROCAL_PI * diffuseColor
// so the mix is reproduced by ADDING the back lobe at t and SUBTRACTING t of the front lobe:
//     delta = sunIrr * RECIPROCAL_PI * base * ( t * tint * max( dot( -N, L ), 0 )
//                                             - t * frontSub * max( dot( N, L ), 0 ) )
// `frontSub` is 1 where the front sun diffuse is still in the shader and 0 where it is not.
//
// WHY THE SHRUB / REED CARDS GET NO TRANSLUCENT TERM BY DEFAULT.  Their material is patched by
// `applyInstanceIrradiance` with `specularOnlySun: true`, so they have NO direct sun diffuse at all:
// their diffuse is one baked scene-linear irradiance per PLACEMENT, added with no cosine.  A
// direction-independent irradiance is already the two-sided model that translucency approximates -
// front and back faces of those cards receive the same light today - and the sun is already inside
// that baked value.  Adding a directional back lobe there would be light the bake has counted once
// already, and it would break the round-15 cam02 level (104.5 against the reference's 106.0, 0.99x).
// They do get the crown-bent normals (their specular and the 7 cov == 0 probe cards see it) and the
// soft edges.  `?leaftrn=shrubs` forces the term on for the A/B; the measurement is in web/README.md.
//
// CROWNS ARE FOUND, NOT ASSUMED.  gltfpack dropped every node name and the export MERGED several
// trees into single primitives (MAT_bark_cypress mesh_26 spans 229 m, MAT_leaf_cypress mesh_29 spans
// 230 m), so "one primitive = one tree" is false and a bbox centre would sit in mid-air between
// trees.  Each geometry's vertices are therefore flood-filled on a coarse XZ grid into CONNECTED
// CLUSTERS, one per crown, and every vertex carries its own cluster's centre in `pfaCrown`.  That one
// attribute then serves both jobs: the normal bend at load, and the runtime LOD distance in the
// vertex shader (so a merged mesh switches per TREE, not per primitive, with no per-frame CPU work).
import * as THREE from 'three';

/** Card materials, by the name the export writes (clones keep the name). */
export const LEAF_RE = /^MAT_leaf_[a-z]+$/;
export const CARD_RE = /^MAT_(shrub(_light|_dry)?|reeds)$/;
export const BARK_RE = /^MAT_bark_[a-z]+$/;
export const isFoliage = ( n ) => LEAF_RE.test( n || '' ) || CARD_RE.test( n || '' );
export const isTreeMat = ( n ) => isFoliage( n ) || BARK_RE.test( n || '' );

/**
 * The Phase 5 constants, read off `scripts/mat_build.py` (`leaf_material(...)` calls, lines 1738-1757):
 * `trn` is the Mix Shader factor and `tint` the multiplier on the base colour that feeds the
 * Translucent BSDF.  In Blender the factor is further modulated per texel by the `*_trn` mask mapped
 * 0.05..0.85 -> 0.35..1.55; that map is export item D and is NOT shipped yet, so the constant stands
 * alone here (mean of the map ~ 1) and this table is replaced by the mask when it lands.
 */
export const PHASE5_LEAF = {
	MAT_leaf_cypress:    { trn: 0.25, tint: [ 0.90, 1.10, 0.50 ] },
	MAT_leaf_pine:       { trn: 0.18, tint: [ 0.70, 0.95, 0.50 ] },
	MAT_leaf_eucalyptus: { trn: 0.30, tint: [ 0.80, 1.00, 0.50 ] },
	MAT_leaf_broadleaf:  { trn: 0.35, tint: [ 0.80, 1.20, 0.40 ] },
	MAT_shrub:           { trn: 0.34, tint: [ 0.85, 1.15, 0.60 ] },
	MAT_shrub_light:     { trn: 0.40, tint: [ 0.90, 1.10, 0.70 ] },
	MAT_shrub_dry:       { trn: 0.22, tint: [ 1.05, 0.95, 0.50 ] },
	MAT_reeds:           { trn: 0.45, tint: [ 0.95, 1.05, 0.60 ] },
};

/** species token -> the impostor prototypes that may stand in for it (C2, near trees only). */
const SPECIES_OF = { MAT_leaf_cypress: 'cypress', MAT_leaf_pine: 'pine',
	MAT_leaf_eucalyptus: 'eucalyptus', MAT_leaf_broadleaf: 'broadleaf' };

const CLUSTER_CELL = 6.0;          // m, the flood-fill grid; > the gap inside one crown, < the gap between two
const PAIR_MAX_M = 9.0;            // m, how far a trunk cluster may be from its crown
const MIN_HALF_M = 0.25;           // m, the smallest half-extent an ellipsoid normalisation may use

/**
 * 6c ROUND 3 — THE CROWN INTERIOR (QA 16 open 2: "the crowns have no interior", cam02 centre/edge
 * 0.504 against the reference's 0.364, cam05 range/mean 1.26 against 1.77, every viewer crown at
 * 1.6x-4.5x the reference's p10).
 *
 * A crown in the viewer is lit ALL THE WAY THROUGH, and there are three reasons, each with its own
 * lever here:
 *   1. the crown-bent normal at `blend` turns the whole canopy into a sphere lit from one side - a
 *      balloon, exactly as the tiles read.  The bend is what gives the SILHOUETTE its roundness, so
 *      it is not removed but GATED by the vertex's own radius: full at the rim, none in the middle
 *      (`normalGate`, `?leafgate=`), where a card's own normal is the honest one;
 *   2. the interior leaves take the same irradiance as the rim - the near trees' COLOR_0 bake and
 *      the far meshes' vertex AO both carry some of this, but at the LOD the viewer draws neither is
 *      deep enough.  `pfaCrownD.x` is the vertex's depth into its own crown (1 at the centre, 0 at
 *      the box face, ellipsoid-normalised so a tall crown is not mis-measured), and it attenuates
 *      irradiance / iblIrradiance / radiance per fragment;
 *   3. the Phase 5 translucent back lobe is the FULL unoccluded sun on every leaf, interior ones
 *      included.  It is kept at the rim (that is what makes an edge leaf glow in the reference) and
 *      attenuated inside by the same factor, at `trn` of it.
 * `gain` multiplies the whole factor back up so the box LEVEL can be held inside 0.9-1.1x while the
 * contrast moves; `low` darkens the bottom of a cluster (`pfaCrownD.y`), which is what the shrub and
 * reed CARD clusters want and a tree crown does not.
 */
/**
 * PHASE 7 ITEM B — `floor`, the smallest fraction of its own unoccluded light a foliage fragment may
 * keep.  The three terms above stack multiplicatively on the same fragment (depth into the crown,
 * depth below its top, and the sun's path through it), and at the deep end they reached
 * ( 1 - 0.30 - 0.50 ) * 1.05 = 0.21 of the light - darker INSIDE than the Cycles reference, which is
 * QA 17 residual 2: the hero crown's p10 at 0.57x of the reference's, its centre/edge moving away
 * from it, and near-black blotches at 100 % where the terms coincide.  A floor bounds the product
 * without touching the shape of any one term, so the interior/rim read QA 17 credited (cam02
 * centre/edge 0.393 against the reference's 0.364) is kept and only its DEPTH is limited.
 * MEASURED at the stations: all three of QA 17's crown boxes are ATLAS crowns, so a mesh-side floor
 * moves 0.005-0.012 % of the pixels there (cam01/02/05, MAE 0.0004-0.0012 / 255).  It is set to the
 * same 0.35 the atlas side adopted, because the same stack is what a crown shows at the 3 m walk-in
 * and in the mobile close orbit, and it is bounded there by the same rule rather than by a second
 * number.  The shrub / reed CARD clusters keep floor 0: their level is QA 17's one CLOSED foliage
 * item (frame-normalised 0.91-1.47x of the reference) and a floor would only push it further up.
 * `?crownint=str,low,gamma,gain,trn,sun,floor`, `?cardint=` the same.
 */
export const CROWN_INTERIOR = { str: 0.30, low: 0.0, gamma: 1.0, gain: 1.05, trn: 0.85, sun: 0.50, floor: 0.35 };
export const CARD_INTERIOR = { str: 0.20, low: 0.30, gamma: 1.0, gain: 1.0, trn: 1.0, sun: 0.30, floor: 0.0 };
/** How much of the radius the crown-bend is faded in over: 0 = bend everywhere (round-16b). */
export const NORMAL_GATE = 0.45;
/** LOD bias on the cut-out fetch: the shrub / reed cards, then the tree leaf cards (?foliagebias=). */
// MEASURED (6c round 3): 0.8 on the cards drops the hard-edge share at four of the five shrub boxes
// (02 reed clump 6.22 -> 5.80, 02 shore 9.31 -> 8.92, 05 shore 9.38 -> 9.09, 01 shore 7.15 -> 7.17
// flat) with no visible softening at station 3's 8 m in the 1:1 tile.  1.5 buys about twice as much
// and starts to mush the card silhouettes, so it is left as the switch, not the default.  The leaf
// cards keep 0: the tree crowns' edges are not what QA measured.
/**
 * The environment lobe's scale on the LOD2 shrub / reed cards (?cardenv=), and the same number is
 * `loadShrubLod1`'s default for the LOD1 meshes (?shrubenv=), so crossing the LOD distance cannot
 * change a shrub's level.  SWEPT (6c round 3, stations 1, 2, 3, 5): at 1.0 the seven QA shrub boxes
 * read 1.52 / 1.21 / 1.37 / 1.38 / 1.24 / 0.92 / 2.07x the reference, at 0.3 they read
 * 1.36 / 1.10 / 1.18 / 1.14 / 1.02 / 0.88 / 1.53x, and at 0 two of them fall through to 0.82-0.84x.
 * Hard-edge share falls with it (02 reed clump 5.80 -> 2.07 % against the reference's 1.57).
 */
export const CARD_ENV = 0.3;
export const CARD_MIP_BIAS = 0.8;
export const LEAF_MIP_BIAS = 0.0;

/**
 * PHASE 8a — THE SHRUB / REED CARD RELIGHT (`?cardsun=`).
 *
 * What it changes.  The cards carry no direct sun diffuse at all (`specularOnlySun`) and get instead
 * ONE baked scene-linear irradiance per PLACEMENT, added with no cosine (materials.js,
 * `irradiance += vPfaInstIrr * scale`).  Every texel of every card in a clump therefore stands in the
 * same warm light, front and back, sunward side and lee: the measured mean over the 1 379 placements
 * is [ 1.83 1.42 1.36 ], G/R 0.774, and an albedo of hue 100 deg renders at hue 54 under it
 * (docs/briefs/phase8a_rescope_analysis.md §2).  The Cycles reference of the same materials is dark
 * green bushes with gold sunlit rims; the same green is inside the SAME bake, in the shade our cards
 * never get.  This term splits that one number into a sun share and a sky share and gives the sun
 * share a direction, without adding any light.
 *
 * The maths, per fragment (E = the placement's flat baked irradiance, the vec3 above):
 *
 *     s^   = pfaSunIrr / luma( pfaSunIrr )        the MANIFEST sun's chroma at unit luma
 *     s^   = mix( 1, s^, chroma )                 `chroma` dials it toward neutral; luma stays 1
 *     f    = min( share, 0.98 / max( s^ ) )       the sun's share of E's level; clamped so the sky
 *                                                 share ( 1 - f*s^ ) stays >= 0.02 in every channel
 *     nl   = clamp( ( dot( N, L ) + wrap ) / ( 1 + wrap ), 0, 1 )      N = the shading normal
 *     clump= 1 - shade * clamp( vPfaCrownD.z, 0, 1 )                   the sun's path through the
 *                                                 cluster sphere, the same vertex term the interior
 *                                                 occlusion uses: 0 on the sunward surface, 1 deep -
 *                                                 so inner and lee cards fall back to the sky share
 *     g    = clamp( nl * clump / mean, 0, cap )   the sun term RELATIVE to its own scene mean
 *     E'   = E * max( 0, 1 + amt * f * s^ * ( g - 1 ) )
 *
 * Three properties, and they are the reason for the shape:
 *   1. `amt = 0` is not patched in at all, so `?cardsun=0` is today's program and today's pixels,
 *      byte for byte (the test asserts the un-patched source).
 *   2. `g = 1` - a card lit exactly at the scene mean - returns E EXACTLY, in every channel.  The
 *      term is a REDISTRIBUTION around the mean, not a gain: the level (QA 17's one closed shrub
 *      item) is held by construction wherever the box's mean g is 1, and the level error of a box is
 *      exactly `amt * f * s^ * ( mean_box( g ) - 1 )`.  `mean` is the one number that has to be
 *      measured against the captures; it is swept in stage 2 and the level is checked at the eight
 *      QA-17 boxes.
 *   3. The shade chroma is DERIVED, not invented: with the manifest's sun [ 1.0 0.607 0.0 ] the sun
 *      share is s^ = [ 1.546 0.939 0.0 ] at chroma 1 and the sky share it leaves is 1 - f*s^, i.e.
 *      blue-green - the direction of the bake's own darkest decile ([ 0.68 1.02 2.05 ], §2).
 *      `chroma` 0.65 lands that ratio near the measured one; 1.0 is the raw manifest sun.
 *
 * `?cardsun=amt[,share[,wrap[,shade[,mean[,chroma[,cap]]]]]]`, `?cardsun=0` / `off` = today.
 * The default `amt` is 0 until the stage-2 captures adopt a value (this comment is the record).
 */
export const CARD_SUN = { amt: 0, share: 0.55, wrap: 0.5, shade: 0.6, mean: 0.45, chroma: 0.65, cap: 2.5 };
export const CARD_SUN_KEYS = [ 'amt', 'share', 'wrap', 'shade', 'mean', 'chroma', 'cap' ];

/** `"str[,low[,gamma[,gain[,trn[,sun[,floor]]]]]]"` (or an object) over a default, all clamped. */
export function parseInterior( v, dflt ) {
	const d = { ...dflt };
	if ( v === null || v === undefined || v === '' ) return d;
	if ( typeof v === 'object' ) Object.assign( d, v );
	else {
		const s = String( v ).trim().toLowerCase();
		if ( s === '0' || s === 'off' ) return { str: 0, low: 0, gamma: 1, gain: 1, trn: 0, sun: 0, floor: 0 };
		if ( s === '1' || s === 'on' ) return { ...dflt };
		const p = s.split( ',' ).map( ( x ) => parseFloat( x ) );
		const keys = [ 'str', 'low', 'gamma', 'gain', 'trn', 'sun', 'floor' ];
		for ( let i = 0; i < keys.length; i ++ ) if ( Number.isFinite( p[ i ] ) ) d[ keys[ i ] ] = p[ i ];
	}
	const cl = ( x, lo, hi, f ) => ( Number.isFinite( x ) ? Math.min( Math.max( x, lo ), hi ) : f );
	return { str: cl( d.str, 0, 1, dflt.str ), low: cl( d.low, 0, 1, dflt.low ),
		gamma: cl( d.gamma, 0.1, 8, dflt.gamma ), gain: cl( d.gain, 0.25, 4, dflt.gain ),
		trn: cl( d.trn, 0, 1, dflt.trn ), sun: cl( d.sun, 0, 1, dflt.sun ),
		floor: cl( d.floor, 0, 1, dflt.floor === undefined ? 0 : dflt.floor ) };
}

/** True where the interior term would do nothing at all (so the program is left unpatched). */
const interiorOff = ( it ) => ! it
	|| ( it.str <= 0 && it.low <= 0 && it.sun <= 0 && Math.abs( it.gain - 1 ) < 1e-6 );

/** `"amt[,share[,wrap[,shade[,mean[,chroma[,cap]]]]]]"` (or an object) over CARD_SUN, all clamped. */
export function parseCardSun( v, dflt = CARD_SUN ) {
	const d = { ...dflt };
	if ( v === null || v === undefined || v === '' ) return d;
	if ( typeof v === 'object' ) Object.assign( d, v );
	else if ( typeof v === 'number' ) d.amt = v;
	else {
		const s = String( v ).trim().toLowerCase();
		if ( s === 'off' ) return { ...dflt, amt: 0 };
		if ( s === 'on' ) return { ...dflt, amt: dflt.amt > 0 ? dflt.amt : 1 };
		const p = s.split( ',' ).map( ( x ) => parseFloat( x ) );
		for ( let i = 0; i < CARD_SUN_KEYS.length; i ++ )
			if ( Number.isFinite( p[ i ] ) ) d[ CARD_SUN_KEYS[ i ] ] = p[ i ];
	}
	// Round-1 review 3 again: a bad switch falls back to its DEFAULT, never to NaN.
	const cl = ( x, lo, hi, f ) => ( Number.isFinite( x ) ? Math.min( Math.max( x, lo ), hi ) : f );
	return { amt: cl( d.amt, 0, 1, dflt.amt ), share: cl( d.share, 0, 0.98, dflt.share ),
		wrap: cl( d.wrap, 0, 4, dflt.wrap ), shade: cl( d.shade, 0, 1, dflt.shade ),
		mean: cl( d.mean, 0.02, 4, dflt.mean ), chroma: cl( d.chroma, 0, 1, dflt.chroma ),
		cap: cl( d.cap, 1, 8, dflt.cap ) };
}

/** True where the relight would do nothing at all (so the program is left BYTE-IDENTICAL to today). */
export const cardSunOff = ( cs ) => ! cs || ! ( cs.amt > 0 );

/** The per-placement irradiance scale `patchBakedMaterial` put on this material, or null. */
export const instIrrOf = ( mat ) => ( mat && mat.userData && mat.userData.pfaPatched
	&& mat.userData.pfaPatched.instIrr !== undefined ? mat.userData.pfaPatched.instIrr : null );

/**
 * The JS mirror of the GLSL above, and the SPEC the shader is tested against: the per-fragment
 * factor on the flat baked irradiance.  `sunColor` is the manifest sun ([r,g,b], the pfaSunIrr
 * uniform), `nDotL` the cosine on the shading normal and `clumpDepth` the vPfaCrownD.z sun path.
 * @returns {number[]} the rgb factor; [1,1,1] is today's look.
 */
export function cardSunFactor( cs, sunColor, nDotL, clumpDepth = 0 ) {
	const c = parseCardSun( cs );
	const lum = 0.2126 * sunColor[ 0 ] + 0.7152 * sunColor[ 1 ] + 0.0722 * sunColor[ 2 ];
	let sh = lum > 1e-6 ? sunColor.map( ( x ) => x / lum ) : [ 1, 1, 1 ];
	sh = sh.map( ( x ) => 1 + c.chroma * ( x - 1 ) );
	const f = Math.min( c.share, 0.98 / Math.max( sh[ 0 ], sh[ 1 ], sh[ 2 ], 1e-6 ) );
	const nl = Math.min( Math.max( ( nDotL + c.wrap ) / ( 1 + c.wrap ), 0 ), 1 );
	const clump = 1 - c.shade * Math.min( Math.max( clumpDepth, 0 ), 1 );
	const g = Math.min( Math.max( nl * clump / Math.max( c.mean, 1e-3 ), 0 ), c.cap );
	return sh.map( ( x ) => Math.max( 0, 1 + c.amt * f * x * ( g - 1 ) ) );
}

/**
 * `?cardsun=` read from the page, ONCE.  `applyFoliage` is called again for every lazily loaded glb
 * (env_trees, env_shrubs) from `foliageLazy`, which does not carry this flag in its option bag, and
 * a shrub card must not be relit differently because of which file it arrived in.  An explicit
 * `o.cardSun` always wins (the tests pass one).
 */
let cardSunQuery;
export function cardSunFromLocation() {
	if ( cardSunQuery !== undefined ) return cardSunQuery;
	cardSunQuery = null;
	try {
		if ( typeof window !== 'undefined' && window.location )
			cardSunQuery = new URLSearchParams( window.location.search ).get( 'cardsun' );
	} catch ( e ) { cardSunQuery = null; }
	return cardSunQuery;
}

/** Shader-patch failures, surfaced instead of thrown: onBeforeCompile runs at the first render. */
export const shaderErrors = [];
export function recordShaderError( where, e ) {
	const msg = `${where}: ${e && e.message ? e.message : e}`;
	shaderErrors.push( msg );
	if ( typeof window !== 'undefined' ) {
		window.__pfaError = ( window.__pfaError ? `${window.__pfaError}\n` : '' ) + `foliage shader patch — ${msg}`;
	}
	return msg;
}

function once( src, needle, replacement, what ) {
	const n = src.split( needle ).length - 1;
	if ( n !== 1 ) throw new Error( `foliage patch "${what}": expected 1 occurrence, found ${n}` );
	return src.replace( needle, replacement );
}

/** `once` for a pattern: the replacement is a function of the single match. */
function onceRe( src, re, make, what ) {
	const m = src.match( new RegExp( re.source, re.flags.includes( 'g' ) ? re.flags : re.flags + 'g' ) );
	const n = m ? m.length : 0;
	if ( n !== 1 ) throw new Error( `foliage patch "${what}": expected 1 occurrence, found ${n}` );
	return src.replace( re, ( ...args ) => make( ...args ) );
}

// ---------------------------------------------------------------- crown clustering

/**
 * Flood-fill a geometry's vertices into connected crowns on a CLUSTER_CELL grid in object-space XZ.
 * @returns {{ ids:Int32Array, centres:Float32Array, boxes:THREE.Box3[], count:number }}
 */
export function clusterCrowns( geometry, cell = CLUSTER_CELL ) {
	const pos = geometry.getAttribute( 'position' );
	const n = pos.count;
	const cells = new Map();                    // "i,k" -> cell index
	const cellOf = new Int32Array( n );
	const keys = [];
	for ( let v = 0; v < n; v ++ ) {
		const i = Math.floor( pos.getX( v ) / cell ), k = Math.floor( pos.getZ( v ) / cell );
		const key = `${i},${k}`;
		let c = cells.get( key );
		if ( c === undefined ) { c = keys.length; cells.set( key, c ); keys.push( [ i, k ] ); }
		cellOf[ v ] = c;
	}
	// 8-neighbour flood fill over the occupied cells
	const comp = new Int32Array( keys.length ).fill( - 1 );
	let count = 0;
	for ( let c = 0; c < keys.length; c ++ ) {
		if ( comp[ c ] >= 0 ) continue;
		const id = count ++;
		const stack = [ c ];
		comp[ c ] = id;
		while ( stack.length ) {
			const [ i, k ] = keys[ stack.pop() ];
			for ( let di = - 1; di <= 1; di ++ ) for ( let dk = - 1; dk <= 1; dk ++ ) {
				if ( ! di && ! dk ) continue;
				const nb = cells.get( `${i + di},${k + dk}` );
				if ( nb === undefined || comp[ nb ] >= 0 ) continue;
				comp[ nb ] = id; stack.push( nb );
			}
		}
	}
	const boxes = []; for ( let i = 0; i < count; i ++ ) boxes.push( new THREE.Box3() );
	const ids = new Int32Array( n );
	const v3 = new THREE.Vector3();
	for ( let v = 0; v < n; v ++ ) {
		const id = comp[ cellOf[ v ] ];
		ids[ v ] = id;
		boxes[ id ].expandByPoint( v3.set( pos.getX( v ), pos.getY( v ), pos.getZ( v ) ) );
	}
	const centres = new Float32Array( count * 3 );
	for ( let i = 0; i < count; i ++ ) {
		boxes[ i ].getCenter( v3 );
		centres[ i * 3 ] = v3.x; centres[ i * 3 + 1 ] = v3.y; centres[ i * 3 + 2 ] = v3.z;
	}
	// The mean of COLOR_0 per cluster, RAW (still gamma-2 coded).  On the near trees COLOR_0 is the
	// BAKED IRRADIANCE at the vertex (lightmaps.vertex_irradiance), so this is the one measurement of
	// "what light does this tree actually stand in" the viewer already owns - the impostor
	// modulation's E_placement until the bake ships the far trees' own values.
	const col = geometry.getAttribute( 'color' );
	let colourMean = null;
	if ( col && col.itemSize >= 3 ) {
		const sum = new Float64Array( count * 3 ), nv = new Float64Array( count );
		// The encode is gamma-2 (v = c*c*range), so the mean is taken on the DECODED value: the mean
		// of c and the mean of c*c are not the same number and only the second is an irradiance.
		for ( let v = 0; v < n; v ++ ) {
			const id = ids[ v ], x = col.getX( v ), y = col.getY( v ), z = col.getZ( v );
			sum[ id * 3 ] += x * x; sum[ id * 3 + 1 ] += y * y; sum[ id * 3 + 2 ] += z * z;
			nv[ id ] ++;
		}
		colourMean = new Float32Array( count * 3 );
		for ( let i = 0; i < count; i ++ ) for ( let k = 0; k < 3; k ++ )
			colourMean[ i * 3 + k ] = nv[ i ] ? sum[ i * 3 + k ] / nv[ i ] : 0;
	}
	return { ids, centres, boxes, count, colourMean };
}

/**
 * Write `pfaCrown` (the vertex's own crown centre, object space) and, for foliage geometry, replace
 * the normals with the crown-bent ones.  Idempotent per geometry.
 */
function prepareGeometry( geo, bend, cache, gate = 0 ) {
	const hit = cache.get( geo.uuid );
	if ( hit ) return hit;
	const cl = clusterCrowns( geo );
	const pos = geo.getAttribute( 'position' );
	const n = pos.count;
	const crown = new Float32Array( n * 3 );
	for ( let v = 0; v < n; v ++ ) {
		const c = cl.ids[ v ] * 3;
		crown[ v * 3 ] = cl.centres[ c ]; crown[ v * 3 + 1 ] = cl.centres[ c + 1 ]; crown[ v * 3 + 2 ] = cl.centres[ c + 2 ];
	}
	geo.setAttribute( 'pfaCrown', new THREE.BufferAttribute( crown, 3 ) );

	// 6c round 3 — `pfaCrownD` = (depth into the crown, depth below its top), both 0..1, one byte
	// each.  The radius is normalised per AXIS against the cluster's own half-extent, so a 3 m wide
	// 12 m tall cypress and a 9 m broadleaf both read 1 at the centre and 0 at their own silhouette;
	// a single spherical radius would have called the whole cypress "interior".
	const half = new Float32Array( cl.count * 3 ), ytop = new Float32Array( cl.count ), yspan = new Float32Array( cl.count );
	for ( let i = 0; i < cl.count; i ++ ) {
		const b = cl.boxes[ i ];
		half[ i * 3 ] = Math.max( ( b.max.x - b.min.x ) * 0.5, MIN_HALF_M );
		half[ i * 3 + 1 ] = Math.max( ( b.max.y - b.min.y ) * 0.5, MIN_HALF_M );
		half[ i * 3 + 2 ] = Math.max( ( b.max.z - b.min.z ) * 0.5, MIN_HALF_M );
		ytop[ i ] = b.max.y;
		yspan[ i ] = Math.max( b.max.y - b.min.y, MIN_HALF_M );
	}
	const depth = new Uint8Array( n * 2 );
	const rNorm = new Float32Array( n );
	for ( let v = 0; v < n; v ++ ) {
		const id = cl.ids[ v ], c = id * 3;
		const dx = ( pos.getX( v ) - crown[ v * 3 ] ) / half[ c ];
		const dy = ( pos.getY( v ) - crown[ v * 3 + 1 ] ) / half[ c + 1 ];
		const dz = ( pos.getZ( v ) - crown[ v * 3 + 2 ] ) / half[ c + 2 ];
		// A BOX norm, not a Euclidean one.  Measured (r3a): with sqrt(dx^2+dy^2+dz^2) almost every
		// leaf reads r ~ 1 - a card in the middle of the canopy but off-centre on one axis is already
		// "at the silhouette" - so the depth attribute was ~0 nearly everywhere and the term moved
		// cam02's centre/edge by 0.03.  max(|dx|,|dy|,|dz|) is 1 on the cluster's own box face and
		// falls linearly to 0 at its centre, which is the distribution the canopy actually has.
		const r = Math.max( Math.abs( dx ), Math.abs( dy ), Math.abs( dz ) );
		rNorm[ v ] = r;
		const lower = Math.min( Math.max( ( ytop[ id ] - pos.getY( v ) ) / yspan[ id ], 0 ), 1 );
		depth[ v * 2 ] = Math.round( Math.min( Math.max( 1 - r, 0 ), 1 ) * 255 );
		depth[ v * 2 + 1 ] = Math.round( lower * 255 );
	}
	geo.setAttribute( 'pfaCrownD', new THREE.BufferAttribute( depth, 2, true ) );
	let dsum = 0;
	for ( let v = 0; v < n; v ++ ) dsum += depth[ v * 2 ];
	cl.depthMean = n ? dsum / n / 255 : 0;

	if ( bend > 0 ) {
		const nrm = geo.getAttribute( 'normal' );
		const out = new Float32Array( n * 3 );
		const a = new THREE.Vector3(), r = new THREE.Vector3();
		// The bend is what rounds the SILHOUETTE, and it is also what flattened the inside: a vertex
		// deep in the canopy pointed at the crown's own outside and took the sky like a rim leaf.
		// `gate` fades the bend in over the outer shell only (smoothstep(gate, 1, rNorm)), so the
		// silhouette keeps its sphere and the interior keeps its card normals (?leafgate=0 = round 16b).
		const g = Math.min( Math.max( gate, 0 ), 0.999 );
		for ( let v = 0; v < n; v ++ ) {
			a.set( nrm.getX( v ), nrm.getY( v ), nrm.getZ( v ) ).normalize();
			r.set( pos.getX( v ) - crown[ v * 3 ], pos.getY( v ) - crown[ v * 3 + 1 ], pos.getZ( v ) - crown[ v * 3 + 2 ] );
			let b = bend;
			if ( g > 0 ) {
				const t = Math.min( Math.max( ( rNorm[ v ] - g ) / ( 1 - g ), 0 ), 1 );
				b = bend * t * t * ( 3 - 2 * t );
			}
			// A vertex AT the centre has no radial direction: it keeps its card normal.
			if ( b > 0 && r.lengthSq() > 1e-8 ) { r.normalize(); a.lerp( r, b ); if ( a.lengthSq() < 1e-8 ) a.copy( r ); a.normalize(); }
			out[ v * 3 ] = a.x; out[ v * 3 + 1 ] = a.y; out[ v * 3 + 2 ] = a.z;
		}
		geo.setAttribute( 'normal', new THREE.BufferAttribute( out, 3 ) );
	}
	cache.set( geo.uuid, cl );
	return cl;
}

// ---------------------------------------------------------------- the shader patch

const HASH_GLSL = /* glsl */`
	// Interleaved gradient noise: a purely SPATIAL hash, so the LOD dissolve is a fixed dither
	// pattern and a screenshot of the same frame is byte-identical twice running.
	float pfaHash( vec2 p ) { return fract( 52.9829189 * fract( dot( p, vec2( 0.06711056, 0.00583715 ) ) ) ); }
`;

/**
 * Patch one foliage / bark MeshStandardMaterial: the LOD dissolve (all tree materials) and the
 * translucent mix (materials with a Phase 5 constant and `frontSub` resolved by the caller).
 */
function patchFoliageMaterial( mat, { shared, trn, tint, frontSub, fade, dist, band, sign = 1,
	trnMap = null, switchMask = false, interior = null, mipBias = 0, cardSun = null } ) {
	if ( mat.userData.pfaFoliage ) return false;
	const it = interiorOff( interior ) ? null : interior;
	// PHASE 8a: `null` where the relight is off, and then the program is NOT patched at all - that is
	// what makes `?cardsun=0` byte-identical to today rather than merely numerically equal.
	const cs = cardSunOff( cardSun ) ? null : cardSun;
	const bias = Number.isFinite( mipBias ) && mipBias > 0 ? Math.min( mipBias, 4 ) : 0;
	const u = {
		pfaMipBias: { value: bias },
		pfaInterior: { value: new THREE.Vector4( it ? it.str : 0, it ? it.low : 0,
			it ? it.gamma : 1, it ? it.gain : 1 ) },
		// (the translucent lobe's share of the occlusion, the sun-path term's strength, Phase 7's floor)
		pfaInteriorB: { value: new THREE.Vector3( it ? it.trn : 0, it ? it.sun : 0,
			it ? ( it.floor || 0 ) : 0 ) },
		pfaTrnFac: { value: trn },
		// 6c round 2: export item D's per-texel translucency FACTOR (materials.foliage), which already
		// includes the Phase 5 constant - `pfaTrnFac` then carries only the ?leaftrn scale.
		pfaTrnMap: { value: trnMap },
		pfaTrnTint: { value: new THREE.Vector3( ...tint ) },
		pfaFrontSub: { value: frontSub },
		// Per MATERIAL, not shared: the trees switch at `treeMeshDist` and the shrub/reed cards at
		// `shrubLodDist`, and a LOD2 set is the same switch with the sign flipped.
		pfaSwitchDist: { value: Number.isFinite( dist ) ? dist : 1e9 },
		pfaSwitchBand: { value: Math.max( band, 1e-3 ) },
		pfaSwitchSign: { value: sign },
		// PHASE 8a — the card relight (see CARD_SUN).  amt / share / wrap / shade, then mean / chroma / cap.
		pfaCardSun: { value: new THREE.Vector4( cs ? cs.amt : 0, cs ? cs.share : 0,
			cs ? cs.wrap : 0, cs ? cs.shade : 0 ) },
		pfaCardSunB: { value: new THREE.Vector3( cs ? cs.mean : 1, cs ? cs.chroma : 0, cs ? cs.cap : 1 ) },
	};
	mat.userData.pfaFoliage = { trn, tint, frontSub, fade, dist, band, sign, trnMap: !! trnMap, switchMask,
		interior: it, mipBias: bias, cardSun: cs, uniforms: u };
	const prev = mat.onBeforeCompile;
	mat.onBeforeCompile = function ( shader, renderer ) {
		if ( prev ) prev.call( this, shader, renderer );
		// The patch below runs at the FIRST RENDER of this material.  A throw here takes the frame
		// with it and the page never becomes ready, so a failed patch is recorded on __pfaError and
		// the material simply compiles unpatched - visible, reported, not fatal (round-1 review 9).
		try {
		Object.assign( shader.uniforms, u, shared.uniforms );
		if ( fade ) {
			shader.vertexShader = once( shader.vertexShader, '#include <common>',
				'#include <common>\nattribute vec3 pfaCrown;\nuniform float pfaSwitchDist;\nuniform float pfaSwitchBand;\n'
				+ 'uniform float pfaSwitchSign;\nvarying float vPfaFade;'
				+ ( switchMask ? '\nattribute float pfaSwitchOn;' : '' ), 'fade attributes (vertex)' );
			shader.vertexShader = once( shader.vertexShader, '#include <worldpos_vertex>',
				'#include <worldpos_vertex>\n\t{\n\t\tvec4 pfaC = vec4( pfaCrown, 1.0 );\n'
				+ '\t\t#ifdef USE_INSTANCING\n\t\tpfaC = instanceMatrix * pfaC;\n\t\t#endif\n'
				+ '\t\tvec3 pfaCw = ( modelMatrix * pfaC ).xyz;\n'
				+ '\t\tfloat pfaT = smoothstep( pfaSwitchDist, pfaSwitchDist + pfaSwitchBand, distance( cameraPosition, pfaCw ) );\n'
				+ '\t\tvPfaFade = ( pfaSwitchSign > 0.0 ) ? 1.0 - pfaT : pfaT;\n'
				// 6c round 2: three of the 28 shrub/reed meshes have no LOD1 (manifest shrubs.lod1.not_in_lod1)
				// and gltfpack merged their single placements INTO a node whose other rows do, so the switch
				// has to be per ROW there: pfaSwitchOn = 0 means "this placement has no second LOD, always draw".
				+ ( switchMask ? '\t\tvPfaFade = mix( 1.0, vPfaFade, pfaSwitchOn );\n' : '' )
				+ '\t}',
				'fade distance (vertex)' );
			shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
				`#include <common>\nvarying float vPfaFade;${HASH_GLSL}`, 'fade varying (fragment)' );
			// BEFORE the alpha test, so a dissolved fragment costs nothing further.  The dissolve is
			// stochastic rather than a coverage ramp because a card's alpha is a TEXTURE and three's
			// alphaToCoverage smoothstep would turn a constant per-tree factor back into a hard step.
			shader.fragmentShader = once( shader.fragmentShader, '#include <alphatest_fragment>',
				// STRICT `>=` against the impostor's strict `<`: the two tests partition [0,1) exactly,
				// including the pixels where the hash is exactly 0 (round-1 review 1).
				'if ( vPfaFade < 0.9995 && pfaHash( gl_FragCoord.xy ) >= vPfaFade ) discard;\n\t#include <alphatest_fragment>',
				'LOD dissolve' );
		}
		if ( it ) {
			// The vertex's own depth into its crown, written at load (prepareGeometry): one vec2 of
			// normalised bytes, no per-frame CPU work.  The THIRD component is computed here.
			shader.vertexShader = once( shader.vertexShader, '#include <common>',
				'#include <common>\nattribute vec2 pfaCrownD;\nvarying vec3 vPfaCrownD;\nuniform vec3 pfaSunDir;',
				'interior attribute (vertex)' );
			// THE SUN PATH, and why the depth term alone was not enough.  Measured on the forced-mesh
			// A/B (r3mA/r3mC): with the interior taken to BLACK the cam02 mesh crown lost 6 % of its
			// level, because a camera outside an opaque canopy only ever sees its outer SHELL - the
			// geometric interior is hidden behind the very leaves that are lit.  What is dark in the
			// reference is not the middle of the crown but the leaves the sun had to cross the crown
			// to reach.  So: treat the cluster as a sphere of its own radius, and measure how far a
			// sun ray travels inside it to arrive at this vertex - 0 on the sunward surface, 2 radii
			// on the far side.  `|u|` is the radius the depth attribute already carries, the
			// direction is the world radial, and `pfaSunDir` is the shared sun uniform, so this costs
			// one normalize per vertex and works through instancing and any rotation.
			shader.vertexShader = once( shader.vertexShader, '#include <worldpos_vertex>',
				'#include <worldpos_vertex>\n\t{\n'
				+ '\t\tvec4 pfaIC = vec4( pfaCrown, 1.0 );\n\t\tvec4 pfaIP = vec4( transformed, 1.0 );\n'
				+ '\t\t#ifdef USE_INSTANCING\n\t\tpfaIC = instanceMatrix * pfaIC;\n\t\tpfaIP = instanceMatrix * pfaIP;\n\t\t#endif\n'
				+ '\t\tvec3 pfaD3 = ( modelMatrix * pfaIP ).xyz - ( modelMatrix * pfaIC ).xyz;\n'
				+ '\t\tfloat pfaRad = 1.0 - clamp( pfaCrownD.x, 0.0, 1.0 );\n'
				+ '\t\tvec3 pfaU = ( dot( pfaD3, pfaD3 ) > 1e-10 ? normalize( pfaD3 ) : vec3( 0.0, 1.0, 0.0 ) ) * pfaRad;\n'
				+ '\t\tfloat pfaUL = dot( pfaU, pfaSunDir );\n'
				+ '\t\tfloat pfaPath = - pfaUL + sqrt( max( 1.0 - dot( pfaU, pfaU ) + pfaUL * pfaUL, 0.0 ) );\n'
				+ '\t\tvPfaCrownD = vec3( pfaCrownD.xy, clamp( pfaPath * 0.5, 0.0, 1.0 ) );\n\t}',
				'interior varying write' );
			shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
				'#include <common>\nvarying vec3 vPfaCrownD;\nuniform vec4 pfaInterior;\nuniform vec3 pfaInteriorB;',
				'interior varyings (fragment)' );
			// BEFORE `lights_fragment_end`, and it has to scale BOTH halves of the frame's light,
			// because they are finished at different points in the chunk chain:
			//   * the INDIRECT terms are still inputs here - `irradiance` carries the near trees'
			//     COLOR_0 bake and the shrubs' per-placement value, `iblIrradiance` the probe's
			//     diffuse, `radiance` its specular (and the sheen lobe computed from it) - and
			//     RE_IndirectDiffuse / RE_IndirectSpecular consume them inside the include;
			//   * the DIRECT terms are already accumulated: `lights_fragment_begin` ran the light
			//     loop long before this line.  Scaling only the inputs therefore missed every
			//     material that still has a sun diffuse, which is why r3max (interior fully black)
			//     moved the cam02 crown by 5 % and not by 40 %.  `reflectedLight` is scaled in place.
			// `pfaOcc` stays in scope for the translucent lobe appended after the include, which is
			// attenuated separately so the rim can keep it.
			shader.fragmentShader = once( shader.fragmentShader, '#include <lights_fragment_end>',
				'float pfaOcc = 1.0;\n\t{\n'
				+ '\t\tvec3 pfaD = clamp( vPfaCrownD, 0.0, 1.0 );\n'
				+ '\t\tpfaOcc = clamp( ( 1.0 - pfaInterior.x * pow( pfaD.x, pfaInterior.z ) - pfaInterior.y * pfaD.y\n'
				+ '\t\t\t- pfaInteriorB.y * pfaD.z ) * pfaInterior.w, 0.0, 4.0 );\n'
				// PHASE 7 ITEM B: the floor on the STACK of the three darkening terms.  Applied after
				// `gain`, so it bounds what the fragment actually keeps, and only from below, so no
				// fragment that was already bright enough moves at all.
				+ '\t\tpfaOcc = max( pfaOcc, pfaInteriorB.z );\n'
				+ '\t\tirradiance *= pfaOcc;\n\t\tiblIrradiance *= pfaOcc;\n\t\tradiance *= pfaOcc;\n'
				+ '\t\treflectedLight.directDiffuse *= pfaOcc;\n\t\treflectedLight.directSpecular *= pfaOcc;\n\t}\n'
				+ '\t#include <lights_fragment_end>', 'crown interior occlusion' );
		}
		if ( bias > 0 ) {
			// THE HARD EDGE (QA 16 open 1: 2x-8x the reference's hard-edge share).  A shrub card is a
			// 1 K cut-out drawn at 8-40 m, and three picks its mip from the screen-space derivative,
			// which for a card seen almost edge-on is a sharp level: the leaf boundary arrives as a
			// full-contrast step and `hard%` counts it.  The reference is Cycles with the same
			// texture and many rays per pixel.  A positive LOD bias asks for the next mip up, which
			// carries the same silhouette with a soft boundary - and it softens the ALPHA with it,
			// because the alpha is that texture's own channel, so the alphaToCoverage resolve gets a
			// gradient to work with instead of a step.  `?foliagebias=`; 0 is the round-16b path.
			let chunk = THREE.ShaderChunk.map_fragment;
			chunk = once( chunk, 'texture2D( map, vMapUv )', 'texture2D( map, vMapUv, pfaMipBias )', 'map mip bias' );
			shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
				'#include <common>\nuniform float pfaMipBias;', 'mip bias uniform' );
			shader.fragmentShader = once( shader.fragmentShader, '#include <map_fragment>', chunk,
				'map_fragment include' );
		}
		if ( trn > 0 ) {
			shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
				'#include <common>\nuniform float pfaTrnFac;\nuniform vec3 pfaTrnTint;\nuniform float pfaFrontSub;\n'
				+ 'uniform vec3 pfaSunDir;\nuniform vec3 pfaSunIrr;'
				+ ( trnMap ? '\nuniform sampler2D pfaTrnMap;' : '' ), 'translucency uniforms' );
			shader.fragmentShader = once( shader.fragmentShader, '#include <lights_fragment_end>',
				'#include <lights_fragment_end>\n\t{\n'
				+ '\t\tvec3 pfaL = normalize( ( viewMatrix * vec4( pfaSunDir, 0.0 ) ).xyz );\n'
				+ '\t\tfloat pfaBack = max( dot( - normal, pfaL ), 0.0 );\n'
				+ '\t\tfloat pfaFront = max( dot( normal, pfaL ), 0.0 );\n'
				// With the map, `t` is the texel (the Map Range in the Phase 5 node tree is already baked
				// into it) and pfaTrnFac carries only the ?leaftrn scale; without it, the constant.
				+ ( trnMap ? '\t\tfloat pfaT = pfaTrnFac * texture2D( pfaTrnMap, vMapUv ).r;\n'
					: '\t\tfloat pfaT = pfaTrnFac;\n' )
				// 6c round 3: the back lobe is the FULL unoccluded sun, which is right at the rim and
				// is half of why an interior leaf glowed.  `mix( 1, pfaOcc, pfaTrnOcc )` keeps it at
				// the silhouette (pfaOcc = 1 there) and attenuates it inside with everything else.
				+ ( it ? '\t\tfloat pfaTrnO = mix( 1.0, pfaOcc, pfaInteriorB.x );\n' : '' )
				+ `\t\treflectedLight.directDiffuse += ${it ? 'pfaTrnO * ' : ''}pfaSunIrr * RECIPROCAL_PI * diffuseColor.rgb * pfaT\n`
				+ '\t\t\t* ( pfaTrnTint * pfaBack - pfaFrontSub * pfaFront );\n\t}',
				'translucent mix' );
		}
		if ( cs ) {
			// PHASE 8a — THE CARD RELIGHT.  This patch REWRITES the line `patchBakedMaterial` appended
			// to `lights_fragment_maps` (`irradiance += vPfaInstIrr * <scale>;`), so it runs on the
			// shader the BAKED patch has already produced: `prev.call` above is that patch, and
			// materials.js is not touched by Phase 8a.  If the line is not there (a card material
			// with no per-placement irradiance), the throw is caught below and reported, and the
			// material compiles exactly as it does today.
			shader.fragmentShader = once( shader.fragmentShader, '#include <common>',
				'#include <common>\nuniform vec4 pfaCardSun;\nuniform vec3 pfaCardSunB;'
				// the sun's direction and colour come from the manifest, through the SHARED uniforms
				// the whole foliage pass already owns; declared here only where the translucent lobe
				// (the other consumer) has not declared them already.
				+ ( trn > 0 ? '' : '\nuniform vec3 pfaSunDir;\nuniform vec3 pfaSunIrr;' ),
				'card relight uniforms' );
			// `vPfaCrownD.z` is the sun's path through this vertex's cluster sphere (0 on the sunward
			// surface, 1 deep), written by the interior patch above; with `?cardint=0` there is no
			// such varying and the clump term degenerates to 1 - every card takes the pure cosine.
			const depth = it ? 'clamp( vPfaCrownD.z, 0.0, 1.0 )' : '0.0';
			shader.fragmentShader = onceRe( shader.fragmentShader,
				/irradiance \+= vPfaInstIrr \* ([0-9.]+);/,
				( _m, c ) => '{\n'
					+ `\t\tvec3 pfaE = vPfaInstIrr * ${c};\n`
					+ '\t\tfloat pfaSunLum = dot( pfaSunIrr, vec3( 0.2126, 0.7152, 0.0722 ) );\n'
					+ '\t\tvec3 pfaSunC = pfaSunLum > 1e-6 ? pfaSunIrr / pfaSunLum : vec3( 1.0 );\n'
					+ '\t\tpfaSunC = mix( vec3( 1.0 ), pfaSunC, pfaCardSunB.y );\n'
					// the sky share is 1 - f * s^ and may not go negative in any channel
					+ '\t\tfloat pfaShare = min( pfaCardSun.y,\n'
					+ '\t\t\t0.98 / max( max( pfaSunC.r, pfaSunC.g ), max( pfaSunC.b, 1e-6 ) ) );\n'
					+ '\t\tvec3 pfaSunL = normalize( ( viewMatrix * vec4( pfaSunDir, 0.0 ) ).xyz );\n'
					// `normal` is the shading normal: view space, the normal map in it, and already
					// flipped toward the camera on a DOUBLE_SIDED card.
					+ '\t\tfloat pfaCardNL = clamp( ( dot( normal, pfaSunL ) + pfaCardSun.z )\n'
					+ '\t\t\t/ ( 1.0 + pfaCardSun.z ), 0.0, 1.0 );\n'
					+ `\t\tfloat pfaCardClump = 1.0 - pfaCardSun.w * ${depth};\n`
					+ '\t\tfloat pfaCardG = clamp( pfaCardNL * pfaCardClump / max( pfaCardSunB.x, 1e-3 ),\n'
					+ '\t\t\t0.0, pfaCardSunB.z );\n'
					// the redistribution: at pfaCardG == 1 this is exactly the flat term, in every channel
					+ '\t\tirradiance += pfaE * max( vec3( 0.0 ),\n'
					+ '\t\t\tvec3( 1.0 ) + pfaCardSun.x * pfaShare * pfaSunC * ( pfaCardG - 1.0 ) );\n'
					+ '\t}',
				'card relight (the per-placement irradiance line)' );
		}
		} catch ( e ) { recordShaderError( `material ${mat.name || '(unnamed)'}`, e ); }
	};
	const prevKey = mat.customProgramCacheKey;
	mat.customProgramCacheKey = function () {
		// `sign`, `dist` and `band` are UNIFORMS, so they do not belong in the program key.
		// `pfaInterior` and `pfaTrnOcc` are uniforms; only WHETHER the interior is patched in is a
		// program difference, so one bit is all the key needs.
		return `${prevKey ? prevKey.call( this ) : ''}|fol:${trn.toFixed( 3 )}:${frontSub}:${fade ? 1 : 0}`
			+ `:${trnMap ? 1 : 0}:${switchMask ? 1 : 0}:${it ? 1 : 0}:${bias > 0 ? 1 : 0}`
			// 8a: the relight's numbers are UNIFORMS; only whether it is patched in is a program bit.
			+ `:${cs ? 1 : 0}`;
	};
	mat.needsUpdate = true;
	return true;
}

// ---------------------------------------------------------------- the pass

/**
 * @param {object} o
 * @param {THREE.Scene} o.scene
 * @param {THREE.DirectionalLight} o.sun
 * @param {boolean} o.msaa           the render target is multisampled (alphaToCoverage is worth it)
 * @param {number} o.normalBlend     0 = the card normals as exported, 1 = a pure crown sphere
 * @param {number} o.trnScale        multiplies every Phase 5 translucency constant (?leaftrn=)
 * @param {boolean} o.trnShrubs      also give the shrub/reed cards the directional back lobe
 * @param {number} o.meshDist        metres: within it a tree draws its mesh (Infinity = always mesh)
 * @param {number} o.fadeBand        metres of crossfade beyond meshDist
 * @param {object|string} o.interior      the crown interior term over CROWN_INTERIOR (?crownint=)
 * @param {object|string} o.cardInterior  the same for the shrub / reed card clusters (?cardint=)
 * @param {number} o.normalGate      the radius below which the crown bend is not applied (?leafgate=)
 */
export function applyFoliage( o ) {
	const { scene, sun, note = () => {} } = o;
	// Round-1 review 3: a non-numeric or out-of-range switch must fall back to its DEFAULT, never to
	// NaN - `smoothstep` with a NaN edge returns NaN, `hash > NaN` is false, and the frame loses every
	// foliage fragment (or keeps every one), which reads as a viewer bug rather than as a bad flag.
	const num = ( v, dflt, lo = - Infinity, hi = Infinity ) =>
		( Number.isFinite( v ) ? Math.min( Math.max( v, lo ), hi ) : dflt );
	const bend = num( o.normalBlend, 0.5, 0, 1 );
	const trnScale = num( o.trnScale, 1.0, 0, 8 );
	const meshDist = ( o.meshDist === Infinity ) ? Infinity : num( o.meshDist, 80, 0, 1e6 );   // Phase 7 C
	const fadeBand = num( o.fadeBand, 5, 0.01, 1e5 );
	// range x scale: the whole decode of COLOR_0 into scene-linear irradiance, from the manifest.
	const vertexIrrScale = num( o.vertexIrrScale, 0, 0, 1e9 );
	const cardBend = num( o.cardNormalBlend, 0, 0, 1 );
	// 6c round 3: the crown interior.  `interior` is the tree crowns' term and `cardInterior` the
	// shrub / reed card clusters' (which also want the `low` half: the bottom of a clump is shaded).
	const interior = parseInterior( o.interior, CROWN_INTERIOR );
	const cardInterior = parseInterior( o.cardInterior, CARD_INTERIOR );
	const normalGate = num( o.normalGate, NORMAL_GATE, 0, 0.99 );
	// `?cardenv=` — the ENVIRONMENT lobe on the LOD2 shrub / reed cards, the LOD1 set's `?shrubenv=`
	// applied to the cards it switches to.  MEASURED (6c round 3): with the lobe removed the station-3
	// LOD1 shrubs drop from 2.07x the reference to 1.34x and their hard-edge share from 12.5 % to
	// 6.8 %, and the cam02 reed clump from 1.38x to 1.06x with its hard-edge share landing on the
	// reference's (1.66 % against 1.57), while the per-placement diffuse - the term the bake ships and
	// the one both QA and the brief suspected - moves those boxes by less than 0.01x even when it is
	// multiplied by its own `cov`.  A card is one flat quad whose normal reflects the horizon, and the
	// PMREM lobe (with KHR_materials_sheen, which is an environment lobe too) hands every one of them
	// a sky highlight the Cycles reference's hundred separate leaves never get.
	const cardEnv = num( o.cardEnv, CARD_ENV, 0, 4 );
	// `?cardsun=` — PHASE 8a, the shrub / reed cards' directional relight (see CARD_SUN for the maths).
	// An explicit option wins; otherwise the page's own query string, so the lazily loaded glbs
	// (env_trees, env_shrubs) are relit exactly like the eager ones without a second switch.
	const cardSun = parseCardSun( o.cardSun !== undefined ? o.cardSun : cardSunFromLocation(), CARD_SUN );
	// `?foliagebias=` — the LOD bias on the cut-out fetch.  "cardBias" alone, or "cardBias,leafBias".
	const biases = String( o.mipBias === undefined || o.mipBias === null ? '' : o.mipBias ).split( ',' );
	const cardMip = num( parseFloat( biases[ 0 ] ), CARD_MIP_BIAS, 0, 4 );
	const leafMip = num( parseFloat( biases[ 1 ] ), LEAF_MIP_BIAS, 0, 4 );
	const report = { geometries: 0, clusters: 0, leafMaterials: 0, cardMaterials: 0, barkMaterials: 0,
		bent: 0, softened: 0, units: [], normalBlend: bend, trnScale, meshDist, fadeBand,
		trnShrubs: !! o.trnShrubs, msaa: !! o.msaa, skipped: [], vertexIrrScale, cardNormalBlend: cardBend,
		trnMapped: 0, byMesh: new Map(), recrown: null,
		interior, cardInterior, normalGate, interiorMaterials: 0, cardMipBias: cardMip, leafMipBias: leafMip,
		cardEnv, cardEnvMaterials: 0, cardEnvAlready: 0,
		cardSun, cardSunMaterials: 0, cardSunSkipped: [] };
	// 6c round 2: a lazily loaded glb (env_trees, env_shrubs) is a SECOND applyFoliage call, and its
	// materials must share the FIRST call's uniform objects - the impostor dissolve reads the same
	// pfaMeshDist / pfaFadeBand, and two copies would drift the moment a flag moved one of them.
	const shared = o.sharedUniforms ? { uniforms: o.sharedUniforms } : { uniforms: {
		pfaMeshDist: { value: Number.isFinite( meshDist ) ? meshDist : 1e9 },
		pfaFadeBand: { value: Math.max( fadeBand, 1e-3 ) },
		pfaSunDir: { value: sun ? sun.position.clone().normalize() : new THREE.Vector3( 0, 1, 0 ) },
		// three folds a light's intensity into its colour uniform, so this is the same vector the
		// built-in direct term uses; the sun is the only analytic light in the scene.
		pfaSunIrr: { value: sun ? sun.color.clone().multiplyScalar( sun.intensity ) : new THREE.Color( 0, 0, 0 ) },
	} };
	report.shared = shared;
	// export item D's per-texel translucency factor, by material name (materials.foliage); the map
	// already carries the Phase 5 constant, so where one exists the constant is NOT applied again.
	const trnMaps = o.trnMaps || {};

	const cache = new Map();          // geometry uuid -> its clustering
	const seenMat = new Set();
	const meshes = [];
	scene.updateMatrixWorld( true );  // the unit list is world space and is read once, here
	scene.traverse( ( m ) => {
		if ( ! m.isMesh || ! m.material ) return;
		const mats = Array.isArray( m.material ) ? m.material : [ m.material ];
		if ( ! mats.some( ( x ) => x && isTreeMat( x.name ) ) ) return;
		meshes.push( { mesh: m, mats } );
	} );

	for ( const { mesh, mats } of meshes ) {
		// mesh NAME -> the materials whose switch uniform that mesh obeys, so a caller that finds a
		// tree with no impostor behind it can put exactly those materials back on "always mesh".
		const byMesh = report.byMesh.get( mesh.name ) || [];
		for ( const m of mats ) if ( m && ! byMesh.includes( m ) ) byMesh.push( m );
		report.byMesh.set( mesh.name, byMesh );
		const foliage = mats.some( ( x ) => x && isFoliage( x.name ) );
		// THE SHRUB / REED CARDS ARE NOT BENT BY DEFAULT, and the reason is what their shader does
		// with a normal.  Their diffuse is one baked irradiance per placement added with NO cosine,
		// and `noEnvDiffuse: false` only lets the environment reach the 7 cov == 0 cards, so on 1 372
		// of the 1 379 the normal drives the SPECULAR alone.  Bending it outward therefore does not
		// round their shading; it aims more sky reflection at the camera.  Measured at cam02 in the
		// 60 520 700 980 box: blue 97.2 -> 104.6 where the Cycles reference has blue LOWEST at 97.7,
		// saturation 0.077 -> 0.033 against the reference's 0.098.  `?cardnormal=` is the A/B.
		const cardsOnly = foliage && ! mats.some( ( x ) => x && LEAF_RE.test( x.name || '' ) )
			&& mats.some( ( x ) => x && CARD_RE.test( x.name || '' ) );
		const thisBend = ! foliage ? 0 : ( cardsOnly ? cardBend : bend );
		let cl;
		try { cl = prepareGeometry( mesh.geometry, thisBend, cache, cardsOnly ? 0 : normalGate ); }
		catch ( e ) { report.skipped.push( `${mesh.name}: ${e.message}` ); continue; }
		if ( thisBend > 0 ) report.bent ++;
		for ( const mat of mats ) {
			if ( ! mat || ! mat.isMeshStandardMaterial || seenMat.has( mat.uuid ) ) continue;
			seenMat.add( mat.uuid );
			const p5 = PHASE5_LEAF[ mat.name ];
			const leaf = LEAF_RE.test( mat.name || '' );
			const card = CARD_RE.test( mat.name || '' );
			// The front sun diffuse is only there to be taken away where the material still HAS it:
			// `specularOnlySun` (the shrub/reed patch) has already removed it.
			const specOnly = !! ( mat.userData.pfaPatched && mat.userData.pfaPatched.specularOnlySun );
			const wantTrn = p5 && ( leaf || ( card && o.trnShrubs ) );
			const tmap = wantTrn ? ( trnMaps[ mat.name ] || null ) : null;
			// With the map the factor IS the texel (Map Range baked in), so the constant is not
			// multiplied in a second time; `trnScale` (?leaftrn=) still scales both paths.
			const trn = wantTrn ? ( tmap ? trnScale : p5.trn * trnScale ) : 0;
			if ( tmap ) report.trnMapped ++;
			patchFoliageMaterial( mat, {
				shared, trn, tint: ( tmap && tmap.userData && tmap.userData.pfaTint ) || ( p5 ? p5.tint : [ 1, 1, 1 ] ),
				trnMap: tmap,
				// per ROW where the geometry says so (the three shrub meshes with no LOD1)
				switchMask: !! ( mesh.geometry.attributes && mesh.geometry.attributes.pfaSwitchOn ),
				frontSub: specOnly ? 0 : 1, fade: true,
				// bark has no crown of its own (its cluster is the trunk, whose "interior" is the
				// axis), so it is left alone; leaves take the crown term, cards their own.
				interior: leaf ? interior : ( card ? cardInterior : null ),
				mipBias: leaf ? leafMip : ( card ? cardMip : 0 ),
				// The relight rewrites the per-placement irradiance line, so it is only offered to a
				// CARD material that actually has one (patchBakedMaterial has already run on every
				// one that does: `applyInstanceIrradiance` precedes `applyFoliage` in both paths).
				cardSun: ( card && instIrrOf( mat ) !== null ) ? cardSun : null,
				// The trees switch to their impostor at `meshDist`; the shrub/reed cards have no
				// second LOD until export item E lands, so they are patched with the SAME shader and
				// an infinite distance, and `applyShrubLod` only has to move a uniform.
				dist: card ? Infinity : meshDist, band: fadeBand, sign: 1,
			} );
			// Soft edges: keep the export's MASK cutoff exactly, let three resolve the boundary texel
			// across the MSAA samples instead of cutting it binary.
			// ONCE PER MATERIAL, and the guard is the point (r3 review 1).  `loadShrubLod1` scales the
			// same 25 clones by `?shrubenv=` before it calls this pass, so without the flag the LOD1
			// set shipped at 0.3 x 0.3 = 0.09 - three times less environment than the LOD2 cards it
			// dissolves into, which is exactly the discontinuity the shared constant exists to
			// prevent.  `pfaEnvScaled` is written by whichever pass gets there first and read by both.
			if ( card && mat.userData.pfaEnvScaled !== undefined ) {
				report.cardEnvAlready ++;
			} else if ( card && cardEnv !== 1 ) {
				mat.envMapIntensity = ( mat.envMapIntensity ?? 1 ) * cardEnv;
				if ( mat.sheenColor ) mat.sheenColor.multiplyScalar( cardEnv );
				mat.userData.pfaEnvScaled = cardEnv;
				mat.needsUpdate = true;
				report.cardEnvMaterials ++;
			}
			if ( o.msaa && mat.alphaTest > 0 ) { mat.alphaToCoverage = true; report.softened ++; }
			if ( mat.userData.pfaFoliage && mat.userData.pfaFoliage.interior ) report.interiorMaterials ++;
			if ( card && ! cardSunOff( cardSun ) ) {
				if ( instIrrOf( mat ) !== null ) report.cardSunMaterials ++;
				else report.cardSunSkipped.push( mat.name || '(unnamed)' );
			}
			if ( leaf ) report.leafMaterials ++; else if ( card ) report.cardMaterials ++; else report.barkMaterials ++;
		}
	}
	report.geometries = cache.size;
	let dw = 0, dn = 0, bigCluster = 0;
	for ( const cl of cache.values() ) {
		report.clusters += cl.count;
		// the mean depth actually written, so "the interior term did nothing" can be told from
		// "the interior term is off" without a debug render
		if ( cl.depthMean !== undefined ) { dw += cl.depthMean * cl.ids.length; dn += cl.ids.length; }
		for ( let i = 0; i < cl.count; i ++ ) {
			const b = cl.boxes[ i ];
			if ( Math.max( b.max.x - b.min.x, b.max.z - b.min.z ) > 40 ) bigCluster ++;
		}
	}
	report.depthMean = dn ? dw / dn : 0;
	report.clustersOver40m = bigCluster;

	// ---- the tree units: one per crown cluster per instance, in world space -----------------
	const box = new THREE.Box3(), mtx = new THREE.Matrix4();
	const crowns = [], trunks = [];
	for ( const { mesh, mats } of meshes ) {
		const cl = cache.get( mesh.geometry.uuid );
		if ( ! cl ) continue;
		const leafMat = mats.find( ( x ) => x && LEAF_RE.test( x.name || '' ) );
		const barkOnly = ! leafMat && mats.some( ( x ) => x && BARK_RE.test( x.name || '' ) );
		if ( ! leafMat && ! barkOnly ) continue;         // shrub / reed cards are not trees
		const n = mesh.isInstancedMesh ? mesh.count : 1;
		for ( let i = 0; i < n; i ++ ) {
			if ( mesh.isInstancedMesh ) mtx.fromArray( mesh.instanceMatrix.array, i * 16 ).premultiply( mesh.matrixWorld );
			else mtx.copy( mesh.matrixWorld );
			for ( let c = 0; c < cl.count; c ++ ) {
				box.copy( cl.boxes[ c ] ).applyMatrix4( mtx );
				const centre = box.getCenter( new THREE.Vector3() ), size = box.getSize( new THREE.Vector3() );
				const cm = cl.colourMean;
				const rec = { centre, minY: box.min.y, maxY: box.max.y, width: Math.max( size.x, size.z ),
					mesh: mesh.name, instance: i, material: leafMat ? leafMat.name : null,
					geo: mesh.geometry, cluster: c, mtx: mtx.clone(), barkOnly,
					// decoded with the ONE global range the manifest declares x lightmaps.scale
					irradiance: ( cm && vertexIrrScale > 0 )
						? [ cm[ c * 3 ] * vertexIrrScale, cm[ c * 3 + 1 ] * vertexIrrScale, cm[ c * 3 + 2 ] * vertexIrrScale ]
						: null };
				( leafMat ? crowns : trunks ).push( rec );
			}
		}
	}
	// pair each crown with the nearest trunk cluster, so the impostor's height is the WHOLE tree
	for ( const c of crowns ) {
		let best = null, bestD = PAIR_MAX_M;
		for ( const t of trunks ) {
			const d = Math.hypot( t.centre.x - c.centre.x, t.centre.z - c.centre.z );
			if ( d < bestD ) { bestD = d; best = t; }
		}
		report.units.push( {
			centre: c.centre, crownY: c.centre.y, width: Math.max( c.width, best ? best.width : c.width ),
			baseY: best ? Math.min( best.minY, c.minY ) : c.minY,
			topY: Math.max( c.maxY, best ? best.maxY : c.maxY ),
			species: SPECIES_OF[ c.material ] || null, mesh: c.mesh, instance: c.instance,
			trunkDist_m: best ? bestD : null, irradiance: c.irradiance,
		} );
	}
	// ROUND-1 REVIEW 2 — the trunk must cross the switch distance at the same frame as its crown.
	// The bark cluster's own centre sits several metres BELOW the crown centre the impostor's iSwitch
	// uses, so a bark-only mesh dissolved at a different distance from the canopy above it.  The
	// pairing already exists (PAIR_MAX_M); here it is run the other way round and the crown's centre
	// is written back into the BARK geometry's pfaCrown, in that geometry's own local space.
	// One instance is enough: a tree is rigid, so crown - trunk is the same offset in every row.
	{
		const rc = { clusters: 0, unpaired: 0, maxMove_m: 0 };
		const done = new Set(), inv = new THREE.Matrix4(), local = new THREE.Vector3();
		for ( const t of trunks ) {
			if ( ! t.barkOnly ) continue;
			const k = `${t.geo.uuid}:${t.cluster}`;
			if ( done.has( k ) ) continue;
			done.add( k );
			let best = null, bestD = PAIR_MAX_M;
			for ( const c of crowns ) {
				const d = Math.hypot( c.centre.x - t.centre.x, c.centre.z - t.centre.z );
				if ( d < bestD ) { bestD = d; best = c; }
			}
			if ( ! best ) { rc.unpaired ++; continue; }
			inv.copy( t.mtx ).invert();
			local.copy( best.centre ).applyMatrix4( inv );
			const cl = cache.get( t.geo.uuid ), attr = t.geo.getAttribute( 'pfaCrown' );
			if ( ! cl || ! attr ) { rc.unpaired ++; continue; }
			for ( let v = 0; v < cl.ids.length; v ++ ) {
				if ( cl.ids[ v ] !== t.cluster ) continue;
				attr.array[ v * 3 ] = local.x; attr.array[ v * 3 + 1 ] = local.y; attr.array[ v * 3 + 2 ] = local.z;
			}
			attr.needsUpdate = true;
			rc.clusters ++;
			rc.maxMove_m = Math.max( rc.maxMove_m, best.centre.distanceTo( t.centre ) );
		}
		report.recrown = rc;
		if ( rc.clusters || rc.unpaired )
			note( `foliage: ${rc.clusters} bark cluster(s) re-crowned so trunk and canopy cross the LOD distance `
				+ `together (max move ${rc.maxMove_m.toFixed( 2 )} m)`
				+ ( rc.unpaired ? `; ${rc.unpaired} found no crown within ${PAIR_MAX_M} m and keep their own centre` : '' ) );
	}

	note( `foliage: ${report.geometries} geometr(ies) clustered into ${report.clusters} crown(s), `
		+ `normals bent ${bend.toFixed( 2 )} toward the crown centre on ${report.bent} mesh(es) `
		+ `(shrub/reed cards at ${cardBend.toFixed( 2 )}: the normal only drives their specular); `
		+ `${report.leafMaterials} leaf + ${report.cardMaterials} card + ${report.barkMaterials} bark material(s) patched, `
		+ `${report.softened} on alphaToCoverage (${o.msaa ? 'MSAA target' : 'no MSAA: hard cut kept'}); `
		+ `translucency x${trnScale} from the Phase 5 constants`
		+ ( o.trnShrubs ? ' (shrub/reed cards INCLUDED, ?leaftrn=shrubs)' : ' (shrub/reed cards excluded: their diffuse is the direction-independent baked placement irradiance)' )
		+ `; ${report.units.length} near-tree unit(s) found, LOD switch at ${Number.isFinite( meshDist ) ? `${meshDist} m + ${fadeBand} m fade` : 'never (mesh always)'}` );
	const fmt = ( x ) => `str ${x.str.toFixed( 2 )} low ${x.low.toFixed( 2 )} gamma ${x.gamma.toFixed( 2 )} `
		+ `gain ${x.gain.toFixed( 2 )} trn ${x.trn.toFixed( 2 )} sun ${x.sun.toFixed( 2 )}`;
	note( `foliage: environment lobe x${cardEnv} on ${report.cardEnvMaterials} card material(s)`
		+ ( report.cardEnvAlready ? `, ${report.cardEnvAlready} already scaled by an earlier pass and LEFT ALONE` : '' )
		+ ' (?cardenv=, shared with ?shrubenv= so the LOD switch cannot change a shrub\'s level)' );
	note( `foliage interior: ${report.interiorMaterials} material(s) darkened by depth into their own cluster — `
		+ `crowns (${fmt( interior )}), cards (${fmt( cardInterior )}); crown-bend gated above `
		+ `r ${normalGate.toFixed( 2 )} of the cluster half-extent (?leafgate=, ?crownint=, ?cardint=)` );
	if ( report.skipped.length ) note( `foliage: ${report.skipped.length} mesh(es) skipped: ${report.skipped.slice( 0, 4 ).join( '; ' )}` );
	return report;
}

/**
 * C3 — shrub / reed LOD: LOD1 within `dist` metres of the walker, LOD2 beyond, both sharing the
 * placement's baked irradiance.  The meshes come from export item E; until they land this is a code
 * path with nothing to switch, and it says so rather than pretending.
 *
 * THE CONTRACT IT READS (gltfpack drops node names, so the manifest must name the nodes, never a
 * string in the glb).  Either of:
 *   `raw.shrub_lod = { dist_m?, lod1_nodes: [n, ...], lod2_nodes: [n, ...] }`   (glTF node indices
 *       into env.glb, the same index space as `lightmaps.instance_irradiance.nodes[].gltf_node`), or
 *   a `lod` field of "LOD1" / "LOD2" on each `lightmaps.instance_irradiance.nodes[]` entry.
 * Both are joined through `mesh.userData.pfaGltfNode`, exactly as the instance irradiance is, and a
 * node the scene does not present is reported, never silently skipped.
 */
export function applyShrubLod( { scene, manifest, note = () => {}, dist } ) {
	// `undefined` is "the caller did not ask", so an explicit ?shrublod=30 is still an override and
	// any explicit value still beats the manifest's own dist_m (round-1 review 9).
	const asked = Number.isFinite( dist );
	const out = { dist: asked ? dist : 30, lod1: 0, lod2: 0, missing: [], source: null, asked };
	dist = out.dist;
	const raw = ( manifest && manifest.raw ) || {};
	const ii = ( manifest && manifest.gate3 && manifest.gate3.instanceIrradiance ) || null;
	const lod1 = new Set(), lod2 = new Set();
	if ( raw.shrub_lod && ( raw.shrub_lod.lod1_nodes || raw.shrub_lod.lod2_nodes ) ) {
		( raw.shrub_lod.lod1_nodes || [] ).forEach( ( n ) => lod1.add( n ) );
		( raw.shrub_lod.lod2_nodes || [] ).forEach( ( n ) => lod2.add( n ) );
		if ( typeof raw.shrub_lod.dist_m === 'number' && ! asked ) out.dist = dist = raw.shrub_lod.dist_m;
		out.source = 'shrub_lod';
	} else if ( ii && ii.nodes && ii.nodes.some( ( n ) => n.lod ) ) {
		for ( const n of ii.nodes ) {
			if ( String( n.lod ).toUpperCase() === 'LOD1' ) lod1.add( n.gltf_node );
			else if ( String( n.lod ).toUpperCase() === 'LOD2' ) lod2.add( n.gltf_node );
		}
		out.source = 'instance_irradiance.nodes[].lod';
	}
	if ( ! lod1.size && ! lod2.size ) {
		note( `shrub/reed LOD: no LOD1 set in the manifest (export item E) — every card stays on the shipped LOD2, `
			+ `switch distance ${dist} m is wired and idle (?shrublod=)` );
		return out;
	}
	const seen = new Set();
	scene.traverse( ( m ) => {
		if ( ! m.isMesh ) return;
		const gn = m.userData && m.userData.pfaGltfNode;
		if ( gn === undefined ) return;
		const sign = lod1.has( gn ) ? 1 : ( lod2.has( gn ) ? - 1 : 0 );
		if ( ! sign ) return;
		seen.add( gn );
		for ( const mat of Array.isArray( m.material ) ? m.material : [ m.material ] ) {
			const f = mat && mat.userData.pfaFoliage;
			if ( ! f ) continue;
			f.uniforms.pfaSwitchDist.value = dist;
			f.uniforms.pfaSwitchSign.value = sign;
			f.dist = dist; f.sign = sign;
			if ( sign > 0 ) out.lod1 ++; else out.lod2 ++;
		}
	} );
	for ( const n of [ ...lod1, ...lod2 ] ) if ( ! seen.has( n ) ) out.missing.push( String( n ) );
	note( `shrub/reed LOD (${out.source}): LOD1 within ${dist} m on ${out.lod1} material(s), LOD2 beyond on ${out.lod2}`
		+ ( out.missing.length ? `; node(s) NOT in the scene: ${out.missing.join( ', ' )}` : '' ) );
	return out;
}

/**
 * ∫ L dω over an equirectangular sky, as a Vector3 (scene-linear).  Used only for its CHROMATICITY:
 * it is the sky half of the irradiance the impostor atlases were baked under (`manifest.impostors.
 * lighting`: each prototype alone on a lawn under the whole open sky), and the bake's diagnosis
 * measured that light at hue 225 deg against the scene's 52 deg.
 */
export function equirectIntegral( texture ) {
	const img = texture && texture.image;
	if ( ! img || ! img.data || ! img.width || ! img.height ) return null;
	const { data, width: w, height: h } = img;
	const half = data.BYTES_PER_ELEMENT === 2;
	const ch = data.length / ( w * h );
	if ( ch < 3 ) return null;
	const get = ( i ) => ( half ? THREE.DataUtils.fromHalfFloat( data[ i ] ) : data[ i ] );
	const acc = new THREE.Vector3();
	const dTheta = Math.PI / h, dPhi = 2 * Math.PI / w;
	for ( let j = 0; j < h; j ++ ) {
		const sinT = Math.sin( ( j + 0.5 ) * dTheta ) * dTheta * dPhi;
		let r = 0, g = 0, b = 0;
		for ( let i = 0; i < w; i ++ ) {
			const k = ( j * w + i ) * ch;
			r += get( k ); g += get( k + 1 ); b += get( k + 2 );
		}
		acc.x += r * sinT; acc.y += g * sinT; acc.z += b * sinT;
	}
	return acc;
}

/**
 * C2 / the bake's impostor diagnosis: the per-placement modulation `E_placement / E_bake`.
 *
 * `mode`:
 *   'full'    the ratio as it stands - only correct once E_bake is a MEASURED value (the bake ships
 *             it per prototype in the far-tree irradiance JSON);
 *   'chroma'  the ratio normalised to unit luminance, so only the COLOUR of the light is corrected
 *             and the atlas keeps its own level.  This is the default while E_bake is the viewer's
 *             own estimate (sun + sky integral), because an estimate that is off by a factor would
 *             otherwise re-light every far tree by that factor.
 */
/**
 * The ratio rules, as the manifest states them.  `trees.far_mesh.lighting.impostor` ships `strength`,
 * `clamp` and `zero_channel_fallback`, and its own `how` is the formula below verbatim:
 *     atlas_frame * clamp( ( E_placement / E_bake ) ** strength, 0, clamp )   per channel.
 * The constants here are only the fallback for a manifest that does not carry the block; they happen
 * to equal today's values, which is exactly why reading them matters - a bake that changes the
 * ceiling would otherwise be silently ignored by the viewer.
 */
export const RATIO_RULES = { strength: 1.0, clamp: 4.0, zeroChannelFallback: 1.0 };

export function ratioRules( raw ) {
	const b = raw && raw.trees && raw.trees.far_mesh && raw.trees.far_mesh.lighting
		&& raw.trees.far_mesh.lighting.impostor;
	const num = ( v, d ) => ( typeof v === 'number' && isFinite( v ) && v > 0 ? v : d );
	return b ? {
		strength: num( b.strength, RATIO_RULES.strength ),
		clamp: num( b.clamp, RATIO_RULES.clamp ),
		// a fallback of 0 is meaningful (draw nothing there), so it is only rejected when absent
		zeroChannelFallback: ( typeof b.zero_channel_fallback === 'number' && isFinite( b.zero_channel_fallback ) )
			? b.zero_channel_fallback : RATIO_RULES.zeroChannelFallback,
		from: 'trees.far_mesh.lighting.impostor',
	} : { ...RATIO_RULES, from: 'the viewer\'s defaults (no impostor block in the manifest)' };
}

export function irradianceRatio( ePlacement, eBake, mode = 'chroma', rules = RATIO_RULES ) {
	if ( ! ePlacement || ! eBake ) return null;
	// a number keeps the old call shape (the clamp) working
	const R = ( typeof rules === 'number' ) ? { ...RATIO_RULES, clamp: rules } : ( rules || RATIO_RULES );
	// "fall back to `zero_channel_fallback` where E_bake has a zero channel" - a zero channel is not a
	// small number, it is no measurement at all, and 0/0 would otherwise re-light it arbitrarily.
	const r = [ 0, 1, 2 ].map( ( i ) => ( eBake[ i ] > 1e-9
		? Math.pow( ePlacement[ i ] / eBake[ i ], R.strength ) : R.zeroChannelFallback ) );
	if ( ! r.every( ( x ) => isFinite( x ) && x > 0 ) ) return null;
	// The ceiling applies to the RATIO, in BOTH modes: a placement the bake measured in deep shade
	// divided by a nursery under the open sky can otherwise run away, and chroma's normalisation
	// divides by a luminance that the same runaway channel dominates.
	const c = r.map( ( x ) => Math.min( x, R.clamp ) );
	if ( mode !== 'chroma' ) return c;
	const lum = 0.2126 * c[ 0 ] + 0.7152 * c[ 1 ] + 0.0722 * c[ 2 ];
	return lum > 1e-9 ? c.map( ( x ) => x / lum ) : null;
}

/**
 * The far trees' own modulation, when the bake's JSON is in the manifest.  Contract (bake item 2 /
 * `trees.far_mesh.lighting`): `prototypes: { <name>: { E_bake: [r,g,b] } }` and a placement list
 * carrying a Blender location and an rgb, joined to `manifest.treesFar[i].base` BY LOCATION - the
 * same join the shrub irradiance uses, with the same refusal to guess when it does not land.
 */
export function farTreeIrradiance( treesFar, raw, mode, note = () => {} ) {
	const lit = raw && raw.trees && raw.trees.far_mesh && raw.trees.far_mesh.lighting;
	// schema /2 nests the rows per mesh and makes the top-level `placements` a count, so `rows` is the
	// flattened list `loadFarTreeLighting` leaves behind; an inline block may use either name.
	const rows = lit && ( lit.rows || lit.instances || ( Array.isArray( lit.placements ) ? lit.placements : null ) );
	if ( ! lit || ! Array.isArray( rows ) || ! rows.length || ! lit.prototypes ) {
		note( 'far-tree impostor modulation: the bake\'s trees.far_mesh.lighting is not in the manifest yet '
			+ '(E_placement per placement + E_bake per prototype); the far atlases draw unmodulated' );
		return { applied: 0, unmatched: 0, byIndex: new Map() };
	}
	const rules = ratioRules( raw );
	const key = ( p ) => `${p[ 0 ].toFixed( 2 )},${p[ 1 ].toFixed( 2 )},${p[ 2 ].toFixed( 2 )}`;
	const byLoc = new Map();
	for ( const r of rows ) {
		const loc = r.location_blender || r.loc || r.location;
		if ( Array.isArray( loc ) && Array.isArray( r.rgb ) ) byLoc.set( key( loc ), r.rgb );
	}
	const byIndex = new Map();
	let unmatched = 0;
	treesFar.forEach( ( t, i ) => {
		const e = Array.isArray( t.base ) ? byLoc.get( key( t.base ) ) : null;
		const proto = lit.prototypes[ t.prototype ] || lit.prototypes[ ( raw.impostors && raw.impostors.prototype_map && raw.impostors.prototype_map[ t.prototype ] ) || t.prototype ];
		const eb = proto && ( proto.E_bake || proto.e_bake );
		const ratio = irradianceRatio( e, eb, mode, rules );
		if ( ratio ) byIndex.set( i, ratio ); else unmatched ++;
	} );
	note( `far-tree impostor modulation: ${byIndex.size}/${treesFar.length} placement(s) joined by location `
		+ `(${unmatched} unmatched), mode ${mode}, strength ${rules.strength}, clamp ${rules.clamp}, `
		+ `zero-channel fallback ${rules.zeroChannelFallback} (from ${rules.from})` );
	return { applied: byIndex.size, unmatched, byIndex };
}

/**
 * C2: turn the near-tree units into impostor entries in the shape `buildImpostors` reads, choosing
 * each one's prototype by SPECIES and then by the closest width/height aspect - the export dropped
 * the node names, so the material is the only species evidence in the glb, and the aspect is what
 * separates a columnar cypress from a spreading one.
 */
export function nearTreeImpostorEntries( units, impostors, note = () => {}, eBake = null, mode = 'chroma' ) {
	const out = [], chosen = {};
	// Round-1 review 4: the mesh fade is a per-MATERIAL uniform, so a unit that matches no prototype
	// still dissolves at the switch distance with NOTHING behind it.  Every such unit's mesh is
	// collected here and the caller puts those materials back on "always mesh".
	out.unmatched = [];
	if ( ! impostors || ! impostors.prototypes ) { out.unmatched = units.slice(); return out; }
	const protos = Object.entries( impostors.prototypes );
	for ( const u of units ) {
		if ( ! u.species ) { out.unmatched.push( u ); continue; }
		const cands = protos.filter( ( [ k ] ) => k.toLowerCase().includes( u.species ) );
		if ( ! cands.length ) { out.unmatched.push( u ); continue; }
		const height = Math.max( u.topY - u.baseY, 0.1 );
		const aspect = u.width / height;
		let best = null, bestE = Infinity;
		for ( const [ k, p ] of cands ) {
			if ( ! ( p.heightAboveBase > 0 ) || ! ( p.radius > 0 ) ) continue;
			const e = Math.abs( Math.log( ( 2 * p.radius / p.heightAboveBase ) / aspect ) );
			if ( e < bestE ) { bestE = e; best = k; }
		}
		if ( ! best ) { out.unmatched.push( u ); continue; }
		chosen[ best ] = ( chosen[ best ] || 0 ) + 1;
		// `eBake` is either ONE rgb (the viewer's own sky estimate) or a map keyed by PROTOTYPE (the
		// bake's measured E_bake, which is per prototype because each atlas was baked in its own
		// nursery).  A near tree borrows the atlas of the prototype it was matched to, so it must
		// divide by THAT prototype's value.
		const eb = Array.isArray( eBake ) ? eBake : ( eBake && eBake[ best ] ) || null;
		out.push( {
			prototype: best, id: `near_${u.mesh}_${u.instance}_${out.length}`, height,
			// `base` is BLENDER (x, y, z) as manifest.impostors.placement states, from the three-space
			// trunk base: three (x, y, z) -> Blender (x, -z, y).
			base: [ u.centre.x, - u.centre.z, u.baseY ],
			near: true, switchCentre: [ u.centre.x, u.centre.y, u.centre.z ],
			// E_placement is this crown's own mean COLOR_0 irradiance - the only measured "what light
			// does this tree stand in" the viewer owns until the bake ships the far trees' values.
			irr: ( mode === '0' || ! mode ) ? null : irradianceRatio( u.irradiance, eb, mode ),
		} );
	}
	note( `near-tree impostors: ${out.length}/${units.length} unit(s) matched a prototype by species + aspect `
		+ `(${Object.entries( chosen ).map( ( [ k, v ] ) => `${k.replace( /^ENV_tree_|_LOD1$/g, '' )} x${v}` ).join( ', ' )})`
		+ ( out.unmatched.length ? `; ${out.unmatched.length} unit(s) matched NOTHING and keep their mesh at every distance` : '' ) );
	return out;
}


/**
 * Round-1 review 4 — put the materials of these meshes back on "always draw the mesh" (an infinite
 * switch distance), because no impostor was built behind them.  Returns the number of materials moved.
 */
export function keepMeshAlways( report, meshNames, note = () => {} ) {
	if ( ! report || ! report.byMesh || ! meshNames || ! meshNames.length ) return 0;
	const seen = new Set();
	let n = 0;
	for ( const name of new Set( meshNames ) ) {
		for ( const mat of report.byMesh.get( name ) || [] ) {
			const f = mat && mat.userData.pfaFoliage;
			if ( ! f || seen.has( mat.uuid ) ) continue;
			seen.add( mat.uuid );
			f.uniforms.pfaSwitchDist.value = 1e9; f.dist = Infinity;
			n ++;
		}
	}
	if ( n ) note( `foliage: ${n} material(s) kept on the mesh at every distance - their tree(s) have no impostor to fade into` );
	return n;
}
