// Normalises export/out/<gate>/manifest.json (written by the bake engineer) into what the viewer needs,
// so a schema change there is absorbed in one place.  Every field that had to be defaulted is reported
// in `notes` and logged, because a silently defaulted exposure or sun vector makes parity meaningless.
import stationsFallback from './stations_blender.json';

export const WATER_Z = - 1.3;   // scripts/common.py

function pick( obj, ...keys ) {
	for ( const k of keys ) {
		const v = k.split( '.' ).reduce( ( o, p ) => ( o == null ? o : o[ p ] ), obj );
		if ( v !== undefined && v !== null ) return v;
	}
	return undefined;
}

export function resolveUrl( base, url ) {
	if ( ! url ) return null;
	if ( /^(https?:)?\//.test( url ) ) return url;
	return new URL( url, base ).href;
}

/**
 * @param {object|null} raw  parsed manifest.json (null -> pure defaults, test-scene mode)
 * @param {string} baseUrl   absolute URL of the manifest, for relative asset paths
 */
export function normaliseManifest( raw, baseUrl ) {
	const notes = [];
	const def = ( value, fallback, what ) => {
		if ( value === undefined || value === null ) { notes.push( `defaulted ${what} = ${JSON.stringify( fallback )}` ); return fallback; }
		return value;
	};
	raw = raw || {};

	// --- geometry ------------------------------------------------------------------------------
	const glbRaw = pick( raw, 'glb', 'scene', 'model', 'assets.glb', 'files.glb' );
	const glb = resolveUrl( baseUrl, typeof glbRaw === 'string' ? glbRaw : glbRaw?.url );

	// --- stations ------------------------------------------------------------------------------
	let stations = pick( raw, 'stations', 'cameras' );
	if ( ! stations || ! stations.length ) { stations = stationsFallback.stations; notes.push( 'stations: manifest had none, using scripts/qa_cameras.py fallback' ); }
	stations = stations.map( ( s, i ) => ( {
		index: s.index ?? i + 1,
		name: s.name ?? `station_${i + 1}`,
		location: s.location ?? s.loc,
		target: s.target ?? null,
		rotation_euler: s.rotation_euler ?? s.rotation ?? null,
		matrix_world: s.matrix_world ?? s.matrix ?? null,
		lens: s.lens ?? 35,
		sensor_width: s.sensor_width ?? 36,
		sensor_fit: s.sensor_fit ?? 'HORIZONTAL',
		shift_x: s.shift_x ?? 0,
		shift_y: s.shift_y ?? 0,
		clip_start: s.clip_start ?? 0.1,
		clip_end: s.clip_end ?? 5000,
	} ) );

	// --- colour --------------------------------------------------------------------------------
	const lutRaw = pick( raw, 'lut', 'colour.lut', 'color.lut' );
	const lut = lutRaw ? {
		url: resolveUrl( baseUrl, typeof lutRaw === 'string' ? lutRaw : ( lutRaw.url || lutRaw.path || lutRaw.file ) ),
		size: ( typeof lutRaw === 'object' && ( lutRaw.size ?? lutRaw.lut_size ) ) || null,
		shaper: ( typeof lutRaw === 'object' && lutRaw.shaper ) || null,
		shaperMin: ( typeof lutRaw === 'object' && ( lutRaw.shaper_min ?? lutRaw.shaperMin ) ) ?? undefined,
		shaperMax: ( typeof lutRaw === 'object' && ( lutRaw.shaper_max ?? lutRaw.shaperMax ) ) ?? undefined,
	} : null;
	if ( ! lut ) notes.push( 'no LUT in the manifest: the display pass falls back to gamma 2.2 (NOT the Phase 5 look)' );

	// Exposure.  A manifest may give a multiplier (exposure_multiplier / exposure_scale) or EV
	// (exposure_ev, or `exposure` matching Blender's scene.view_settings.exposure = -2.833).
	// If the LUT was baked WITH the exposure applied (lut.includes_exposure), the pass multiplies by 1.
	let exposure = pick( raw, 'exposure_multiplier', 'exposure_scale', 'colour.exposure_multiplier' );
	const ev = pick( raw, 'exposure_ev', 'exposure', 'view.exposure', 'colour.exposure' );
	const lutHasExposure = pick( raw, 'lut.includes_exposure', 'colour.lut.includes_exposure' );
	if ( exposure === undefined ) {
		if ( lutHasExposure === true ) { exposure = 1.0; notes.push( 'exposure: LUT declares includes_exposure, pass multiplier = 1' ); }
		else if ( ev !== undefined ) { exposure = Math.pow( 2, ev ); notes.push( `exposure: ${ev} EV -> multiplier ${Math.pow( 2, ev ).toFixed( 5 )}` ); }
		else { exposure = 1.0; notes.push( 'exposure: absent, multiplier = 1 (assumes the LUT carries -2.833 EV)' ); }
	}

	// --- sky -----------------------------------------------------------------------------------
	const sky = pick( raw, 'sky', 'world', 'environment' ) || {};
	const skyCamera = resolveUrl( baseUrl, pick( sky, 'camera', 'background', 'camera_hdr', 'camera_exr' ) );
	const skyGlossy = resolveUrl( baseUrl, pick( sky, 'glossy', 'specular', 'glossy_hdr', 'glossy_exr' ) );
	const skyRotationDeg = def( pick( sky, 'rotation_deg', 'rotation' ), 180,
		'sky.rotation_deg (Blender equirect u=0.5 faces -X, three faces +X)' );

	// --- sun (specular only; the diffuse is in the lightmaps) ----------------------------------
	const sunRaw = pick( raw, 'sun', 'light.sun' ) || {};
	let sunDirBlender = pick( sunRaw, 'direction', 'vector', 'dir' );        // direction the light travels TO the scene
	const az = pick( sunRaw, 'azimuth', 'azimuth_deg' ), el = pick( sunRaw, 'elevation', 'elevation_deg' );
	if ( ! sunDirBlender && az !== undefined && el !== undefined ) {
		// scripts/common.sun_direction: azimuth clockwise from north, -X = north, +Y = east
		const a = az * Math.PI / 180, e = el * Math.PI / 180;
		sunDirBlender = [ - Math.cos( a ) * Math.cos( e ), Math.sin( a ) * Math.cos( e ), Math.sin( e ) ];
		notes.push( `sun: direction from azimuth ${az} / elevation ${el}` );
	}
	if ( ! sunDirBlender ) { sunDirBlender = [ - Math.cos( 118.5 * Math.PI / 180 ) * Math.cos( 7.36 * Math.PI / 180 ), Math.sin( 118.5 * Math.PI / 180 ) * Math.cos( 7.36 * Math.PI / 180 ), Math.sin( 7.36 * Math.PI / 180 ) ]; notes.push( 'sun: absent, using the Phase 5 world (az 118.5, el 7.36)' ); }
	const sun = {
		directionBlender: sunDirBlender,
		irradiance: def( pick( sunRaw, 'irradiance', 'strength', 'energy' ), 67.3, 'sun.irradiance (W/m2, Phase 5 LIGHT_sun)' ),
		color: pick( sunRaw, 'color', 'colour' ) || [ 1, 1, 1 ],
		angleDeg: pick( sunRaw, 'angle_deg', 'angle' ) ?? 0.526,
	};

	// --- lightmaps -----------------------------------------------------------------------------
	// Accepted shapes: {lightmaps:[{match|object|mesh|material, url, encoding, intensity}]}
	//                  {assets:[{name, lightmap:{url, encoding}}]}
	const lightmaps = [];
	for ( const lm of pick( raw, 'lightmaps' ) || [] ) {
		lightmaps.push( {
			match: lm.match ?? lm.object ?? lm.mesh ?? lm.material ?? lm.name,
			matchKind: lm.material ? 'material' : 'object',
			url: resolveUrl( baseUrl, lm.url || lm.path || lm.file ),
			encoding: lm.encoding || 'linear',
			intensity: lm.intensity ?? 1.0,
			rgbmMaxRange: lm.rgbm_max_range ?? lm.max_range ?? 7.0,
		} );
	}
	for ( const a of pick( raw, 'assets' ) || [] ) {
		const lm = a.lightmap;
		if ( ! lm ) continue;
		lightmaps.push( {
			match: a.name ?? a.object,
			matchKind: 'object',
			url: resolveUrl( baseUrl, typeof lm === 'string' ? lm : ( lm.url || lm.path || lm.file ) ),
			encoding: ( typeof lm === 'object' && lm.encoding ) || 'linear',
			intensity: ( typeof lm === 'object' && lm.intensity ) ?? 1.0,
			rgbmMaxRange: ( typeof lm === 'object' && ( lm.rgbm_max_range ?? lm.max_range ) ) ?? 7.0,
		} );
	}

	const out = {
		raw, baseUrl, glb, stations, lut, exposure, sun, lightmaps, notes,
		waterZ: def( pick( raw, 'water_z', 'waterZ', 'scene.water_z' ), WATER_Z, 'water_z' ),
		sky: { camera: skyCamera, glossy: skyGlossy, rotationDeg: skyRotationDeg },
		frameSize: pick( raw, 'frame', 'render.frame' ) || { width: 1280, height: 720 },
	};
	if ( ! glb ) notes.push( 'no glb in the manifest: test scene only' );
	return out;
}
