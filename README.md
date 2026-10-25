# Green-zone-v2 — Nike backend

Python functions สำหรับ **detect green zone, heatmap และ park verify** ใช้ TIFF ทั้งสามภาพของทีม แยกพื้นที่แต่ละภาพชัดเจน ไม่รวมเป็นยอดสวนทั้งเขต และคง `grid.py` ของเพื่อนไว้

## เริ่มใช้งาน

Python 3.10+; ทดสอบ backend ล่าสุดด้วย Python 3.12.14 แล้ว 46 ข้อผ่าน

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-nike.txt

# ตั้ง Images/ และค่าต่างๆ ใน data/scenes.json แล้วรัน
.\.venv\Scripts\python.exe run_nike.py --all --output Output/my-run

# เทียบทะเบียนสวนดอนเมืองกับพิกเซลจริงของทั้งสามภาพ
.\.venv\Scripts\python.exe verify_parks.py --output Output/my-park-check

# ทดสอบ
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

เลือก output ใหม่ทุกครั้ง ไม่เขียนทับผลเก่า `Images/` กับ `Output/` อยู่เฉพาะเครื่อง ไม่ commit ไม่ต้องใช้ API key สำหรับข้อมูล snapshot ที่มี

## หน้าที่หลักและฟังก์ชัน

| ฟังก์ชัน | ใช้ทำอะไร |
| --- | --- |
| `detect_green(bands, red_band=3, nir_band=4, ...)` | array `(bands,height,width)` → class mask ทดลอง |
| `make_heatmap(mask, pixel_m, clean_radius_m=3, ...)` | ตัดส่วนบาง กรองกลุ่มเล็ก และสร้าง RGBA พร้อมพื้นที่ |
| `analyse_scene(tif_path, out_dir, ...)` | อ่านทั้งภาพแบบ window รวมขอบครบ คัดพื้นที่และบันทึกผล |
| `find_parks_in_image(tif_path, registry_path, district='don-mueang')` | หาเฉพาะหมุดทะเบียนที่อยู่บนข้อมูลภาพจริงครบทุก band |
| `prepare_park_review(...)` | เทียบหมุดกับ mask และเตรียมงานตรวจ |
| `record_park_review(...)` | บันทึกหลักฐานตำแหน่ง/การเข้าใช้และผู้ตรวจ |
| `clean_saved_results(run_dir, out_dir, ...)` | คัดผลที่มีแล้ว โดยตรวจ parent hashes |

```python
from run_nike import run_all
from greensight import find_parks_in_image

results = run_all(out_dir='Output/my-three-scenes')
parks = find_parks_in_image('Images/Theos00.tif', district='don-mueang')
print(len(parks['features']))
```

`run_all()` อ่านเกณฑ์ร่วมจาก `data/scenes.json` หากเรียก `analyse_scene()` เอง ให้ส่ง context/policy/pending paths และ buffers ตาม config ด้วย

## เกณฑ์คัดพื้นที่ปัจจุบัน

1. อ่าน TIFF 512×512 รวม window ก่อนกรองกลุ่ม ตรวจ NoData ครบทุก band
2. ตรวจ raw-band ratio ทดลอง โดยสมมติ RED=3/NIR=4 ยังไม่ได้ยืนยัน calibration เฉพาะไฟล์
3. กันอาคาร 8 เมตร บ้านที่มีข้อมูล 20 เมตร เขต residential 10 เมตร และ private-access polygons จาก snapshot
4. ใช้กรอบคัดบริบทบ้านจากภาพใน `area-exclusions.geojson` รวม 86 เซลล์ตรวจและกรณีผู้ใช้ชี้ ไม่ใช่ขอบกรรมสิทธิ์ อาจกันพืชส่วนรวมใกล้บ้านด้วย
5. Disk opening รัศมี 3 เมตร แล้วเก็บกลุ่ม 4 ทิศที่ ≥300 ตร.ม. ไม่เติมพิกเซลพืชใหม่
6. สนามบิน/แนวรางที่ระบุไว้แยกเป็น pending ไม่รวมผลหลัก และคัดกลุ่มเล็กซ้ำหลังแบ่งพื้นที่
7. ตัด halo ออกจากกรอบที่กันไว้ด้วย สีจางเป็นระยะเส้นตรง ไม่ใช่ความร้อนหรือระยะเดิน
8. สนามกีฬา/โรงเรียน/วัด/รีสอร์ต/พื้นที่ร่วมที่ยังไม่ทราบการเข้าใช้คงเป็น candidate หากไม่ถูกคัดด้วยข้อมูลบริบทที่มี พร้อมสถานะยังไม่ยืนยัน

ปรับ `min_area_m2` ใน data/scenes.json หรือ CLI `--min-area-m2` ได้ (คงค่า 300 ตร.ม. ตามที่ตกลงเดิม) หากต้องการเน้นเฉพาะกลุ่มใหญ่กว่าเดิม อย่าเพิ่ม threshold แบบเงียบๆ หรือใช้ขนาดพื้นที่อ้างว่าเป็นสวนสาธารณะ

