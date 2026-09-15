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
	const glbRaw = pick( raw, 'glb', 'files.glb', 'model' );
	const glb = resolveUrl( baseUrl, typeof glbRaw === 'string' ? glbRaw : ( glbRaw?.path || glbRaw?.url ) );

	// --- stations ------------------------------------------------------------------------------
	// schema pfa-phase6-gate0/1 keys stations by camera name with lens_mm / rotation_euler_xyz;
	// older/array shapes are accepted too.  Look-at targets are not in the manifest, so they are
	// taken from scripts/qa_cameras.py (stations_blender.json) by name purely as a cross-check.
	let rawStations = pick( raw, 'stations', 'cameras' );
	let stationList;
	if ( rawStations && ! Array.isArray( rawStations ) ) {
		stationList = Object.entries( rawStations ).map( ( [ name, s ], i ) => ( { name, index: s.index ?? i + 1, ...s } ) );
	} else if ( rawStations && rawStations.length ) {
		stationList = rawStations.map( ( s, i ) => ( { index: s.index ?? i + 1, ...s } ) );
	} else {
		stationList = stationsFallback.stations;
		notes.push( 'stations: manifest had none, using scripts/qa_cameras.py fallback' );
	}
	const byName = new Map( stationsFallback.stations.map( s => [ s.name, s ] ) );
	const stations = stationList.map( ( s, i ) => {
		const ref = byName.get( s.name );
		return {
			index: s.index ?? i + 1,
			name: s.name ?? `station_${i + 1}`,
			location: s.location ?? s.loc,
			target: s.target ?? ref?.target ?? null,
			rotation_euler: s.rotation_euler_xyz ?? s.rotation_euler ?? s.rotation ?? null,
			matrix_world: s.matrix_world ?? s.matrix ?? null,
			lens: s.lens_mm ?? s.lens ?? 35,
			sensor_width: s.sensor_width_mm ?? s.sensor_width ?? 36,
			sensor_fit: s.sensor_fit ?? 'HORIZONTAL',
			shift_x: s.shift_x ?? 0,
			shift_y: s.shift_y ?? 0,
			clip_start: s.clip_start ?? 0.1,
			clip_end: s.clip_end ?? 5000,
			reference_photo: s.reference_photo ?? ref?.ref ?? null,
		};
	} );

	// --- colour --------------------------------------------------------------------------------
	const lutRaw = pick( raw, 'lut', 'colour.lut', 'color.lut' );
	const sh = ( typeof lutRaw === 'object' && lutRaw && typeof lutRaw.shaper === 'object' ) ? lutRaw.shaper : null;
	const lut = lutRaw ? {
		url: resolveUrl( baseUrl, typeof lutRaw === 'string' ? lutRaw : ( lutRaw.url || lutRaw.path || lutRaw.file ) ),
		size: ( typeof lutRaw === 'object' && ( lutRaw.size ?? lutRaw.lut_size ) ) || null,
		// schema pfa-phase6-gate0/1: lut.shaper = { min_ev, max_ev, pivot } means an AgX log2 shaper
		shaper: sh ? 'log2' : ( ( typeof lutRaw === 'object' && typeof lutRaw.shaper === 'string' ) ? lutRaw.shaper : null ),
		shaperMin: sh ? sh.min_ev : ( ( typeof lutRaw === 'object' && ( lutRaw.shaper_min ?? lutRaw.shaperMin ) ) ?? undefined ),
		shaperMax: sh ? sh.max_ev : ( ( typeof lutRaw === 'object' && ( lutRaw.shaper_max ?? lutRaw.shaperMax ) ) ?? undefined ),
		shaperPivot: sh ? ( sh.pivot ?? 0.18 ) : undefined,
		exposureOwner: ( typeof lutRaw === 'object' && lutRaw.exposure_applied_by ) || null,
	} : null;
	if ( ! lut ) notes.push( 'no LUT in the manifest: the display pass falls back to gamma 2.2 (NOT the Phase 5 look)' );

	// Exposure.  export/bake_lut.py pushes the identity Hald through Blender's OWN view transform AT
	// the scene's exposure, so a LUT from that bake ALREADY contains -2.833 EV and the pass multiplier
	// must stay 1.0.  An explicit exposure_multiplier wins; `includes_exposure: false` switches to 2^EV.
	let exposure = pick( raw, 'exposure_multiplier', 'exposure_scale', 'colour.exposure_multiplier', 'view.exposure_multiplier' );
	const ev = pick( raw, 'exposure_ev', 'view.exposure_ev', 'exposure', 'view.exposure', 'colour.exposure' );
	const lutHasExposure = pick( raw, 'lut.includes_exposure', 'view.lut.includes_exposure', 'colour.lut.includes_exposure' );
	if ( exposure === undefined ) {
		if ( lut && /viewer/i.test( lut.exposureOwner || '' ) && ev !== undefined ) {
			exposure = Math.pow( 2, ev );
			notes.push( `exposure: the LUT says exposure_applied_by "${lut.exposureOwner}", multiplier 2^${ev.toFixed( 4 )} = ${Math.pow( 2, ev ).toFixed( 5 )}` );
		} else if ( lutHasExposure === false && ev !== undefined ) { exposure = Math.pow( 2, ev ); notes.push( `exposure: LUT declares includes_exposure false, multiplier 2^${ev} = ${Math.pow( 2, ev ).toFixed( 5 )}` ); }
		else if ( lut ) { exposure = 1.0; notes.push( `exposure: multiplier 1.0 (the LUT carries the ${ev !== undefined ? ev.toFixed( 3 ) : '-2.833'} EV exposure)` ); }
		else if ( ev !== undefined ) { exposure = Math.pow( 2, ev ); notes.push( `exposure: no LUT, gamma fallback gets 2^${ev.toFixed( 3 )} = ${Math.pow( 2, ev ).toFixed( 5 )}` ); }
		else { exposure = 1.0; notes.push( 'exposure: absent, multiplier = 1' ); }
	}

	// --- sky -----------------------------------------------------------------------------------
	const sky = pick( raw, 'sky', 'world', 'environment' ) || {};
	// schema pfa-phase6-gate0/1: sky.camera / sky.glossy are objects { exr, hdr }.  The .hdr (RGBE) is
	// used: 3.6 MB vs 32 MB and enough range for a background and a PMREM source.
	const skyFile = ( v ) => ( typeof v === 'string' ? v : ( v && ( v.hdr || v.exr ) ) );
	const skyCamera = resolveUrl( baseUrl, skyFile( pick( sky, 'camera', 'background', 'camera_hdr', 'camera_exr' ) ) );
	const skyGlossy = resolveUrl( baseUrl, skyFile( pick( sky, 'glossy', 'specular', 'glossy_hdr', 'glossy_exr' ) ) );
	// Blender/manifest mapping: u = 0.5 + atan2(bx, by)/360.  With three (X,Y,Z) = blender (x, z, -y)
	// that is three's atan2(Z,X) + 90 deg, so the manifest's u is three's u + 0.25 and the environment
	// needs a quarter turn about Y.  three's backgroundRotation applies the INVERSE sense, so the value
	// is +90, measured: a sweep of 0 / 90 / 180 / -90 against the Cycles reference frame gives
	// mean |delta| over five sky boxes of 33.1 / 1.5 / 19.0 / 21.4 of 255.
	const skyRotationDeg = def( pick( sky, 'rotation_deg', 'rotation' ), 90,
		'sky.rotation_deg (+90 about Y; measured against the Cycles frame, 1.5/255)' );

	// --- sun (specular only; the diffuse is in the lightmaps) ----------------------------------
	// The manifest's `direction_blender` / `direction_gltf` is the direction the light TRAVELS, so the
	// DirectionalLight is placed at -direction * d.  An azimuth/elevation pair instead points TOWARD
	// the sun, so the light is placed at +direction * d.
	const sunRaw = pick( raw, 'sun', 'light.sun' ) || {};
	let toSunBlender = null;
	const travel = pick( sunRaw, 'direction_blender', 'direction', 'vector', 'dir' );
	const az = pick( sunRaw, 'azimuth', 'azimuth_deg' ), el = pick( sunRaw, 'elevation', 'elevation_deg' );
	if ( travel ) { toSunBlender = travel.map( v => - v ); notes.push( `sun: travel direction [${travel.map( v => v.toFixed( 3 ) )}] -> light placed opposite` ); }
	else if ( az !== undefined && el !== undefined ) {
		// scripts/common.sun_direction: azimuth clockwise from north, -X = north, +Y = east
		const a = az * Math.PI / 180, e = el * Math.PI / 180;
		toSunBlender = [ - Math.cos( a ) * Math.cos( e ), Math.sin( a ) * Math.cos( e ), Math.sin( e ) ];
		notes.push( `sun: direction from azimuth ${az} / elevation ${el}` );
	} else {
		const a = 118.5 * Math.PI / 180, e = 7.36 * Math.PI / 180;
		toSunBlender = [ - Math.cos( a ) * Math.cos( e ), Math.sin( a ) * Math.cos( e ), Math.sin( e ) ];
		notes.push( 'sun: absent, using the Phase 5 world (az 118.5, el 7.36)' );
	}
	const sun = {
		toSunBlender,
		irradiance: def( pick( sunRaw, 'energy_w_m2', 'irradiance', 'strength', 'energy' ), 67.3, 'sun.irradiance (W/m2, Phase 5 LIGHT_sun)' ),
		color: pick( sunRaw, 'color', 'colour' ) || [ 1, 1, 1 ],
		angleDeg: pick( sunRaw, 'angle_deg' ) ?? ( pick( sunRaw, 'angle_rad' ) !== undefined ? pick( sunRaw, 'angle_rad' ) * 180 / Math.PI : 0.526 ),
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
	const assetsRaw = pick( raw, 'assets' ) || [];
	const assetList = Array.isArray( assetsRaw )
		? assetsRaw : Object.entries( assetsRaw ).map( ( [ name, a ] ) => ( { name, ...a } ) );
	for ( const a of assetList ) {
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

	// RGBM range used by every lightmap in the schema (textures.*.rgbm_range)
	let rgbmRange = 7.0;
	for ( const [ k, v ] of Object.entries( pick( raw, 'textures' ) || {} ) ) {
		if ( k.includes( 'lightmap' ) && v && v.rgbm_range ) { rgbmRange = v.rgbm_range; break; }
	}

	const out = {
		raw, baseUrl, glb, stations, lut, exposure, sun, lightmaps, notes, rgbmRange,
		waterZ: def( pick( raw, 'water.viewer_y', 'water.water_z', 'water_z', 'waterZ', 'scene.water_z' ), WATER_Z, 'water_z' ),
		sky: { camera: skyCamera, glossy: skyGlossy, rotationDeg: skyRotationDeg },
		frameSize: pick( raw, 'frame', 'render.frame' ) || { width: 1280, height: 720 },
	};
	if ( ! glb ) notes.push( 'no glb in the manifest: test scene only' );
	return out;
}
