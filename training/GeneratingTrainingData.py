import psutil
import subprocess
import time
import wmi
import csv
import os
from datetime import datetime

LHM_PATH = r"C:\Users\twoth\Desktop\training\LibreHardwareMonitor\LibreHardwareMonitor.exe"

#INTEL CORE i7-7700HQ 기준인데 변경가능성있음
BASE_CLOCK = 1400#MHz
CRITICAL_TEMP = 95#섭씨


#LibreHWMonitor실행중인지 확인하는 함수
def Ensure_lhm_running():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'LibreHardwareMonitor.exe':
            print("이미 실행중")
            return True
    try:
        subprocess.Popen(LHM_PATH)
        time.sleep(3)#프로그램이 실행될시간
        return True
    except FileNotFoundError:
        print(f"경로가 잘못된경우")
        exit()
    except Exception as e:
        print(f"이외의 오류: {e}")
        exit()


# 3. 메인 모니터링 로직
Ensure_lhm_running()
print("모니터링 시작, 종료조건은 Ctrl+C")

# WMI(온도 센서 통로) 연결
try:
    hwmon = wmi.WMI(namespace="root\\OpenHardwareMonitor")
except Exception as e:
    print("권한 문제 or 이외의 오류로 WMI(온도 센서 통로)연결 실패: {e}")
    exit()


os.makedirs("trainingData", exist_ok=True)
filename = f"trainingData/throttle_log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

# CSV 파일 열기 및 헤더 작성
with open(filename, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Time", "CPU_Temp(C)", "CPU_Usage(%)", "CPU_Freq(MHz)", "RAM_Usage(%)", "Status"])
    #시간 ,cpu온도, 점유율,클럭주기 , 램점유율, 상태?
    try:
        while True:
            time.sleep(2) # 2초마다 갱신
            now = datetime.now().strftime("%H:%M:%S")
            
            # [A] psutil 데이터 수집 (점유율, 클럭, RAM)
            cpu_util = psutil.cpu_percent(interval=None)
            cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0
            ram_util = psutil.virtual_memory().percent
            
            # [B] WMI 온도 데이터 수집 (코어 중 가장 높은 온도 추출)
            max_temp = 0
            sensors = hwmon.Sensor()
            for sensor in sensors:
                if sensor.SensorType == 'Temperature' and 'CPU' in sensor.Name:
                    if sensor.Value > max_temp:
                        max_temp = sensor.Value
            
            # [C] 쓰로틀링 판별 로직
            status = "Normal"
            if cpu_util > 80 and max_temp >= CRITICAL_TEMP and cpu_freq < BASE_CLOCK:
                status = "THROTTLING"
                print(f"쓰로틀링, (온도:{max_temp}°C, 점유율:{cpu_util}%, 클럭:{cpu_freq}MHz)")
            else:
                # 콘솔창이 너무 복잡해지는 게 싫다면 아래 print문은 주석 처리해도 됩니다.
                print(f"[{now}] 정상 (온도:{max_temp}°C, 점유율:{cpu_util}%, 클럭:{cpu_freq}MHz)")

            # [D] CSV 파일에 현재 상태 기록
            writer.writerow([now, max_temp, cpu_util, cpu_freq, ram_util, status])
            f.flush() # 버퍼를 비워 데이터 유실 방지

    except KeyboardInterrupt:
        print(f"\n로그파일 저장 완료")