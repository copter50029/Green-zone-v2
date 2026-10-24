# Green-zone-v2 — Nike: green zone / heatmap / park verify

เพิ่มฟังก์ชัน Python สำหรับงาน Nike แยกจาก `grid.py` ของทีม ไม่มี frontend

## โครงสร้างและงานที่ทำแล้ว

| ไฟล์ | ทำอะไร |
| --- | --- |
| `grid.py` | โค้ดทีมเดิม: ตัด TIFF เป็นกริด 2000×2000 px และบันทึก `grid_index.csv` |
| `greensight/detect.py` | `detect_green()` ตรวจพิกเซลเข้าข่ายพืชด้วย band ratio |
| `greensight/heatmap.py` | `make_heatmap()` กรองกลุ่มเล็กกว่า 300 ตร.ม. และสร้างสีเขียวพร้อม halo ค่อย ๆ จาง |
| `greensight/park_verify.py` | `prepare_park_review()` เทียบหมุดทะเบียนกับภาพ; `record_park_review()` บันทึกการตรวจโดยคน |
| `run_nike.py` | ตัวอย่างเรียกฟังก์ชันครบชุดและบันทึกผลสำหรับ QGIS/เพื่อนทำ frontend |
| `data/parks15.geojson` | หมุดทะเบียน Greener Bangkok จาก snapshot 23 ต.ค. 2026 พร้อมที่มา |
| `tests/` | ทดสอบฟังก์ชันด้วยข้อมูลสังเคราะห์ |
| `docs/NIKE.md` | รายละเอียด input/output ข้อจำกัด และวิธีต่อกับงานทีม |

`Images/`, `Output/`, `.venv/` เป็นข้อมูล/ผลในเครื่อง ไม่ส่งขึ้น GitHub โค้ด Nike ไม่ต้องแก้ `grid.py`

## ติดตั้งและทดสอบ

Python 3.10 ขึ้นไป จาก root repository:

```powershell
python -m venv .venv                     # ข้ามถ้ามีแล้ว
.\.venv\Scripts\python.exe -m pip install -r requirements-nike.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## ใช้ฟังก์ชันสั้น ๆ

```python
import rasterio
from greensight import detect_green, make_heatmap

with rasterio.open("Output/grid_2000/tiles/tile_r7_c9.tif") as src:
    src_transform, src_crs = src.transform, src.crs
    mask = detect_green(
        src.read(), red_band=3, nir_band=4, nodata=src.nodata,
        valid_mask=(src.read_masks() != 0).all(axis=0),
    )
    result = make_heatmap(mask, pixel_m=src.res[0], min_area_m2=300, radius_m=50)

# result["mask"] = คลาสหลังกรองกลุ่มเล็ก
# result["rgba"] = สี uint8 ขนาด (height,width,4)
# result["stats"] = จำนวนกลุ่มและพื้นที่ ตร.ม.
```

**Band 3/4 ในตัวอย่างเป็นสมมติฐานทดลอง** metadata ของไฟล์ที่มีไม่บอกชื่อ band จึงยังไม่เรียกผลว่า NDVI ที่ยืนยันแล้ว ratio อย่างเดียวอาจตรวจติดหลังคา หากมี mask อาคาร/พื้นที่ส่วนตัวที่ตรวจแล้ว ให้ส่ง `exclude_mask=...` (bool บนกริดเดียวกัน) เข้า `detect_green()`

## รันทดลองกับ tile จริง

```powershell
.\.venv\Scripts\python.exe run_nike.py Output/grid_2000/tiles/tile_r7_c9.tif Output/nike-trial-01 --scene-id Theos00 --red-band 3 --nir-band 4 --imagery-date 2024-10-12
```

เลือก output ใหม่ทุกครั้ง โปรแกรมปฏิเสธการเขียนทับผลเดิม วันที่ภาพให้ใช้ข้อมูลผลิตภัณฑ์ที่ตรวจแล้ว ตัวอย่าง 2024-10-12 มาจากชื่อไฟล์ต้นฉบับเดิม ยังต้องยืนยัน metadata

ผล 4 ไฟล์: `candidate-mask.tif`, `heatmap.tif` (RGBA มีพิกัด), `summary.json`, `park-review.geojson` เปิด GeoTIFF/GeoJSON ใน QGIS ได้ เพื่อนนำผลไปแสดงต่อโดยเก็บ CRS/transform คู่กัน ตัวอย่างนี้ยังไม่ได้เพิ่ม HTTP API

ตัวอย่างจำกัด 25 ล้านพิกเซลเพื่อกันการอ่าน TIFF ใหญ่ทั้งภาพเข้าหน่วยความจำ ใช้ tile/crop ตรวจงานก่อน ผลบน tile มีขอบตัด ต้องรวม scene ก่อนสรุปพื้นที่จริงทั้งภาพ

## เทียบสวน 15 นาที

```python
import json
from greensight import prepare_park_review

