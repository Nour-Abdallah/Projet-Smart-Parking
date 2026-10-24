import cv2
import pytesseract
import numpy as np
import csv
import os
import time

# 🔧 Chemin Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# 📂 Base CSV
BASE_CSV = "authorized_vehicles.csv"

AUTHORIZED_PLATES = set()
OWNER_MAP = {}

with open(BASE_CSV, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        plate = row["plate"].strip().upper().replace(" ", "").replace("-", "")
        AUTHORIZED_PLATES.add(plate)
        OWNER_MAP[plate] = row["owner"]

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Erreur caméra")
    exit()

LAST_PLATE = ""
LAST_TIME = 0
COOLDOWN = 2.0  # secondes

print("📡 Système de contrôle d'accès démarré...\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 100, 200)

    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plate_text = ""
    plate_box = None

    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.018 * cv2.arcLength(cnt, True), True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            plate_img = gray[y:y+h, x:x+w]
            plate_img = cv2.threshold(plate_img, 150, 255, cv2.THRESH_BINARY)[1]

            plate_text = pytesseract.image_to_string(
                plate_img,
                config="--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            )
            plate_text = plate_text.strip().upper().replace(" ", "").replace("-", "")
            plate_box = (x, y, w, h)
            break

    current_time = time.time()

    if plate_text and plate_box:
        if plate_text != LAST_PLATE or (current_time - LAST_TIME) > COOLDOWN:
            LAST_PLATE = plate_text
            LAST_TIME = current_time

            # 🔐 Vérification accès
            if plate_text in AUTHORIZED_PLATES:
                color = (0, 200, 0)
                owner = OWNER_MAP.get(plate_text, "Inconnu")
                message = f"ACCES AUTORISE | {plate_text}"

                print(f"[✔] ACCES AUTORISE | Matricule : {plate_text} | Propriétaire : {owner}")

            else:
                color = (0, 0, 200)
                message = f"ACCES REFUSE | {plate_text}"

                print(f"[✖] ACCES REFUSE  | Matricule : {plate_text}")

        x, y, w, h = plate_box
        cv2.rectangle(frame, (x-5, y-5), (x+w+5, y+h+5), color, 3)

        cv2.rectangle(frame, (0, 0), (frame.shape[1], 90), (0, 0, 0), -1)

        cv2.putText(frame, message, (20, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)

    cv2.imshow("Parking Intelligent", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        print("\n🛑 Arrêt du système")
        break

cap.release()
cv2.destroyAllWindows()