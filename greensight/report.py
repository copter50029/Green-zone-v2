"""Static local results report; no frontend server or JS build needed."""
import html
from pathlib import Path

from .scene import write_json


def write_report(out_dir, results):
    output = Path(out_dir)
    cards = []
    for result in results:
        scene = html.escape(result['scene_id'])
        area = result['stats']['retainedCandidateAreaM2']
        cards.append(f'''<section><h2>{scene}</h2><p>Candidate {area:,.2f} m² · {result['stats']['retainedPatchCount']} patches · {result['review_tasks']} registered points awaiting review</p>
        <div class="images"><figure><img src="{scene}/source.png"><figcaption>Source image (display stretch)</figcaption></figure><figure><img src="{scene}/heatmap.png"><figcaption>Green candidate + fading proximity halo, after mapped exclusions</figcaption></figure></div>
        <p><a href="{scene}/summary.json">Summary / provenance</a> · <a href="{scene}/park-review.geojson">Park review GeoJSON</a></p></section>''')
    page = '''<!doctype html><html lang="th"><meta charset="utf-8"><title>GreenSight — Nike scene results</title>
    <style>body{font:16px system-ui,sans-serif;background:#edf2ef;color:#173b2d;margin:30px auto;max-width:1500px;padding:0 22px}section{background:white;border-radius:14px;padding:20px;margin:22px 0}.images{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{width:100%;height:auto}figcaption{padding:10px 0;color:#52635a}a{color:#167d4a}.warning{background:#fff5da;padding:16px;border-radius:8px}</style>
    <h1>GreenSight · ผลประมวลผลทั้งสามภาพ</h1><p class="warning">สีเขียวเป็น candidate พืชหลังตัดพื้นที่ที่มีข้อมูลอ้างอิง สีแดงจางเป็นระยะเส้นตรง ไม่ใช่ความร้อนหรือระยะเดิน ผลยังไม่มี accuracy จาก labels จริง และยังไม่ยืนยันสิทธิการเข้าถึงสวน<br>OSM อาจไม่ครบและคนละปีกับภาพ การตัด landuse=residential อาจตัดต้นไม้สาธารณะในบริเวณนั้นด้วย</p>''' + ''.join(cards) + '</html>'
    (output/'index.html').write_text(page,encoding='utf-8')
    write_json(output/'summary-all.json',results)
