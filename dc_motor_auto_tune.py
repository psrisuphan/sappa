import numpy as np
import control as ct
import matplotlib.pyplot as plt
from scipy.optimize import least_squares, minimize
import os

# ============== Utilities ==============
def ask_float(prompt, default=None):
    s = input(prompt).strip()
    if s == "" and default is not None:
        return float(default)
    try:
            return float(s)
    except:
        print("กรุณาใส่ตัวเลขที่ถูกต้อง")
        return ask_float(prompt, default)

def ask_yesno(prompt, default="y"):
    s = input(prompt + (" [Y/n]: " if default.lower().startswith("y") else " [y/N]: ")).strip().lower()
    if s == "" and default:
        return default.lower().startswith("y")
    if s in ["y", "yes", "1"]:
        return True
    if s in ["n", "no", "0"]:
        return False
    print("กรุณาตอบ y หรือ n")
    return ask_yesno(prompt, default)

def step_metrics(sys, step_mag=1.0, t_end=4.0, npts=1600):
    t = np.linspace(0, t_end, npts)
    t, y = ct.step_response(sys * step_mag, t)
    yss = y[-1] if len(y) else np.nan
    PO = max(0.0, (np.max(y) - (yss if yss!=0 else 1e-9)) / (yss if yss!=0 else 1e-9) * 100.0)
    idx = np.where(np.abs(y - yss) <= 0.02 * abs(yss if yss!=0 else 1.0))[0]
    ts = t[idx[0]] if len(idx) else np.inf
    try:
        t10 = t[np.where(y >= 0.1*yss)[0][0]]
        t90 = t[np.where(y >= 0.9*yss)[0][0]]
        tr = t90 - t10
    except:
        tr = np.inf
    ess = abs(step_mag - yss)
    e = step_mag - y
    iae = np.trapz(np.abs(e), t)
    return {"t": t, "y": y, "yss": yss, "PO": PO, "ts": ts, "tr": tr, "ess": ess, "IAE": iae}

def dc_motor_tf(R, L, J, b, Kt, Ke, include_L=True):
    if include_L:
        # G(s) = Kt / [(Ls+R)(Js+b) + Kt*Ke] (second order)
        num = [Kt]
        den = [L*J, (L*b + R*J), (R*b + Kt*Ke)]
    else:
        # ละ L -> first order approx
        num = [Kt]
        den = [R*J, (R*b + Kt*Ke)]
    return ct.TransferFunction(num, den)

def pid_controller(Kp, Ki, Kd, use_d_filter=True, Tf=0.01):
    # C(s) = Kp + Ki/s + Kd*s  (หรือ Kd*s/(1+sTf) ถ้าใช้ฟิลเตอร์อนุพันธ์)
    if use_d_filter and Kd > 0:
        # Kd*s/(1+sTf) + (Kp + Ki/s)
        C_d = ct.TransferFunction([Kd, 0], [Tf, 1])
        C_pi = ct.TransferFunction([Kp, Ki], [1, 0])
        return C_d + C_pi
    else:
        return ct.TransferFunction([Kd, Kp, Ki], [1, 0])

# ============== สร้าง step_data.csv แบบจำลอง ==============
def synthesize_step_data(path_csv, R, L, Kt, Ke, J_true, b_true,
                         step_mag=1.0, t_end=3.0, dt=0.01, include_L=True,
                         noise_std=0.0, seed=0):
    G_true = dc_motor_tf(R, L, J_true, b_true, Kt, Ke, include_L=include_L)
    t = np.arange(0.0, t_end + 1e-12, dt)
    _, y = ct.step_response(G_true * step_mag, T=t)

    if noise_std > 0:
        rng = np.random.default_rng(seed)
        y = y + rng.normal(0.0, noise_std, size=y.shape)

    data = np.column_stack([t, y])
    np.savetxt(path_csv, data, delimiter=",", fmt="%.6f")
    print(f"[SIM] สร้างไฟล์จำลองแล้ว -> {path_csv} (N={len(t)}, dt={dt}s, noise_std={noise_std})")
    return t, y