## Park verify และขอบเขตภาพ

ใช้ [แผนที่สวน 15 นาที Greener Bangkok](https://greener.bangkok.go.th/en/map-15-minute-garden/) ประกอบกับ `data/parks15.geojson` ซึ่งเป็น snapshot วันที่ 23 ต.ค. 2569 ไม่ใช่สถานะการเข้าใช้ปัจจุบัน

| ภาพ | หมุดทะเบียนที่ตรงตัวกรองดอนเมืองและอยู่บนภาพจริง | การตีความ |
| --- | ---: | --- |
| Theos00 | 2 | ภาพครอบคลุมบริเวณสนามบินดอนเมือง ไม่ใช่ขอบเขตทั้งเขต |
| Theos01 | 0 | พิกัดอยู่นอกกรุงเทพฯ วิเคราะห์แยก ไม่สรุปว่าไม่มีสวน |
| Theos02 | 0 | คนละกรอบพื้นที่กับ Theos00 ไม่เหมารวมว่าเป็นดอนเมือง |

ตัวกรอง district อาศัย metadata ในทะเบียน ไม่ใช่ polygon เขตการปกครอง ต้องมีขอบเขตเขตเพิ่มเติมหากจะวัดพื้นที่เฉพาะดอนเมืองทั้งหมด หมุดทะเบียนไม่ใช่ทางเข้าหรือขอบสวน ทุกจุดเริ่ม needs_review / verified_park=false จนมีหลักฐานตรวจจริง

## ไฟล์ผลสำหรับ backend / QGIS

| ไฟล์ | ความหมาย |
| --- | --- |
| `raw-mask.tif` | ผล ratio บนกริดต้นฉบับ |
| `candidate-mask.tif` | ผลหลักหลังคัดบ้าน/จุดเล็ก/แยก pending |
| `heatmap.tif`, `heatmap.png` | RGBA มีพิกัด / ภาพย่อสำหรับตรวจ |
| `pending-mask.tif`, `pending.tif` | พื้นที่เข้าข่ายที่แยกรอตรวจ ไม่รวมผลหลัก |
| `park-review.geojson` | หมุดและข้อมูลเตรียมตรวจสวน |
| `summary.json`, `summary-all.json`, `status.json` | พื้นที่ ค่าตั้ง ที่มา hashes และสถานะรัน |
| `audit.json`, `patch-review-catalog.json` | ผลตรวจซอฟต์แวร์และรายการกลุ่มคงเหลือ |

Mask codes: `0=other`, `1=candidate`, `2=uncertain`, `255=NoData` พื้นที่คำนวณบน native grid ไม่วัดจาก PNG ห้ามกรองทีละ tile แล้วบวกพื้นที่ซ้ำกัน

ผลอ้างอิงล่าสุด: `Output/nike-reviewed-final-20261025` ซึ่งประมวลผลก่อนปรับโครงสร้างโปรเจกต์ครั้งนี้ ค่าพื้นที่ไม่ถูกเปลี่ยนจากการลบส่วนเว็บ ผลตรวจทะเบียนรอบ backend-only อยู่ `Output/backend-park-lookup-20261025` และ tests อยู่ `Output/backend-only-tests-20261025.log`

## ส่งงานให้เพื่อน

```text
grid.py                 โค้ดฐานของทีม
run_nike.py             เรียกวิเคราะห์ตาม config
verify_parks.py         เทียบทะเบียนกับภาพ ไม่สร้าง UI
greensight/             ฟังก์ชัน backend
data/scenes.json        ค่าตั้งสามภาพ
data/exclusions/        snapshot อาคาร/ที่อยู่อาศัย
data/labels/            labels และ policy polygons
tests/                  ตรวจพฤติกรรมซอฟต์แวร์
docs/                   คู่มือและหลักฐานวิธีทำ
Images/, Output/        ข้อมูลในเครื่อง ไม่ commit
```

ดู [คู่มือรับงาน backend](docs/BACKEND-HANDOFF-th.md), [วิธีคัดบ้าน](docs/PUBLIC-GREEN-SCREENING-th.md), [วิธี labels](docs/LABELS-th.md), [รายงาน audit เดิม](docs/FULL-AUDIT-th.md) และ [ประวัติงาน](docs/WORKLOG.md)

ยังไม่มี human-reviewed labels สำหรับ accuracy จริง ไม่มีโมเดลที่ฝึกกับข้อมูลจริง และยังยืนยันว่ากำจัดหลังคา/สวนในบ้านได้ทั้งหมดไม่ได้ แยก vegetation truth ออกจากการคัดตามนโยบายเสมอ ผลที่เหลือคือ candidate ที่ต้องตรวจสิทธิและการเข้าถึงต่อ

ทำงานบน `nike/green-zone-functions` เฉพาะเครื่อง ยังไม่ push หรือเปิด PR
