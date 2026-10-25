import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from greensight.scene import analyse_scene,write_json,read_json
from greensight.handoff import export_frontend
from greensight.label_review import prepare_label_review,apply_label_review


class HandoffTests(unittest.TestCase):
    def test_projected_export_bounds_alpha_and_read_only_source(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); run=root/'run'
            data=np.ones((4,40,60),dtype='uint16')*100
            data[3,10:30,10:40]=300
            data[:,:3,:]=65535
            with rasterio.open(root/'source.tif','w',driver='GTiff',width=60,height=40,count=4,dtype='uint16',nodata=65535,crs='EPSG:32647',transform=from_origin(670000,1540000,1,1)) as dst:
                dst.write(data)
            summary=analyse_scene(root/'source.tif',run/'test',scene_id='test',red_band=3,nir_band=4)
            write_json(run/'summary-all.json',[summary])
            original=(run/'test/summary.json').read_bytes()
            exported=export_frontend(run,root/'web',max_size=100)
            entry=exported['scenes'][0]
            self.assertEqual(entry['candidate_area_m2'],summary['stats']['retainedCandidateAreaM2'])
            self.assertIsNone(entry['real_accuracy'])
            self.assertEqual(entry['verified_parks'],0)
            with rasterio.open(run/'test/heatmap.tif') as src:
                expected=transform_bounds(src.crs,'EPSG:4326',*src.bounds)
            np.testing.assert_allclose(entry['bounds_wgs84'],expected,atol=1e-6)
            for layer in ('source','heatmap'):
                with rasterio.open(root/f'web/test/{layer}.png') as img:
                    self.assertEqual(img.count,4)
                    self.assertEqual(max(img.width,img.height),100)
                    self.assertGreater(img.read(4).max(),0)
            self.assertEqual(original,(run/'test/summary.json').read_bytes())
            self.assertEqual(read_json(root/'web/test/parks.geojson')['features'],[])
            with self.assertRaises(FileExistsError):
                export_frontend(run,root/'web')
            with (run/'test/source.png').open('ab') as stream: stream.write(b'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                export_frontend(run,root/'tampered')
            self.assertFalse((root/'tampered').exists())

    def test_incomplete_run_never_exported(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            write_json(root/'summary-all.json',[{'scene_id':'a'}])
            (root/'a').mkdir()
            write_json(root/'a/status.json',{'status':'processing'})
            with self.assertRaisesRegex(ValueError,'completed'):
                export_frontend(root,root/'web')


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.labels={'target':'vegetation','features':[{'id':'a','geometry':{'type':'Polygon','coordinates':[]},
            'properties':{'scene_id':'s','source_window':[1,1,2,2],'source_crop':'s-01','class':'positive','split':'test','origin':'assistant_visual'}}]}

    def test_blank_queue_cannot_create_human_references(self):
        queue=prepare_label_review(self.labels)
        reviewed=apply_label_review(self.labels,queue)
        self.assertTrue(all(not v['features'] for v in reviewed.values()))

    def test_explicit_correction_keeps_original_and_test_split(self):
        original=copy.deepcopy(self.labels)
        queue=prepare_label_review(self.labels)
        queue['decisions'][0].update({'class':'negative','reviewer':'Test reviewer','reviewed_on':'2026-10-25','notes':'Fixture correction'})
        result=apply_label_review(self.labels,queue)
        self.assertEqual(self.labels,original)
        feature=result['test']['features'][0]
        self.assertEqual(feature['properties']['class'],'negative')
        self.assertEqual(feature['properties']['origin'],'human')
        self.assertEqual(feature['properties']['assistant_source']['class'],'positive')
        self.assertFalse(result['train']['features'])

    def test_missing_evidence_duplicate_unknown_and_uncertain(self):
        queue=prepare_label_review(self.labels)
        queue['decisions'][0]['class']='negative'
        with self.assertRaises(ValueError): apply_label_review(self.labels,queue)
        queue=prepare_label_review(self.labels)
        queue['decisions'].append(copy.deepcopy(queue['decisions'][0]))
        with self.assertRaises(ValueError): apply_label_review(self.labels,queue)
        queue['decisions']=[{'label_id':'unknown','class':None}]
        with self.assertRaises(ValueError): apply_label_review(self.labels,queue)
        queue=prepare_label_review(self.labels)
        queue['decisions'][0].update({'class':'uncertain','reviewer':'Test reviewer','reviewed_on':'2026-10-25','notes':'Unresolved'})
        self.assertFalse(apply_label_review(self.labels,queue)['test']['features'])
