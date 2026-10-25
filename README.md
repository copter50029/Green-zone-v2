# Green-zone-v2 — งาน Nike

Backend Python สำหรับ **detect green zone → heatmap → park verify** แยกจาก `grid.py` ของทีม โค้ดฐานของเพื่อนยังอยู่เดิม

## ใช้งานเร็ว

```powershell
# จาก root repository; ต้องมี Python 3.10+
.\.venv\Scripts\python.exe -m pip install -r requirements-nike.txt
.\.venv\Scripts\python.exe run_nike.py --all --output Output/nike-new-run
```

ตั้ง 3 ภาพและข้อมูลประกอบใน `data/scenes.json` เลือก output ใหม่ทุกครั้ง ไม่เขียนทับผลเดิม ไม่ต้องติดตั้ง frontend

เปิด `Output/nike-new-run/index.html` ดูภาพเปรียบเทียบ หรือเปิด GeoTIFF/GeoJSON ใน QGIS

## ฟังก์ชันหลัก

| ฟังก์ชัน | ใช้ทำอะไร |
| --- | --- |
| `detect_green(bands, red_band=3, nir_band=4, ...)` | ตรวจ candidate พืชทีละ array/window |
| `make_heatmap(mask, pixel_m, ...)` | เก็บกลุ่ม ≥300 ตร.ม. และสร้างสีเขียวพร้อม halo จาง |
| `analyse_scene(tif_path, out_dir, ...)` | ทำทั้งภาพด้วย window เก็บขอบครบ รวมก่อนกรองกลุ่ม |
| `prepare_park_review(registry, mask, transform, crs, ...)` | เทียบหมุดทะเบียนกับภาพ สร้างงานรอตรวจ |
| `record_park_review(task, ...)` | บันทึกผู้ตรวจและหลักฐานตำแหน่ง/การเข้าถึง |
| `evaluate_mask(mask, references, transform, crs, target=...)` | ประเมินเฉพาะ labels ที่ตรวจแล้ว ถ้าไม่มีคืนสถานะรอข้อมูล |

```python
from greensight import analyse_scene

summary = analyse_scene(
    "Images/Theos00.tif", "Output/my-scene-run",
    scene_id="Theos00", red_band=3, nir_band=4,
    registry_path="data/parks15.geojson",
    context_path="data/exclusions/Theos00.geojson",
    imagery_date="2024-10-12",
)
```

หรือเรียก `from run_nike import run_all; run_all(out_dir="Output/my-three-scenes")`

## ใช้ array สั้น ๆ กับงานของเพื่อน

```python
from greensight import detect_green, make_heatmap

mask = detect_green(bands, red_band=3, nir_band=4,
                    nodata=65535, valid_mask=valid, exclude_mask=excluded)
result = make_heatmap(mask, pixel_m=0.5, min_area_m2=300, radius_m=50)
# result["mask"], result["rgba"], result["stats"]
```

`bands` = numpy `(bands,height,width)`; `valid` / `excluded` เป็น bool บนกริดเดียวกัน ถ้าไม่มี exclusion ไม่ต้องใส่พารามิเตอร์นี้ mask codes: `0=other, 1=candidate, 2=uncertain, 255=NoData`

เมื่อทำเองทีละ tile ต้องรวมกลับ scene ก่อน `make_heatmap()` ส่วน `analyse_scene()` รวมให้แล้ว ไม่พึ่ง tile ที่ `grid.py` อาจข้ามขอบไว้

## ผลต่อภาพ

| ไฟล์ | ความหมาย |
| --- | --- |
| `raw-mask.tif` | ผล ratio บนกริดต้นฉบับเต็ม รวม NoData |
| `candidate-mask.tif` | หลัง exclusions และกรองกลุ่ม บน native grid ตัดเฉพาะกรอบ NoData ภายนอก |
| `heatmap.tif` | RGBA มีพิกัด พร้อม alpha โปร่งใส |
| `source.png`, `heatmap.png` | ภาพย่อสำหรับรายงาน ไม่ใช่ข้อมูลวิเคราะห์ |
| `park-review.geojson` | หมุดทะเบียนที่อยู่บนข้อมูลภาพจริง พร้อม metrics และสถานะรอตรวจ |
| `summary.json`, `status.json` | พื้นที่ counts hashes window/grid และสถานะรัน |

