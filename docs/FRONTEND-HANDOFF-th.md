# ส่งต่อ frontend และตรวจ labels

## อธิบายงานใน 30 วินาที

เราใช้ TIFF จาก GISTDA เป็นข้อมูลหลักทั้งสามภาพ ตรวจพืชที่เข้าข่าย อ่านแบบ window แล้วรวมทั้งภาพก่อนกรองกลุ่มตั้งแต่ 300 ตร.ม. ใช้ข้อมูลอาคาร/ที่อยู่อาศัย/พื้นที่จำกัดสิทธิที่มีในเครื่องช่วยคัดออก สีเขียวคือ candidate พืช สีจางรอบๆ คือความใกล้เชิงระยะเส้นตรง หมุด 15 คือรายการทะเบียนที่ตำแหน่งอยู่ในข้อมูลภาพ ไม่ใช่สวนที่ระบบยืนยันสิทธิหรือเวลาเปิดแล้ว

## สร้างชุดให้ frontend

```python
from greensight import export_frontend

manifest = export_frontend(
    'Output/nike-scenes-20261025',
    'Output/my-frontend-package',  # ต้องเป็นโฟลเดอร์ใหม่
)
```

ไม่ต้องประมวลผลภาพเดิมใหม่ ไม่ติดตั้งบริการแผนที่หรือ API key ไม่เพิ่ม web server ให้ backend ฟังก์ชันตรวจ hashes ของไฟล์ผลก่อนส่งออกและไม่แก้ผลต้นฉบับ

ชุดพร้อมใช้ในเครื่อง: `Output/frontend-ready-20261025/` และ zip ชื่อเดียวกัน ให้เพื่อนนำเนื้อหาโฟลเดอร์ไปวางใน static assets ของ frontend เช่น `public/nike/` แล้วอ่าน `/nike/manifest.json` ผ่าน HTTP ของแอปเพื่อน ไม่ fetch จาก file://

| Field | ความหมาย |
| --- | --- |
| schema_version | รุ่น contract ปัจจุบัน 1 |
| scenes[].id | Theos00 / Theos01 / Theos02 |
| bounds_wgs84 | [west, south, east, north] องศา ไม่ใช่ [lat,lng] |
| image_crs | EPSG:3857 สำหรับแผนที่เว็บ Web Mercator |
| source / heatmap | URL PNG RGBA สัมพันธ์กับโฟลเดอร์ manifest |
| parks | URL GeoJSON หมุดทะเบียน พิกัด GeoJSON=[longitude,latitude] |
| candidate_area_m2 | พื้นที่จากกริดวิเคราะห์เดิม ไม่คำนวณจาก PNG |
| valid_area_m2 | พื้นที่ข้อมูลภาพที่ใช้งานได้ |
| park_points / verified_parks | จำนวนในภาพ / จำนวนยืนยันแล้ว ห้ามแสดงสองค่านี้แทนกัน |
| status / real_accuracy | สถานะทดลอง / null จนมีหลักฐานประเมินจริง |
| limitations | ข้อจำกัดที่ต้องสื่อสารกับผู้ใช้ |
| source_sha256 | hash TIFF หลักของผลวิเคราะห์ |
| files_sha256 | hash ของไฟล์ในชุดส่งต่อ ไม่รวม manifest เอง |

PNG ถูก warp เป็น EPSG:3857 แล้ว มี alpha นอกขอบข้อมูล วางสองชั้น source/heatmap ด้วย bounds เดียวกัน ปรับ opacity ของ heatmap ได้ และให้ผู้ใช้เปิด/ปิดหมุดสวน ภาพย่อสูงสุด 1,200 พิกเซลใช้เพื่อดูภาพรวมเท่านั้น งานวัดพื้นที่หรือดูรายละเอียดต้องใช้ GeoTIFF ต้นฉบับใน QGIS/ระบบ tiles ของทีม

ตัวอย่างส่วนเชื่อมสำหรับ frontend ที่มี Leaflet อยู่แล้ว (ตัวอย่าง adapter ไม่ใช่ frontend ใหม่):

```javascript
const base = '/nike/';
const { scenes } = await fetch(base + 'manifest.json').then(r => r.json());
const scene = scenes[0];
const [west, south, east, north] = scene.bounds_wgs84;
const bounds = [[south, west], [north, east]];
L.imageOverlay(base + scene.source, bounds).addTo(map);
L.imageOverlay(base + scene.heatmap, bounds, { opacity: 0.75 }).addTo(map);
map.fitBounds(bounds);
const parks = await fetch(base + scene.parks).then(r => r.json());
L.geoJSON(parks).addTo(map); // popup ให้ใช้ textContent สำหรับข้อความจากข้อมูล
```