with open("data/parks15.geojson", encoding="utf-8") as stream:
    parks = json.load(stream)

tasks = prepare_park_review(
    parks, result["mask"], src_transform, src_crs,
    scene_id="Theos00", search_radius_m=50,
    imagery_date="2024-10-12",
)
```

`src_transform` / `src_crs` ต้องมาจาก raster เดียวกับ mask หมุดนอกภาพหรือบน NoData ถูกแยกออกพร้อมเหตุผล ไม่ย้ายไปหาสีเขียว ทุกจุดเริ่ม `needs_review` การยืนยันชื่อ/ตำแหน่งและการเข้าถึงสาธารณะต้องมีผู้ตรวจและหลักฐาน ดู `record_park_review()` ใน [คู่มือ Nike](docs/NIKE.md)

ข้อมูลอ้างอิง: [แผนที่สวน Greener Bangkok](https://greener.bangkok.go.th/en/green-space/15-minute-garden/#map-15min-garden) ชุดที่แนบเป็น snapshot 23 ต.ค. 2026: 530 รายการ ใช้พิกัดได้ 528 รายการ ไม่ใช่การรับรองสถานะปัจจุบัน

## ต่อกับกริดของทีม

1. `grid_cut()` ตัดภาพ โดยตั้ง output แยก `Theos00`, `Theos01`, `Theos02` เพื่อไม่ให้ tile ชื่อซ้ำทับกัน
2. `detect_green()` ทำทีละ tile/window และเก็บ transform ของแต่ละชิ้น
3. รวม core mask กลับกริด scene เดิมก่อน `make_heatmap()` เพื่อไม่ตัดกลุ่ม 300 ตร.ม. ที่พาดขอบ tile
4. `prepare_park_review()` สร้างงานตรวจจากทะเบียน; คนตรวจจึงบันทึกผลผ่าน `record_park_review()`

`grid.py` เดิมข้าม partial edge tiles เป็นค่าเริ่มต้น และประเมิน valid fraction แบบ sampling band เดียว หากต้องเก็บขอบภาพใช้ `grid_cut(..., keep_partial=True)` ฟังก์ชัน detect ตรวจ NoData ครบทุก band อีกครั้ง โค้ดตัดกริดไม่ได้เป็น sliding-window inference ที่มี halo/overlap แล้วรวมผล

## Branch และส่งให้เพื่อน review

งาน Nike อยู่ `nike/green-zone-functions` ส่งเฉพาะไฟล์งานนี้ขึ้น branch แล้วเปิด PR เข้า `main` เก็บการแก้ชื่อภาพใน `grid.py` ที่มีอยู่ในเครื่องเป็นงานแยก ไม่ commit TIFF, Output หรือ .venv

ระบบนี้ให้ **candidate vegetation และข้อมูลช่วยตรวจสวน** ยังไม่มี labels ตรวจโดยคนหรือค่า accuracy จริง และยังไม่ยืนยันว่าตัดหลังคา/ต้นไม้ในบ้านออกได้ทั้งหมด
