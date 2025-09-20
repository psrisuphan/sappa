# DC Motor Speed Control with PID Tuning

## Overview
โปรเจคนี้ทำการจำลองการควบคุมความเร็วของมอเตอร์ DC โดยใช้ **PID controller** และสามารถปรับค่า **Kp**, **Ki**, และ **Kd** เพื่อให้ได้การตอบสนองที่ดีที่สุดสำหรับมอเตอร์ในระบบควบคุม

## Requirements
โปรเจคนี้ต้องการ Python environment ที่ติดตั้ง dependencies ต่อไปนี้:

- **Python 3.12** หรือ **Python 3.13**
- **pip** (เพื่อใช้ติดตั้ง dependencies)

แพ็คเกจที่จำเป็นต้องใช้:
- `numpy`
- `scipy`
- `matplotlib`
- `control`

### วิธีการติดตั้ง dependencies:
1. สร้าง virtual environment ใหม่:

    python -m venv .venv

2. เปิดใช้งาน virtual environment:

    - สำหรับ macOS/Linux:

        source .venv/bin/activate

    - สำหรับ Windows:

        .venv\Scripts\activate

3. ติดตั้ง dependencies จาก `requirements.txt`:

    pip install --upgrade pip
    pip install -r requirements.txt

*****วิธีการใช้งาน*****

1. ป้อนค่าพารามิเตอร์ของมอเตอร์ DC

เมื่อรันโปรแกรม โปรแกรมจะขอให้กรอกค่าพารามิเตอร์ของมอเตอร์ เช่น:

    J: Moment of inertia (kg.m²)
    b: Damping coefficient (N.m.s)
    R: Resistance (Ohm)
    L: Inductance (H)
    K: Motor constant (Nm/A หรือ Vs/rad)
    หากไม่ได้ระบุค่า J หรือ b (ใส่ -1), โปรแกรมจะทำการคำนวณค่าผ่าน System Identification เพื่อหาค่าที่เหมาะสม

2. ปรับแต่ง PID Controller

ในขั้นตอนนี้ ผู้ใช้สามารถกรอกค่า PID สำหรับการควบคุมมอเตอร์:

    Kp: Proportional gain
    Ki: Integral gain
    Kd: Derivative gain
    หากไม่ใส่ค่าเหล่านี้ โปรแกรมจะใช้ค่าที่ตั้งไว้ล่วงหน้าเพื่อทดสอบการตอบสนองของระบบ

3. การจำลองและการพล็อตกราฟ

    โปรแกรมจะทำการคำนวณและจำลองการตอบสนองของมอเตอร์ DC โดยใช้ PID controller ที่ผู้ใช้กำหนด และจะแสดงกราฟ Speed (rad/s) กับ Time (s) สำหรับแต่ละค่าของ PID ที่ทดสอบ

4. การรันโปรแกรม

    รันโปรแกรมโดยใช้คำสั่ง:

        python motor_control.py

เมื่อรันโปรแกรม โปรแกรมจะถามค่าพารามิเตอร์ต่างๆ จากผู้ใช้ และแสดงกราฟที่จำลองการตอบสนองของมอเตอร์ที่ควบคุมด้วย PID

*****ตัวอย่างผลลัพธ์*****

โปรแกรมจะสร้างกราฟที่แสดงผลของการควบคุมมอเตอร์ DC ในการตอบสนองแบบ Step Response โดยแสดงความเร็ว (rad/s) ของมอเตอร์ตามเวลา (s) เมื่อได้รับสัญญาณ Step จาก PID controller ที่ทดสอบ
หมายเหตุ: หากผู้ใช้ไม่มีข้อมูลของมอเตอร์จากผู้ผลิต (เช่น ค่า J, b), โปรแกรมจะทำการประเมินค่าด้วย System Identification แทน เพื่อหาค่าที่เหมาะสมที่สุด

การปรับแต่งเพิ่มเติม
    สามารถปรับค่าของ Kp, Ki, และ Kd เพื่อทดสอบผลลัพธ์ต่างๆ และดูการตอบสนองของมอเตอร์
    สำหรับการหาค่าพารามิเตอร์มอเตอร์ (J, b) ที่แม่นยำขึ้น, สามารถใช้ System Identification เพื่อหาค่าจากข้อมูล Step Response ที่เก็บได้