# ============== System Identification (เมื่อ J หรือ b == -1) ==============
def identify_J_b(t_data, w_data, R, L, Kt, Ke, V_step, include_L=True):
    w_data = w_data - w_data[0]  # remove offset
    def simulate(J, b, t_vec):
        G = dc_motor_tf(R, L, J, b, Kt, Ke, include_L=include_L)
        _, y = ct.step_response(G * V_step, T=t_vec)
        return y

    def residuals(theta):
        J, b = theta
        if J <= 0 or b <= 0:
            return 1e6*np.ones_like(w_data)
        y_hat = simulate(J, b, t_data)
        return (y_hat - w_data)

    theta0 = np.array([0.01, 0.1])
    lb = [1e-7, 1e-7]
    ub = [1.0, 10.0]
    res = least_squares(residuals, theta0, bounds=(lb, ub), method="trf", verbose=1)
    J_hat, b_hat = res.x

    # plot measured vs fitted
    G_fit = dc_motor_tf(R, L, J_hat, b_hat, Kt, Ke, include_L=include_L)
    _, y_sim = ct.step_response(G_fit * V_step, T=t_data)
    mse = np.mean((y_sim - (w_data))**2)
    rmse = np.sqrt(mse)

    plt.figure()
    plt.plot(t_data, w_data, label="Measured")
    plt.plot(t_data, y_sim, label="Fitted (simulated)")
    plt.xlabel("Time (s)")
    plt.ylabel("Speed (rad/s)")
    plt.title("System Identification: Measured vs Fitted")
    plt.grid(True)
    plt.legend()
    print("\n[ID] Estimated J = %.6f kg·m^2, b = %.6f N·m·s, RMSE = %.6e" % (J_hat, b_hat, rmse))
    return float(J_hat), float(b_hat)

# ============== PID Tuning (coarse → refine) ==============
def tune_pid(G, step_mag=1.0, t_end=4.0, npts=1600, use_d_filter=True, Tf=0.01,
             weights=None):
    if weights is None:
        weights = {"ess":5.0, "PO":0.05, "tr":0.3, "ts":0.2, "IAE":0.5}

    def closed_loop(Kp, Ki, Kd):
        C = pid_controller(Kp, Ki, Kd, use_d_filter=use_d_filter, Tf=Tf)
        return ct.feedback(C*G, 1)

    def objective(x):
        Kp, Ki, Kd = np.maximum(x, 0.0)
        try:
            sys = closed_loop(Kp, Ki, Kd)
            m = step_metrics(sys, step_mag=step_mag, t_end=t_end, npts=npts)
        except Exception:
            return 1e9
        score = (weights["ess"]*m["ess"] +
                 weights["PO"] *m["PO"]  +
                 weights["tr"] *m["tr"]  +
                 weights["ts"] *m["ts"]  +
                 weights["IAE"]*m["IAE"])
        if not np.isfinite(score):
            return 1e9
        return score

    # coarse grid
    Kp_list = np.geomspace(5, 500, 6)
    Ki_list = np.geomspace(1, 300, 6)
    Kd_list = np.geomspace(0.1, 50, 5)
    best = (np.inf, None)
    for Kp in Kp_list:
        for Ki in Ki_list:
            for Kd in Kd_list:
                val = objective([Kp, Ki, Kd])
                if val < best[0]:
                    best = (val, [Kp, Ki, Kd])
    x0 = np.array(best[1])

    # local refine
    res = minimize(objective, x0, method="Nelder-Mead",
                   options={"maxiter": 400, "xatol":1e-3, "fatol":1e-3})
    x = np.clip(res.x, [0,0,0], [1e5,1e5,1e5])
    res2 = minimize(objective, x, method="Powell",
                    options={"maxiter": 400, "xtol":1e-3, "ftol":1e-3})
    x2 = np.clip(res2.x, [0,0,0], [1e5,1e5,1e5])
    Kp_opt, Ki_opt, Kd_opt = x2
    print("\n[PID] Initial (grid): Kp=%.3f Ki=%.3f Kd=%.3f" % (x0[0], x0[1], x0[2]))
    print("[PID] Optimized     : Kp=%.3f Ki=%.3f Kd=%.3f" % (Kp_opt, Ki_opt, Kd_opt))

    # summary + plots
    def clsys(Kp, Ki, Kd):
        return ct.feedback(pid_controller(Kp, Ki, Kd, use_d_filter=use_d_filter, Tf=Tf)*G, 1)

    sys_best = clsys(Kp_opt, Ki_opt, Kd_opt)
    met_best = step_metrics(sys_best, step_mag=step_mag, t_end=t_end, npts=npts)
    sys_p  = clsys(Kp_opt, 0, 0)
    sys_pi = clsys(Kp_opt, Ki_opt, 0)
    met_p  = step_metrics(sys_p,  step_mag=step_mag, t_end=t_end, npts=npts)
    met_pi = step_metrics(sys_pi, step_mag=step_mag, t_end=t_end, npts=npts)

    print("\n=== Metrics (Optimized PID) ===")
    for k in ["PO","ts","tr","ess","IAE"]:
        print(f"{k}: {met_best[k]:.4f}")
    print("y_ss:", met_best["yss"])

    t = met_best["t"]
    plt.figure()
    plt.plot(t, met_best["y"], label=f"PID (Kp={Kp_opt:.1f}, Ki={Ki_opt:.1f}, Kd={Kd_opt:.1f})")
    plt.plot(t, met_p["y"],  label="P-only")
    plt.plot(t, met_pi["y"], label="PI")
    plt.axhline(step_mag, linestyle="--", linewidth=1)
    plt.xlabel("Time (s)")
    plt.ylabel("Speed (rad/s)")
    plt.title("DC Motor Speed Control - Step Response (Auto-tuned PID)")
    plt.grid(True)
    plt.legend()

    return Kp_opt, Ki_opt, Kd_opt, met_best

