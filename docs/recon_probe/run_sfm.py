import pycolmap as p, time, os, json, sys
W=os.path.dirname(os.path.abspath(__file__)); db=f"{W}/database.db"; out=f"{W}/sparse"
os.makedirs(out,exist_ok=True); T={}
stage=sys.argv[1] if len(sys.argv)>1 else "all"
if stage in("all","extract"):
    if os.path.exists(db): os.remove(db)
    t=time.time(); eo=p.FeatureExtractionOptions(); eo.use_gpu=False; eo.max_image_size=1600
    ro=p.ImageReaderOptions(); ro.camera_model="SIMPLE_RADIAL"
    p.extract_features(db,f"{W}/images",camera_mode=p.CameraMode.PER_IMAGE,reader_options=ro,extraction_options=eo,device=p.Device.cpu)
    T['extract']=time.time()-t; print("extract",T['extract'],flush=True)
if stage in("all","match"):
    t=time.time(); mo=p.FeatureMatchingOptions(); mo.use_gpu=False
    p.match_exhaustive(db,matching_options=mo,device=p.Device.cpu)
    T['match']=time.time()-t; print("match",T['match'],flush=True)
if stage in("all","map"):
    t=time.time(); o=p.IncrementalPipelineOptions(); o.max_runtime_seconds=2400; o.min_model_size=3
    recs=p.incremental_mapping(db,f"{W}/images",out,o)
    T['map']=time.time()-t; print("map",T['map'],len(recs),flush=True)
json.dump(T,open(f"{W}/timings_{stage}.json","w"))
