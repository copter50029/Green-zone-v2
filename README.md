# Green-zone-v2 — งาน Nike

Backend Python สำหรับ **ตรวจพื้นที่สีเขียว → คัดบริบทบ้าน/จุดเล็ก → heatmap → เทียบทะเบียนสวน** ใช้ TIFF ของทีมทั้ง 3 ภาพ โค้ดงาน Nike แยกใน `greensight/` และคง `grid.py` ของเพื่อนไว้

## ผลล่าสุดที่ตรวจแล้ว — 25 ตุลาคม 2569

| ภาพ | Candidate ผลหลัก (ตร.ม.) | แยกชั้นรอตรวจ (ตร.ม.) | กลุ่มผลหลัก |
| --- | ---: | ---: | ---: |
| Theos00 | 160,152.75 | 180,615.50 | 104 |
| Theos01 | 2,161,651.25 | 0.00 | 622 |
| Theos02 | 305,740.00 | 0.00 | 195 |

**ผลหลักยังเป็นพื้นที่เข้าข่าย ไม่ใช่สวนสาธารณะที่ยืนยันแล้ว** พื้นที่รอตรวจไม่รวมยอดหลัก ชั้นรอตรวจว่างหมายถึงยังไม่ได้ระบุกรอบประเภทนั้นในภาพ ไม่ยืนยันว่าไม่มีพื้นที่จำกัดสิทธิ ภาพต่างตำแหน่ง/วันที่จึงไม่รวมเป็นยอดสวนทั้งเขต

ผลในเครื่องที่ควรใช้ต่อ:

- [หน้ารวมภาพ/ชั้นรอตรวจ/หลักฐาน](Output/reviewed-final-report-20261025/index.html)
- [ภาพรวมทั้งสามภาพ](Output/reviewed-final-report-20261025/all-scenes.png)
- [ผลตรวจครบสามภาพ](Output/nike-reviewed-final-20261025/audit-all.json)
- [Manifest ส่งต่อ frontend](Output/frontend-reviewed-20261025/manifest.json)
- ชุดส่งต่อ `Output/frontend-reviewed-20261025.zip`

`Output/` และ `Images/` อยู่เฉพาะเครื่องและถูก ignore ใน Git เพื่อนต้องมี TIFF/ผลส่งต่อของตัวเอง ลิงก์ผลข้างต้นจึงเปิดไม่ได้บน GitHub ที่ไม่มีไฟล์เหล่านี้ รายละเอียดวิธีและข้อจำกัดอ่านได้ใน [FULL-AUDIT-th.md](docs/FULL-AUDIT-th.md)

## เริ่มใช้งาน

Python 3.10+ จาก root repository:

```powershell
# ครั้งแรก หากยังไม่มี .venv
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-nike.txt

# ประมวลผลครบสามภาพ เลือกชื่อ output ที่ยังไม่มี
.\.venv\Scripts\python.exe run_nike.py --all --output Output/my-reviewed-run
```

วาง `Theos00.tif`, `Theos01.tif`, `Theos02.tif` ใน `Images/` แล้วตรวจ paths/bands/context/policy ใน `data/scenes.json` ไม่เขียนทับผลเก่า ไม่ต้องติดตั้ง frontend หรือมี API key เพื่อรันขั้นตอนนี้

เรียกเป็นฟังก์ชันได้สั้นๆ:

```python
from run_nike import run_all
from greensight import export_frontend

results = run_all(out_dir='Output/my-reviewed-run')
manifest = export_frontend('Output/my-reviewed-run', 'Output/my-web-package')
```

## ขั้นตอนคัดพื้นที่

1. อ่าน TIFF ทีละ 512×512 รวมขอบ window ให้ครบ ตรวจ NoData ทุก band และรวม mask ทั้งภาพก่อนกรองกลุ่ม
2. ใช้ raw-band ratio ทดลอง โดยสมมติ RED=3/NIR=4; ไม่อ้างว่าเป็น reflectance NDVI ที่ยืนยัน calibration แล้ว
3. คัดอาคารพร้อม buffer 8 เมตร บ้านที่มีข้อมูล 20 เมตร เขต residential 10 เมตร และ private-access polygons จาก OSM snapshot
4. ใช้กรอบภาพที่ตรวจบริบทบ้านเพิ่ม: 86 เซลล์ตรวจ 250×250 เมตร พร้อมกรอบกรณีที่ผู้ใช้ชี้ใต้สนามบิน ขอบเซลล์เป็นการคัดแบบเข้ม ไม่ใช่ขอบกรรมสิทธิ์ อาจตัดพืชส่วนรวมใกล้บ้านด้วย
5. ตัดเส้นบางด้วย disk opening รัศมี 3 เมตร แล้วกรองกลุ่ม 4 ทิศที่พื้นที่อย่างน้อย 300 ตร.ม. ไม่เติมพืชเพิ่ม
6. ตามนโยบายผู้ใช้ แยกบริเวณสนามบิน/แนวรางที่ระบุไว้เป็นชั้นรอตรวจ และกรองขนาดกลุ่มผลหลักซ้ำหลังแบ่งพื้นที่
7. ตัดทั้งสีเขียวและ halo ออกจากบริเวณบ้าน/กรอบที่กันไว้ สีแดงจางคือระยะเส้นตรงรอบพืช ไม่ใช่ความร้อนหรือระยะเดิน
8. เก็บสนามกีฬา/พื้นที่ร่วมของโรงเรียน วัด รีสอร์ต หรือโครงการจัดสรรเป็น candidate เมื่อไม่ถูกคัดด้วยหลักฐานบริบทที่มี พร้อมสถานะยังไม่ยืนยันการเข้าใช้ตามคำตอบผู้ใช้