ระบบทดสอบ export กับ raster จริงขนาดเล็กและส่งออกทั้งสามภาพแล้ว ยังไม่ได้ทดสอบใน frontend ของเพื่อน เพราะไม่มี source frontend ของเพื่อนใน workflow นี้ แผนที่ที่ใช้ CRS อื่นต้องมี adapter เพิ่ม

## งานตรวจ labels ที่คนต้องทำ

ไฟล์เริ่มต้น `Output/labels-assistant-20261025/human-review-queue.json` มี 42 รายการ **class ของคำตอบจริงว่างทุกแถว** พร้อม suggested_class แยกไว้ เปิด `Theos00/01/02-label-review.png` ในโฟลเดอร์เดียวกันเพื่อดูภาพ source และ core ขยาย จับคู่ด้วย label_id

ผู้ตรวจอ่านภาพจริง แล้วกรอก class=positive/negative/uncertain, reviewer, reviewed_on แบบ YYYY-MM-DD และ notes ตามสิ่งที่ตรวจ แถวที่ยังไม่ตรวจปล่อย class=null ห้ามกรอกผู้ตรวจแทนคนอื่นหรือเปลี่ยนสถานะอัตโนมัติ uncertain ไม่ถูกส่งเป็นคำตอบฝึก/ประเมิน

```python
import json
from pathlib import Path
from greensight import prepare_label_review, apply_label_review

labels = json.loads(Path('data/labels/assistant-vegetation.geojson').read_text())
# ใช้เมื่อสร้างคิวใหม่: queue = prepare_label_review(labels)
queue = json.loads(Path('Output/labels-assistant-20261025/human-review-queue.json').read_text())
reviewed = apply_label_review(labels, queue)
for split, collection in reviewed.items():
    Path(f'Output/human-{split}.geojson').write_text(
        json.dumps(collection, ensure_ascii=False, indent=2), encoding='utf-8')
```

ฟังก์ชันเก็บประวัติ assistant_source แยก train/validation/test คง split เดิม และไม่แก้ original labels คิวว่างจะได้ human references ว่างทั้งหมด การตรวจรูปแบบชื่อ/วันที่ไม่สามารถพิสูจน์ตัวบุคคลหรือความจริงของคำตอบได้ ผู้จัดชุดข้อมูลต้องตรวจคุณภาพและความเป็นอิสระด้วย

## ลำดับถัดไปที่ต้องใช้หลักฐาน

1. ให้ผู้ตรวจอิสระตรวจ labels และเพิ่มตัวอย่างบริเวณใหม่ให้สองคลาสครบทุก split ปัจจุบัน Theos01 validation ขาด negative และ Theos02 test ขาด positive
2. ตรวจชุด train/validation เพื่อปรับวิธี แล้วเก็บ test ไว้ประเมินครั้งสุดท้าย ไม่ปรับ threshold ตาม test
3. ยืนยัน band/calibration จากผลิตภัณฑ์เฉพาะไฟล์; สิทธิ ทางเข้า และเวลาเปิดสวนใช้ข้อมูลหน่วยงาน/ตรวจพื้นที่
4. จึงฝึกและรายงาน precision/recall/IoU ตามหลักฐาน ไม่อ้างผลชุดนี้ว่ากำจัดหลังคาหรือพื้นที่ส่วนตัวได้ครบ

ไม่มีการส่ง GitHub หรือเรียกบริการภายนอกในการส่งออก/จัดชุดตรวจครั้งนี้

## ชุดส่งต่อรอบตรวจครบสามภาพ

ชุดล่าสุด: `Output/frontend-reviewed-20261025.zip` ยึด README และ docs/FULL-AUDIT-th.md สำหรับตัวเลขปัจจุบัน ส่วนตัวอย่าง path รุ่นก่อนด้านบนเป็นประวัติ

แต่ละ scene ใน manifest เพิ่ม optional fields:

```json
{
  "pending": "Theos00/pending.png",
  "pending_area_m2": 180615.5,
  "pending_in_main_total": false
}
```

วาง pending ด้วย bounds เดียวกับ source/heatmap เป็นชั้นสีเหลืองที่เปิดปิดแยกได้ และไม่บวกใน candidate_area_m2 ภาพที่ pending_area_m2=0 หมายถึงไม่มี candidate ในกรอบ pending ที่ระบุ ไม่ได้พิสูจน์ว่าไม่มีพื้นที่จำกัดสิทธิในภาพทั้งหมด หมุด 15 ยัง needs_review/verified=false
