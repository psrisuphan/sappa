# DC Motor Auto Identification & PID Auto-Tuning

โค้ดนี้ช่วยจำลองระบบควบคุมความเร็วของมอเตอร์ DC พร้อมหลากหลายเครื่องมือสำหรับระบุพารามิเตอร์เชิงกล (J, b) และหาค่า PID ที่เหมาะสมที่สุด ปัจจุบันรองรับทั้งโหมด CLI แบบดั้งเดิมและอินเทอร์เฟซแบบกราฟิกด้วย Streamlit

## Highlights
- จำลองพืช (plant) มอเตอร์ DC แบบ order 1 หรือ order 2
- ระบุค่าความเฉื่อย (J) และแรงเสียดทาน (b) จากข้อมูล step response
- ตั้งค่าและปรับจูน PID อัตโนมัติด้วยการค้นหาหยาบและปรับละเอียด
- ตรวจสอบผลการควบคุมด้วยกราฟ step response และตารางสรุปตัวชี้วัด

## Environment Setup
ต้องมี Python 3.10+ และ pip

```
# 1) Clone หรือดาวน์โหลดโปรเจ็กต์
git clone <repo-url>
cd dc-motor-auto-tune

# 2) สร้างและเปิดใช้งาน virtual environment
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows PowerShell

# 3) ติดตั้ง dependencies ที่ต้องใช้
pip install --upgrade pip
pip install -r requirements.txt

# 4) รันโหมด CLI (หากต้องการ)
python dc_motor_auto_tune.py

# 5) หรือรันโหมด Streamlit GUI
streamlit run streamlit_app.py
```

แพ็กเกจหลัก: `numpy`, `scipy`, `matplotlib`, `control`, `streamlit`

## Option A – Command Line Interface
ไฟล์ `dc_motor_auto_tune.py` คือเวอร์ชัน CLI

```
python dc_motor_auto_tune.py
```

ลำดับการทำงานเมื่อรันสคริปต์
- ป้อนค่าพารามิเตอร์ R, L, Kt, Ke, J, b (ใส่ -1 เพื่อให้โปรแกรมประเมินจากข้อมูล step response)
- ระบุว่าจะใช้โมเดลที่รวม L, กำลังของ step ที่ทดสอบ, เวลาจำลอง, และข้อมูลสำหรับ derivative filter
- ถ้าต้องระบุ J หรือ b ระบบจะขอไฟล์ CSV แบบสองคอลัมน์ [t, omega] หรือสร้างข้อมูลจำลองให้
- โปรแกรมจะระบุ J/b (ถ้าจำเป็น), จูน PID, แล้วแสดงกราฟและสรุปตัวชี้วัด

## Option B – Streamlit GUI
ไฟล์ `streamlit_app.py` เปิด GUI สำหรับทำทุกขั้นตอนแบบ interactive

```
streamlit run streamlit_app.py
```

ส่วน Sidebar
- Mechanical/Electrical parameters: กรอกค่าที่ทราบหรือเลือก identify J/b
- Control settings: magnitude ของ step, เวลา simulation, ตัวเลือก derivative filter
- Identification data (หากเลือก identify): อัปโหลด CSV, ใช้ `step_data.csv`, หรือสร้างข้อมูลจำลองพร้อม noise

ผลลัพธ์
- แสดงค่าพารามิเตอร์ที่ใช้และ PID gain ที่จูนได้
- แสดงกราฟ identification fit และกราฟ step response เปรียบเทียบ P, PI, PID
- สรุปตัวชี้วัด เช่น overshoot, settling time, steady-state error
- แสดงข้อมูลดิบ step response เพื่อการตรวจสอบ

## CSV Format for Identification
ไฟล์ต้องมี 2 คอลัมน์ (ไม่มี header)

```
time_seconds, omega_radians_per_second
```

เวลา sampling ควรสม่ำเสมอ หากมี noise สามารถปล่อยไว้ได้ โปรแกรมจะใช้ข้อมูลนั้นโดยตรง

## Known Limitations
- การจูน PID อาจใช้เวลามากกับชุดพารามิเตอร์ที่ทำให้ระบบเกือบไม่เสถียร
- ข้อมูล step response ที่มี noise สูงอาจทำให้ค่าที่ระบุเบี่ยงเบน ต้องใช้ฟิลเตอร์หรือเพิ่มจำนวนข้อมูล

## Troubleshooting
- ถ้ารัน Streamlit แล้วเจอ error เกี่ยวกับ matplotlib backend ให้ปิดหน้าต่างกราฟทั้งหมดก่อนรันใหม่
- หากไม่มี `python` ให้ใช้ `python3` แทนในคำสั่งทั้งหมด
 