## ฟังก์ชันที่เพื่อนเรียกใช้

| ฟังก์ชัน | งาน / input-output |
| --- | --- |
| `detect_green(bands, red_band=3, nir_band=4, ...)` | numpy `(bands,height,width)` → class mask |
| `make_heatmap(mask, pixel_m, clean_radius_m=3, ...)` | mask → mask กรองแล้ว, RGBA และ stats |
| `analyse_scene(tif_path, out_dir, ...)` | TIFF ทั้งภาพ → GeoTIFF/PNG/GeoJSON/summary; ใช้ policy ผ่าน kwargs |
| `clean_saved_results(run_dir, out_dir, ...)` | คัดผลที่บันทึกแล้วพร้อมตรวจ parent hashes; ไม่อ่าน radiometry ใหม่ |
| `export_frontend(run_dir, out_dir)` | ผลครบ scene → PNG EPSG:3857, GeoJSON และ manifest |
| `prepare_park_review(...)` / `record_park_review(...)` | เตรียมงานตรวจสวน / บันทึกหลักฐานการตรวจ |
| `validate_labels(...)` | ตรวจกริด ที่มา การซ้อนและระยะห่างของ assistant vegetation labels |
| `prepare_label_review(...)` / `apply_label_review(...)` | คิวคำตอบว่าง → คำตอบจากผู้ตรวจ แยก train/validation/test |
| `evaluate_mask(...)` | ประเมินได้เมื่อมี human-reviewed test references ที่ตรง target |
| `greensight.audit.audit_scene(...)` | ตรวจ source ทุก window, hashes, exclusions, พื้นที่และทุก component |

Library defaults บางตัวคงค่าเดิมเพื่อรองรับโค้ดเพื่อน การใช้ `run_all()` จะอ่านเกณฑ์ล่าสุดจาก config ครบ หากเรียก `analyse_scene()` เองต้องส่ง buffers และ policy paths ตาม config

Mask codes: `0=other`, `1=candidate`, `2=uncertain`, `255=NoData` ห้ามเรียก `make_heatmap()` แยกแต่ละ tile แล้วนำพื้นที่มาบวก ต้องรวมกลับ scene ก่อน

## ไฟล์ผลและการต่อ frontend

| ไฟล์ต่อภาพ | ความหมาย |
| --- | --- |
| `raw-mask.tif` | ผล ratio บนกริด TIFF เต็ม |
| `candidate-mask.tif` | ผลหลักหลังคัดพื้นที่และแยก pending บน native grid |
| `heatmap.tif` / `heatmap.png` | RGBA มีพิกัด / ภาพย่อผสม RGB สำหรับดู |
| `pending-mask.tif` / `pending.tif` | candidate ที่แยกรอตรวจ / RGBA สีเหลือง ไม่รวมผลหลัก |
| `park-review.geojson` | หมุดทะเบียนในข้อมูลภาพ ไม่ใช่ขอบสวนหรือทางเข้า |
| `summary.json`, `status.json` | พื้นที่ ค่าตั้ง provenance hashes และสถานะรัน |
| `audit.json`, `patch-review-catalog.json` | ผลตรวจและรายการทุกกลุ่มที่เหลือ ซึ่งยังต้องตรวจความหมายจริง |
| `code-used/`, `inputs/` ในชุดตรวจล่าสุด | สำเนาโค้ดตาม hashes และข้อมูลตั้งต้นสำหรับตรวจย้อนกลับ |

เพื่อนนำไฟล์ในชุด web package ไปวางใน static assets เช่น `public/nike/` อ่าน `manifest.json` ผ่าน HTTP ของ frontend แต่ละ scene มี `source`, `heatmap`, `parks` และ optional `pending` พร้อม `bounds_wgs84=[west,south,east,north]` ภาพ PNG แปลง EPSG:3857 แล้ว ใช้ bounds เดียวกันทุกชั้น