# ============== Main flow ==============
def main():
    print("=== DC Motor Auto Identification + PID Auto Tuning ===\n"
          "ใส่ค่าพารามิเตอร์ (กด Enter = ใช้ค่า default ถ้ามี) | ใส่ -1 = ไม่ระบุ")
    # Known electrical/mechanical constants
    R  = ask_float("R (Ohm) [default 1.0] : ", 1.0)
    L  = ask_float("L (H) [default 0.5]   : ", 0.5)
    Kt = ask_float("Kt (N·m/A) [0.01]     : ", 0.01)
    Ke = ask_float("Ke (V·s/rad) [0.01]   : ", 0.01)
    J  = ask_float("J (kg·m^2) [-1=unknown]: ", -1)
    b  = ask_float("b (N·m·s)  [-1=unknown]: ", -1)

    include_L = ask_yesno("ใช้โมเดลรวม L (2nd order) ไหม?", default="y")
    step_mag  = ask_float("ขนาด Step ของแรงดันทดสอบ/ควบคุม [1.0]: ", 1.0)
    sim_T     = ask_float("เวลาจำลอง (s) [4.0]: ", 4.0)

    use_d_filter = ask_yesno("ใช้ derivative filter สำหรับ Kd หรือไม่?", default="y")
    Tf = ask_float("Derivative filter Tf (s) [0.01]: ", 0.01)

    # If J or b unknown -> need CSV for identification or synthesize it
    t_data = w_data = None
    if J < 0 or b < 0:
        print("\nต้องใช้ไฟล์ CSV ข้อมูล step response (2 คอลัมน์: t,omega) ไม่มี header")
        csv_path = input("พาธไฟล์ CSV (เว้นว่างเพื่อ 'สร้างไฟล์จำลอง'): ").strip()

        if csv_path == "":
            # สร้างไฟล์จำลอง step_data.csv
            csv_path = "step_data.csv"
            print("\n--- โหมดจำลอง step_data.csv ---")
            # ขอค่า 'จริง' เพื่อใช้จำลอง (หรือ Enter ใช้ค่าเริ่มต้น)
            J_true = ask_float("กำหนด J_true สำหรับการจำลอง [0.01]: ", 0.01)
            b_true = ask_float("กำหนด b_true สำหรับการจำลอง [0.1] : ", 0.1)
            t_end  = ask_float("เวลาจำลองไฟล์ (s) [3.0]: ", 3.0)
            dt     = ask_float("ช่วงเวลาเก็บข้อมูล dt (s) [0.01]: ", 0.01)
            noise  = ask_float("noise std (rad/s) [0.0=ไม่มี]: ", 0.0)
            synthesize_step_data(csv_path, R, L, Kt, Ke, J_true, b_true,
                                 step_mag=step_mag, t_end=t_end, dt=dt,
                                 include_L=include_L, noise_std=noise, seed=0)

        if not os.path.isfile(csv_path):
            print("ไม่พบไฟล์ CSV: ", csv_path)
            return
        data = np.loadtxt(csv_path, delimiter=",")
        if data.shape[1] < 2:
            print("ไฟล์ต้องมี 2 คอลัมน์: t, omega")
            return
        t_data, w_data = data[:,0], data[:,1]
        # Identify J,b
        J_hat, b_hat = identify_J_b(t_data, w_data, R, L, Kt, Ke, step_mag, include_L=include_L)
        J = J_hat if J < 0 else J
        b = b_hat if b < 0 else b

    # Build plant
    G = dc_motor_tf(R, L, J, b, Kt, Ke, include_L=include_L)
    print("\nPlant G(s) =", G)

    # Tune PID
    Kp, Ki, Kd, met = tune_pid(
        G, step_mag=step_mag, t_end=sim_T, npts=1600,
        use_d_filter=use_d_filter, Tf=Tf
    )

    # Show all figures
    plt.show()

if __name__ == "__main__":
    main()
