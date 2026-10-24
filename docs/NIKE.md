# คู่มือฟังก์ชัน Nike

## 1. detect_green

```python
mask = detect_green(bands, red_band=3, nir_band=4, nodata=65535,
                    valid_mask=valid, exclude_mask=excluded)
```

- `bands`: numpy array `(จำนวน band, height, width)` จาก `src.read()`
- `red_band`, `nir_band`: หมายเลขเริ่ม 1 ต้องระบุเองและต่างกัน ไม่มีการเดา identity จากจำนวน bands
- `valid_mask`: bool `(height,width)`; False เป็น NoData/นอกกรอบศึกษา
- `exclude_mask`: bool บนกริดเดียวกัน; True ตัดออกจาก candidate สำหรับอาคาร/พื้นที่ส่วนตัวที่มีหลักฐาน
- `threshold=0.35`, `uncertain_threshold=0.15`: ค่าทดลอง ปรับได้ ไม่ใช่เกณฑ์มาตรฐานยืนยันพืช
- Output uint8: `0=other`, `1=candidate`, `2=uncertain`, `255=NoData`

คำนวณ `(nir-red)/(nir+red)` โดยแปลงชนิดก่อนลบเพื่อป้องกัน uint16 wraparound ข้อมูลใช้ได้แต่ denominator ไม่บวกเป็น uncertain; NaN/NoData ของ band ใดก็ตามไม่ใช้ พื้นที่ excluded ที่ข้อมูลยังใช้ได้เป็น 0 ส่วน NoData คง 255

ไม่มี ML model ที่ฝึกใหม่ใน package นี้ การย้าย RF ทดลองเดิมเข้ามาทั้ง backend จะเพิ่ม dependencies และยังไม่มี independent labels จึงคง detector เบื้องต้นให้ทีมทดสอบ/เปลี่ยนโมเดลได้ภายใต้ mask contract เดียวกัน

## 2. make_heatmap

```python
result = make_heatmap(mask, pixel_m=0.5, min_area_m2=300,
                      radius_m=50, style="red")
```

รับ mask codes เดิม พิกเซลสี่เหลี่ยมในหน่วยเมตร ไม่แก้ input คืน `mask`, `rgba`, `stats` พื้นที่คำนวณจำนวนพิกเซล × pixel_m²

กลุ่มติดกัน 4 ทิศ ไม่รวมแค่แตะมุม เก็บกลุ่มตั้งแต่ 300 ตร.ม. รวมเท่ากับเกณฑ์ ตัดเล็กกว่าเกณฑ์เป็น 0 สีเขียวแสดง candidate ที่เก็บไว้ สีรอบนอกค่อยจางภายใน radius; NoData โปร่งใสเสมอ ไม่มี candidate จะไม่สร้าง halo ขึ้นเอง

`style`: red (ค่าเริ่มต้น), spectrum, grid (แบ่งแถบสีระยะ ไม่ใช่การ resample เป็นกริด 5 เมตร) ระยะเป็นเส้นตรงถึงศูนย์กลางพิกเซลพืช ไม่ใช่ระยะเดินหรือความร้อน ไม่ทำให้ classifier แม่นขึ้น

รวม tile cores ของภาพเดียวกันก่อนกรองกลุ่มและสร้างระยะเพื่อป้องกันรอยต่อ ตัวอย่าง `run_nike.py` ใช้สำหรับ tile/crop ที่เล็กพอเท่านั้น ยังไม่ใช่ตัวรวม scene ขนาดใหญ่

## 3. prepare_park_review

รับทะเบียน WGS84 Point GeoJSON, mask ที่รวมแล้ว, affine transform, CRS แบบ north-up หน่วยเมตร และ scene_id ที่ระบุถูกต้อง คืน FeatureCollection สำหรับตรวจ + excluded IDs/reasons + provenance

ระบุ scene ให้คงที่ทั้ง registry/mask หาก registry มี sceneId จะตรวจว่าตรงกัน พิกัดหมุดบน NoData/นอกกรอบไม่ได้แสดงเป็นจุดสวนในภาพ

แต่ละงานมีชื่อ พิกัดเดิม ระยะ candidate ที่ใกล้ที่สุดภายใน search_radius_m, พื้นที่ candidate, สัดส่วนพื้นที่ที่มีข้อมูล ลิงก์ Maps/Street View และสถานะ needs_review ระยะ null หมายถึงไม่พบภายในรัศมี ไม่ใช่ไม่มีสวน ส่วนข้อมูลขาดที่ขอบวงยังถูกนับในการวัด coverage

Provenance เก็บ hashes ของ mask/registry, shape, transform, CRS, radius และวันที่ วันที่ snapshot ไม่ใช่วันเปิดสวน ภาพปี 2024 กับทะเบียนปี 2026 ต้องตรวจความต่างของเวลา ไม่มีการเรียก Google API หรือใช้ API key

## 4. record_park_review

```python
reviewed = record_park_review(
    task, reviewer=reviewer_name, reviewed_on=review_date,
    decision="verified_park", position_confirmed=True,
    public_access_confirmed=True, evidence=evidence_records,
    notes=review_notes,
)
```

เรียกเมื่อมีผู้ตรวจจริงเท่านั้น `decision` คือ needs_review / verified_park / rejected

หลักฐานแต่ละรายการมี `url` HTTPS, `observed_on` YYYY-MM-DD และ `scopes` เป็น list ของ position/public_access การยืนยันต้องมีทั้งสอง confirmations และหลักฐานครบสองด้าน การ rejected ต้องมีหลักฐานและเหตุผล บันทึก history โดยไม่แก้ task ต้นฉบับหรือย้ายหมุด

ตัวตรวจบังคับความครบของหลักฐาน แต่ตรวจไม่ได้ว่าคำกล่าวของผู้ตรวจเป็นจริง การพบต้นไม้ใกล้หมุดไม่ใช่การรับรองสวนสาธารณะ/ทางเข้า และ 50 เมตรในฟังก์ชันนี้ไม่ใช่เกณฑ์เดินถึงสวนใน 15 นาที

## ส่งต่อ frontend

ใช้ GeoJSON หมุด, mask codes, RGBA และ summary โดยแยกชื่อชั้น candidate กับ registered parks / verified parks อย่าแปลง needs_review เป็น verified หรือใช้ candidate ทั้งหมดเป็นสวน

GeoTIFF มีพิกัดแต่ไม่ใช่ XYZ tile URL หากเว็บต้องการ HTTP/XYZ ให้เพื่อนสร้าง adapter ตามกริดและ CRS ของผลโดยไม่ย้ายหมุดเพื่อให้ทับสีเขียว

## ข้อมูลในเครื่อง

ตรวจ metadata: Theos00 23,700×18,695, Theos01 25,176×25,348, Theos02 23,468×25,045; ทั้งหมด 4 bands, EPSG:32647, 0.5 เมตร, NoData 65535 และไม่มีชื่อ spectral bands ใน metadata ที่อ่านได้

ตัวอย่างที่ทดลอง: `tile_r7_c9.tif` ของ Theos00 ได้ candidate หลังกรอง 26,478.75 ตร.ม. ใน 30 กลุ่ม มีหมุดทะเบียนรอตรวจ 1 จุด ยืนยันจริง 0 จุด ตัวเลขเป็นผลกฎทดลองบน tile เดียว ไม่ใช่พื้นที่สวนที่ยืนยันหรือผลทั้ง 3 ภาพ

ดู [ประวัติการตรวจและการเปลี่ยนแปลง](WORKLOG.md) สำหรับ scope ที่ทำแล้ว/ยังไม่ทำ