อ่านพื้นที่จาก `candidate_area_m2` ไม่วัดจาก PNG และไม่บวก `pending_area_m2` เมื่อ `pending_in_main_total=false` ตั้งสวิตช์แยกชื่อ “รอตรวจ — ไม่รวมยอดหลัก” ดูตัวอย่างเชื่อมใน [FRONTEND-HANDOFF-th.md](docs/FRONTEND-HANDOFF-th.md) ภาพย่อเหมาะกับภาพรวม งานดูละเอียดใช้ native GeoTIFF/QGIS หรือระบบ tiles ของทีม

## หลักฐานการตรวจและสิ่งที่ยังไม่รับรอง

- การรันสำเร็จล่าสุด: Tests 46 ข้อผ่าน รวม native grid, window edges, noise, house exclusions, halo, pending, export และ park-review guards
- ตรวจ source ทุก window รวม 1,668,988,808 พิกเซล (รวม NoData); valid จริง 108,000,000 พิกเซล ตรวจกลุ่มผลหลักครบ 921 กลุ่ม ทุกกลุ่ม ≥300 ตร.ม.
- ตรวจภาพย่อยครบ 432 ช่องที่ระดับ contact sheet; เก็บการตัดสินใจใน `data/labels/visual-cell-review.json` เป็น assistant interpretation ไม่ใช่ผู้ตรวจภาคสนาม
- Vegetation labels 42 กรอบ: ผู้ช่วยตีความชัด 34, uncertain 8; human-reviewed ยัง 0 เก็บแยกจาก policy exclusions และไม่ใช้เป็น accuracy จริง
- ยังไม่มีโมเดลที่ฝึกกับ human labels จริง ไม่รับรองว่าตัดหลังคา/ต้นไม้ในบ้านได้ทั้งหมด ข้อมูลบ้านอาจไม่ครบ และพื้นที่ที่เหลือไม่ได้ยืนยันสิทธิ/การเข้าถึงสวน
- Band order มีข้อมูลมาตรฐานประกอบ แต่ calibration/identity เฉพาะ TIFF และวันที่จาก metadata ยังไม่ยืนยันครบ
- Greener Bangkok เป็น snapshot ในเครื่อง: 528 พิกัดใช้ได้จาก 530 รายการ ไม่ใช่สถานะปัจจุบัน พบ 2 หมุดใน Theos00; ภาพอื่นไม่มีหมุดจาก snapshot นี้ ไม่แปลว่าไม่มีสวน โดยเฉพาะ Theos01 มีพิกัดอยู่นอกกรุงเทพฯ
- ทดสอบ contract ไฟล์ส่งต่อแล้ว แต่ยังไม่ได้ทดสอบกับ frontend ของเพื่อนจริง ไม่มี benchmark latency ที่รับรอง

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

รันซ้ำท้ายงานติด Windows access denied ก่อนเริ่ม tests แม้ขอสิทธิ์อ่าน runtime แล้ว โค้ดไม่ได้เปลี่ยนหลังชุดทดสอบที่ผ่าน 46 ข้อ ผล audit/ไฟล์ส่งต่อถูกตรวจต่อด้วย PowerShell ดู [สถานะการทดสอบ](Output/reviewed-final-tests-status-20261025.json) เพื่อแยกผลที่ผ่านจริงออกจากความพยายามรันซ้ำที่ถูกบล็อก

## โครงสร้าง

```text
grid.py             โค้ดฐานของทีม
greensight/         ฟังก์ชัน backend ของ Nike
data/scenes.json    ค่าตั้งสามภาพและ policy ที่ใช้ร่วมกัน
data/exclusions/    OSM snapshots พร้อมที่มา
data/labels/        labels, กรอบคัดบ้าน, กรอบ pending และบันทึกตรวจ
Images/             TIFF ในเครื่อง (ไม่ commit)
Output/             ผลแต่ละรันและชุด frontend (ไม่ commit)
tests/              ตรวจพฤติกรรมซอฟต์แวร์
docs/               คู่มือ วิธีทดลอง ข้อจำกัด และประวัติงาน
```

[รายงานตรวจล่าสุด](docs/FULL-AUDIT-th.md) · [วิธีคัดบริบทบ้าน](docs/PUBLIC-GREEN-SCREENING-th.md) · [วิธี labels](docs/LABELS-th.md) · [ประวัติงาน](docs/WORKLOG.md)

ทำงานใน branch `nike/green-zone-functions` และเก็บ commit ในเครื่อง ยังไม่ push หรือเปิด PR ตามที่ผู้ใช้กำหนด