## ข้อมูลและข้อจำกัดที่ต้องรู้

- ใช้ภาพ GISTDA ทั้ง 3 TIFF เป็นหลัก ไม่รวมยอดสามภาพเป็นพื้นที่สวนทั้งเขต
- อ่าน 512×512 พิกเซล เก็บ partial edges และนับพิกเซลครั้งเดียว กรองกลุ่ม 4 ทิศทั้งภาพแล้วจึงสร้างระยะ
- ตัด polygon อาคารพร้อม buffer 2 เมตร พื้นที่ residential และ access=private/no/customers/permit จาก **OSM snapshot ในเครื่อง** ซึ่งอาจไม่ครบ/คนละปีกับภาพ การตัด residential อาจตัดพืชสาธารณะใน polygon นั้นด้วย จึงยังไม่รับรองว่ากำจัดหลังคา/ต้นไม้ในบ้านได้ทั้งหมด
- ข้อมูล OSM ครอบคลุมกรอบศึกษาเดิม พื้นที่ภาพที่เลยกรอบนั้นรายงานใน `valid_area_outside_context_coverage_m2` และยังไม่มีข้อมูล exclusions ครบ ห้ามถือว่าเป็นพื้นที่สาธารณะที่ยืนยันแล้ว
- [เอกสาร ESRI](https://doc.esri.com/en/arcgis-pro/latest/help/data/imagery/satellite-sensor-raster-types.html) สนับสนุนลำดับ THEOS-2 มาตรฐาน Blue/Green/Red/NIR แต่ไฟล์ที่มีไม่ยืนยัน identity/calibration เฉพาะไฟล์ จึงยังใช้ **experimental raw-band ratio**
- ทะเบียน [Greener Bangkok](https://greener.bangkok.go.th/en/green-space/15-minute-garden/#map-15min-garden) เป็น snapshot 23 ต.ค. 2026 จำนวน 528 พิกัดใช้ได้จาก 530 รายการ ไม่ใช่ขอบสวน ทางเข้าหรือสถานะเปิดปัจจุบัน
- ไม่มี labels ตรวจแล้วจึง `real_accuracy=null` และไม่สร้างโมเดล/ตัวเลขความแม่นยำปลอม

## โฟลเดอร์และการตรวจงาน

`greensight/` ฟังก์ชัน · `data/` ค่าตั้งและ snapshots · `tests/` ทดสอบ · `docs/` คู่มือ/วิธีทดลอง · `Images/` และ `Output/` ข้อมูลในเครื่อง ไม่ commit

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

[คู่มือ input/output](docs/NIKE.md) · [วิธีประมวลผลและผลตรวจสามภาพ](docs/FULL-SCENE-METHODS-th.md) · [ประวัติงาน](docs/WORKLOG.md)

ทำงานเฉพาะในเครื่องบน `nike/green-zone-functions` ตามที่ตกลง ยังไม่ push หรือเปิด PR

## Labels จากต้นฉบับ

เพิ่มชุดตีความจากภาพจริงทั้งสามภาพ พร้อม `validate_labels()` ตรวจกริด/NoData/การซ้อน/ระยะ train-test และกัน uncertain ออกจากจำนวนใช้งาน ดู [วิธีและข้อจำกัด](docs/LABELS-th.md) ชุดนี้เป็น assistant visual labels ที่รอคนตรวจ ไม่ใช่ ground truth สำหรับอ้าง accuracy

## ส่งให้เพื่อนทำ frontend / ตรวจ labels

เรียก `export_frontend(run_dir, out_dir)` ได้ชุด PNG ที่จัดพิกัดสำหรับแผนที่เว็บ, GeoJSON และ manifest เดียว พร้อม `prepare_label_review()` / `apply_label_review()` สำหรับเก็บคำตอบตรวจโดยคนโดยไม่แก้ labels เดิม ดู [คู่มือส่งต่อพร้อมตัวอย่าง](docs/FRONTEND-HANDOFF-th.md)
